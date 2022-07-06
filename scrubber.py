# -*- coding: utf-8 -*-


from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementNotInteractableException, \
    ElementClickInterceptedException

import sys, os, time, logging, re, datetime
import pandas as pd

from util import find_value, find_json, find_jsons, append_df, write_to_bucket

import undetected_chromedriver as uc


# 30 minutes suggested (Tomlein et al. 2021)
MAX_WATCH_SECONDS = 1800
LOAD_BUFFER_SECONDS = 10
MAX_RECS = 10
MAX_SCRUB_NET_SIZE = 10
CHROME_VERSION = 102


# Much of this code is inspired by Siqi Wu's YouTube Polarizer: https://github.com/avalanchesiqi/youtube-polarizer
class Scrubber(object):

    def __init__(self, community, scrubbing_strategy, note, account_username, account_password,
                 staining_videos_csv, scrubbing_extras_csv=None, s3_bucket='youtube-audit-bucket'):
        def __get_logger(log_filepath):
            """
            Create a log file.
            """
            fileh = logging.FileHandler(log_filepath, 'w')
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            fileh.setFormatter(formatter)

            logger = logging.getLogger()  # root logger
            for handler in logger.handlers[:]:  # remove all old handlers
                logger.removeHandler(handler)
            logger.addHandler(fileh)
            logger.setLevel(logging.INFO)
            return logger

        def __get_driver():
            chrome_options = uc.ChromeOptions()
            chrome_options.add_argument('--mute-audio')
            chrome_options.add_argument('--load-extension=./conf/webdriver/uBlock-Origin')

            driver = uc.Chrome(options=chrome_options, version_main=CHROME_VERSION)
            driver.maximize_window()

            return driver

        # Creating the outputs directory
        os.makedirs('outputs')
        os.makedirs('outputs/fails')

        self.community = community
        self.scrubbing_strategy = scrubbing_strategy
        self.note = note
        self.account_username = account_username
        self.account_password = account_password
        self.staining_videos_csv = staining_videos_csv
        if scrubbing_extras_csv is not None:
            self.scrubbing_extras_csv = scrubbing_extras_csv
        self.s3_bucket = s3_bucket

        # Staining videos
        test_vid = 'CuOTY6yGygo'
        with open(self.staining_videos_csv, newline='') as f:
            lines = f.readlines()
            lines = [line.rstrip() for line in lines]
            self.staining_videos = lines
        for video in self.staining_videos:
            assert(type(video) == str)
            assert(len(video) == len(test_vid))

        assert(len(self.staining_videos) > 0)
        self.videopage_experiment_vid = self.staining_videos[0]

        # Scrubbing stuff
        if self.scrubbing_strategy in ['not interested', 'no channel', 'dislike recommendation', 'watch']:
            with open(scrubbing_extras_csv, newline='') as f:
                lines = f.readlines()
                lines = [line.rstrip() for line in lines]
                scrubbing_extras = lines
            for extra in scrubbing_extras:
                assert (type(extra) == str)
                if self.scrubbing_strategy == 'watch':
                    assert (len(extra) == len(test_vid))
                else:
                    assert (extra[:2] == 'UC')
            if self.scrubbing_strategy == 'watch':
                self.scrubbing_videos = scrubbing_extras
            else:
                self.scrubbing_channels = scrubbing_extras


        name = self.community + '_' + self.scrubbing_strategy + '_' + str(self.note)
        name = name.replace('.', '_')
        name = name.replace(' ', '-')
        self.name = name

        self.results_filename = 'results_{0}.csv'.format(name)
        self.log_filename = 'logs_{0}.log'.format(name)
        # Increments at each failure
        self.fail_count = 0

        self.results_filepath = os.path.join('.', 'outputs', self.results_filename)
        self.log_filepath = os.path.join('.', 'outputs', self.log_filename)

        open(self.results_filepath, 'x')
        self.logger = __get_logger(self.log_filepath)
        # TESTING
        self.driver = __get_driver()
        time.sleep(3)

        self.phase = "setup"
        self.phase_level = 0
        self.videopage_level = 0
        self.homepage_level = 0

        self.log('Created bot in community {0} and scrubbing strategy {1}'
                 .format(self.community, self.scrubbing_strategy))

    def get_fail_filename(self, count=-1):
        if count == -1:
            return 'fail_{0}_{1}.html'.format(self.name, self.fail_count)
        else:
            return 'fail_{0}_{1}.html'.format(self.name, count)

    def get_fail_filepath(self, count=-1):
        return os.path.join('.', 'outputs', 'fails', self.get_fail_filename(count))

    def set_phase(self, phase):
        self.phase = phase

    def log(self, message, exception=False):
        """
        Print and log the same message
        """
        if exception:
            print(message)
            self.logger.exception(message)
        else:
            print(message)
            self.logger.info(message)

    # Modified from Tomlein et al. (2021)
    def login(self):
        """
        Try and login (many times if necessary)
        """
        counter = 0
        max_tries = 5

        self.log('Attempting login with username "{0}" and password "{1}".'.format(self.account_username, self.account_password))

        success = False
        while success is False and counter < max_tries:
            if counter > 0:
                self.log('Login attempt failed, trying again')
            # Hacky way to alternate
            if counter % 2 == 0:
                self.youtube_login_2()
            else:
                self.youtube_login()
            # May get prompted for recaptcha or phone number here
            time.sleep(10)
            success = self.was_login_successful()
            counter += 1

        if success:
            self.log('Login succeeded at attempt #{0}'.format((counter)))
        else:
            self.log('All login Attempts failed')
            raise RuntimeError(f'All login attempts failed.')

    # Modified from Tomlein et al. (2021)
    # Waiting documentation: https://www.selenium.dev/documentation/webdriver/waits/
    # We use a locator rather than an element (i.e. 'find_element(...)' to pass into the until method, because locator
    #   doesn't return an error when not present (yet), and therefore allows 'until' to do its job by repeatedly pinging
    #   the locator
    def youtube_login(self):
        """
        Perform the login
        """
        # Maximum wait time for page to load when logging in
        login_wait_secs = 30
        #login_url = 'https://accounts.google.com/ServiceLogin?service=chromiumsync'
        login_url = 'https://accounts.google.com/o/oauth2/v2/auth/oauthchooseaccount?' \
                    'redirect_uri=https%3A%2F%2Fdevelopers.google.com%2Foauthplayground&' \
                    'prompt=consent&response_type=code&' \
                    'client_id=407408718192.apps.googleusercontent.com&' \
                    'scope=email&' \
                    'access_type=offline&' \
                    'flowName=GeneralOAuthFlow'
        print('logging into: {0}'.format(login_url))

        self.driver.get(login_url)

        # Submit username and click next
        WebDriverWait(self.driver, login_wait_secs).until(
            EC.visibility_of_element_located((By.ID, 'Email'))
        ).send_keys(self.account_username)
        WebDriverWait(self.driver, login_wait_secs).until(
            EC.element_to_be_clickable((By.ID, 'next'))
        ).click()

        # Submit password and click next
        WebDriverWait(self.driver, login_wait_secs).until(
            EC.visibility_of_element_located((By.ID, 'password'))
        ).send_keys(self.account_password)
        WebDriverWait(self.driver, login_wait_secs).until(
            EC.element_to_be_clickable((By.ID, 'submit'))
        ).click()

    # New login page discovered 5/24
    def youtube_login_2(self):
        login_url = 'https://accounts.google.com/o/oauth2/v2/auth/oauthchooseaccount?' \
                    'redirect_uri=https%3A%2F%2Fdevelopers.google.com%2Foauthplayground&' \
                    'prompt=consent&response_type=code&' \
                    'client_id=407408718192.apps.googleusercontent.com&' \
                    'scope=email&' \
                    'access_type=offline&' \
                    'flowName=GeneralOAuthFlow'
        print('logging into: {0}'.format(login_url))
        self.driver.get(login_url)
        time.sleep(5)

        input_field = self.driver.find_element(By.CSS_SELECTOR, 'input#identifierId')
        input_field.send_keys(self.account_username)
        time.sleep(5)
        next_button = self.driver.find_element(By.CSS_SELECTOR, 'div#identifierNext')
        next_button.click()
        time.sleep(5)

        password = self.driver.find_element(By.CSS_SELECTOR, 'input[type="password"]')
        password.send_keys(self.account_password)
        time.sleep(5)
        next_button = self.driver.find_element(By.CSS_SELECTOR, 'div#passwordNext')
        next_button.click()

    def was_login_successful(self):
        """
        (Not necessarily required if we're confident a login occurs) Confirm the login was successful
        """
        youtube_url = 'https://www.youtube.com/'
        self.driver.get(youtube_url)
        time.sleep(5)
        logged_in = False
        try:
            self.driver.find_element(By.CSS_SELECTOR, '[aria-label="Sign in"]')
        except NoSuchElementException:
            logged_in = True
        return logged_in

    def load_and_save_homepage(self):
        try:
            self.__load_and_save_homepage()
        # Might be a bit broad with key error
        except (EC.NoSuchElementException, KeyError):
            self.fail_safely()

    def __load_and_save_homepage(self):
        """
        Load the homepage, wait, and then save its recommendations
        """
        self.__load_homepage()
        time.sleep(LOAD_BUFFER_SECONDS)
        self.__save_homepage()

        self.homepage_level += 1

    def __load_homepage(self):
        """
        Load the homepage
        """
        homepage_url = 'https://www.youtube.com'

        self.log('Loading homepage.')
        self.driver.get(homepage_url)

    def __save_homepage(self):
        """
        Save the top recommendations (just video ID's) on the homepage
        """

        self.log('Saving homepage.')

        # Grab just what we need from js: the channel id
        channels_dict = {}
        html = self.driver.page_source
        initial_data = find_value(html, 'var ytInitialData = ', 0, '\n').rstrip(';')
        js_videos = find_jsons(initial_data, '"videoRenderer":{')
        for js_video in js_videos:
            try:
                js_vid = js_video['videoId']
                js_cid = js_video['longBylineText']['runs'][0]['navigationEndpoint']['browseEndpoint']['browseId']
                channels_dict[js_vid] = js_cid
            except KeyError:
                continue

        # Use webelements to find video ids in rank order
        video_ids = []
        elems = self.driver.find_elements(By.CSS_SELECTOR, 'a#video-title-link[href^="/watch?v="]')
        for elem in elems:
            link = elem.get_attribute('href')
            if len(link) > len('https://www.youtube.com/watch?v='):
                vid = link[len('https://www.youtube.com/watch?v='):]
                video_ids.append(vid)

        # Run through the rank order video ids, each time finding its corresponding channel id, and writing the results
        recs_data = []
        recs_ids = []
        for i in range(len(video_ids)):
            if i > MAX_RECS-1:
                break

            video_id = video_ids[i]
            if video_id in channels_dict:
                channel_id = channels_dict[video_id]
            else:
                channel_id = None

            rec_data = {'video_id': video_id, 'channel_id': channel_id, 'rank': i, 'component': 'homepage'}

            rec_data = self.__attach_context(rec_data)
            recs_data.append(rec_data)
            recs_ids.append(video_id)

        self.log('Recommended videos: {0}'.format(recs_ids))
        self.__write_recs(recs_data)

    def load_and_save_videopage(self, vid_id):
        """
        Load a videopage, wait, and then save the recommendations
        """
        try:
            duration = self.__load_and_save_videopage(vid_id)
            return duration
        # Might be a bit broad with key error
        except (EC.NoSuchElementException, KeyError):
            self.fail_safely()
            return 0

    def __load_and_save_videopage(self, vid_id):
        """
        Load a videopage, wait, and then save the recommendations
        """
        self.__load_videopage(vid_id)
        time.sleep(LOAD_BUFFER_SECONDS)
        self.__save_videopage(vid_id)
        duration = self.__get_videopage_seconds()

        self.videopage_level += 1

        return duration

    def __load_videopage(self, vid_id):
        """
        Load the videopage
        """
        youtube_watch_url = 'https://www.youtube.com/watch?v='

        self.log('Loading video ID {0}.'.format(vid_id))
        videopage_url = youtube_watch_url + vid_id
        self.driver.get(videopage_url)

    def __save_videopage(self, watch_id):
        """
        Find and write recommendations on the videopage (both video ID's and channel ID's)
        Examines the js code (rather than raw html) because channel ID's are only available there
        """

        self.log('Saving videopage')

        html = self.driver.page_source
        # Find and write recommendations
        initial_data = find_value(html, 'var ytInitialData = ', 0, '\n').rstrip(';')
        secondary_results = find_json(initial_data, '"secondaryResults":{')

        # Sanity check
        if len(secondary_results) <= 0 or \
                'secondaryResults' not in secondary_results or \
                'results' not in secondary_results['secondaryResults'] or \
                len(secondary_results['secondaryResults']['results']) <= 0:
            # Something is wrong!!!
            self.logger.error('Unable to find recommendations!')
            return

        recs = []
        rec_ids = []
        rank = 0
        video_suggestions = secondary_results['secondaryResults']['results']
        # New as of 3/2/2021: Filtering recommendations by "chips", e.g. 'All', 'Listenable', 'Related'...
        try:
            video_suggestions = video_suggestions[1]['itemSectionRenderer']['contents']
        # We need this in the case of Incognito, when there are no rec filters
        except KeyError:
            video_suggestions = secondary_results['secondaryResults']['results']
        for rec in video_suggestions:
            # 0 indexed
            if rank > MAX_RECS-1:
                break
            # This video is autoplay
            if 'compactAutoplayRenderer' in rec:
                rec = rec['compactAutoplayRenderer']['contents'][0]['compactVideoRenderer']
                found = True
            # This video is non-autoplay
            elif 'compactVideoRenderer' in rec:
                rec = rec['compactVideoRenderer']
                found = True
            else:
                # Video could be a livestream which we ignore
                continue

            # Find the video ID
            if found and 'videoId' in rec:
                video_id = rec['videoId']
                cid = rec['longBylineText']['runs'][0]['navigationEndpoint']['browseEndpoint']['browseId']

                rec_data = {'video_id': video_id, 'channel_id': cid, 'rank': rank, 'component': 'videopage',
                            'watch_video_id': watch_id}
                rec_data = self.__attach_context(rec_data)
                recs.append(rec_data)
                rec_ids.append(video_id)

            rank += 1

        self.__write_recs(recs)
        self.log('Recommended videos: {0}'.format(rec_ids))

    def __get_videopage_seconds(self):
        """
        Get the duration of the video
        """
        html = self.driver.page_source
        initial_player_response = find_value(html, 'var ytInitialPlayerResponse = ', 0, '\n').rstrip(';')
        video_details = find_json(initial_player_response, '"videoDetails":{')
        duration = int(video_details['lengthSeconds'])

        return duration

    def watch_video(self, duration):
        """
        Watch the (already-loaded) video for (slightly less than) the specified period of time
        """
        watch_seconds = min(duration, MAX_WATCH_SECONDS) - LOAD_BUFFER_SECONDS
        if watch_seconds < 0:
            watch_seconds = 0
        self.log('Watching video for {0} seconds.'.format(watch_seconds))
        time.sleep(watch_seconds)

    # We only implement this one because it's the only one being used so far for our scrubbing experiment
    def dislike_video(self):
        self.video_action('dislike')

    # Modified from Tomlein et al. (2021)
    def video_action(self, action, turn_on=True):
        """
        Attempt the 'action' of pressing one of the buttons right below the video screen
        By 'action' we mean 'like', 'dislike', or 'subscribe'.
        turn_on was added to accomodate 'un-disliking' a video (via setting turn_on to False).
        Un-disliking functionality is now done through the myactivities page but we keep turn_on for future use
        """
        counter = 1
        max_tries = 5

        self.log('Attempting to press the {0} button.'.format(action))
        while counter < max_tries:
            try:
                success = self.__interact_with_action_button(action, turn_on)
                if success:
                    self.log('Success at attempt #{0}'.format(counter))
                    return success
                else:
                    counter += 1
            # TODO LONGTERM: Make this more specific, think about a "WebInteractionError" to raise whenever the thing
            except:
                counter += 1
                if counter > 5:
                    self.log('All attempts failed.')
                    break
        self.fail_safely()

    # Modified from Tomlein et al. (2021)
    def __interact_with_action_button(self, action, turn_on=True):
        """
        Get and click on the button (if not clicked on already)
        """
        button, already_pressed = self.__get_action_button(action)
        if (already_pressed and turn_on) or \
                (not already_pressed and not turn_on):
            self.log('Button already pressed.')
            return True
        else:
            try:
                button.click()
            except (ElementNotInteractableException, ElementClickInterceptedException):
                # Not tested for subscribe yet
                self.driver.execute_script("arguments[0].click();", button)
        _, now_pressed = self.__get_action_button(action)
        return now_pressed

    # Get both the button and the status of it (whether it is already pressed)
    def __get_action_button(self, action):
        """
        Get the action button, as well as its status as either pressed or not
        """
        if action == 'like':
            return self.__get_like_button()
        if action == 'dislike':
            return self.__get_dislike_button()
        if action == 'subscribe':
            return self.__get_subscribe_button()
        self.log('Action {0} not implemented yet!!!'.format(action))
        raise NotImplementedError

    # Note that we have not tested yet whether the outside (meta_contents) can be loaded
    #   while the inside is not... such an event would necessitate waiting at every stage
    # Why do we have to do regex and not partial link text?
    # ... because searching for 'like' may return the dislike button if it's the first button presented in the loop
    def __get_like_button(self):
        """
        Get the like button and its status (pressed or nah)
        """
        WebDriverWait(self.driver, 30).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'div#menu-container'))
        )

        menu = self.driver.find_element(By.CSS_SELECTOR, 'div#menu-container')
        buttons = menu.find_elements(By.CSS_SELECTOR, 'button.yt-icon-button')
        for elem in buttons:
            label = elem.get_attribute('aria-label')
            if re.search('\A[Ll]ike', label):
                pressed = elem.get_attribute('aria-pressed') == 'true'
                return elem, pressed

    def __get_dislike_button(self):
        """
        Get the dislike button and its status (pressed or nah)
        """
        # TODO: Abstract
        wait_element_secs = 10
        WebDriverWait(self.driver, wait_element_secs).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'div#menu-container'))
        )

        menu = self.driver.find_element(By.CSS_SELECTOR, 'div#menu-container')
        buttons = menu.find_elements(By.CSS_SELECTOR, 'button.yt-icon-button')
        for elem in buttons:
            label = elem.get_attribute('aria-label')
            if re.search('\A[Dd]islike', label):
                pressed = elem.get_attribute('aria-pressed') == 'true'
                return elem, pressed

    def __get_subscribe_button(self):
        """
        Get the subscribe button and its status (pressed or nah)
        """
        WebDriverWait(self.driver, 30).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'div#meta-contents'))
        )

        meta_contents = self.driver.find_element(By.CSS_SELECTOR, 'div#meta-contents')
        subscribe_button = meta_contents.find_element(By.CSS_SELECTOR, 'div#subscribe-button')

        pressed = subscribe_button.text == 'SUBSCRIBED'
        return subscribe_button, pressed

    def __attach_context(self, row):
        """
        Add in details about the run that are required for the recommendation row but do not need to be scraped
        """
        if 'bot_name' not in row:
            row['bot_name'] = self.name
        if 'phase' not in row:
            row['phase'] = self.phase
        if 'phase_level' not in row:
            row['phase_level'] = self.phase_level
        if 'homepage_level' not in row:
            row['homepage_level'] = self.homepage_level
        if 'videopage_level' not in row:
            row['videopage_level'] = self.videopage_level
        if 'time' not in row:
            row['time'] = datetime.datetime.now()
        return row

    def __write_recs(self, recs):
        """
        Write recommendations list into csv
        """
        #hacky fix
        if len(recs) == 0:
            self.log('error with writing- no recommendations!')
            recs = self.__attach_context({})
            recs_df = pd.DataFrame([recs])
        else:
            recs_df = pd.DataFrame(recs)
        append_df(recs_df, self.results_filepath, False)

    def delete_most_recent(self):
        # TODO: Abstract
        element_wait_secs = 10
        try:
            history_url = 'https://www.youtube.com/feed/history'

            self.log('Loading history page.')
            self.driver.get(history_url)

            time.sleep(5)

            WebDriverWait(self.driver, element_wait_secs).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'div#contents'))
            )
            contents = self.driver.find_element(By.CSS_SELECTOR, 'div#contents')

            self.log('Deleting most recent.')
            button = contents.find_element(By.CSS_SELECTOR, 'button')
            button.click()
        except (ElementNotInteractableException, NoSuchElementException, ElementClickInterceptedException):
            self.fail_safely()

    def dislike_recommended(self, sim_rec_match=False):
        unwanted_video = self.scrub_homepage(sim_rec_match=sim_rec_match)
        time.sleep(5)
        if unwanted_video:
            unwanted_video.click()
            time.sleep(5)
            self.dislike_video()

    # Implementing this after realizing you can do "tell us why" --> "don't like video"
    #   after clicking on the actual not interested button
    def not_interested(self, sim_rec_match=False):
        found = self.menu_service('not interested', sim_rec_match=sim_rec_match)
        time.sleep(5)

        if found:
            # click "tell us why"
            tell_us_why_button = self.driver.find_element(By.CSS_SELECTOR, '[aria-label="Tell us why"]')
            tell_us_why_button.click()
            time.sleep(5)

            # click "I don't like the video"
            check_boxes = self.driver.find_elements(By.CSS_SELECTOR, 'div#reasons tp-yt-paper-checkbox')
            for check_box in check_boxes:
                if check_box.text == "I don't like the video":
                    check_box.click()
                    time.sleep(5)
                    break

            # click "Submit"
            submit_button = self.driver.find_element(By.CSS_SELECTOR, 'ytd-button-renderer#submit')
            submit_button.click()

    def no_channel(self, sim_rec_match=False):
        self.menu_service('no channel', sim_rec_match)

    def menu_service(self, action, sim_rec_match):
        unwanted_video = self.scrub_homepage(sim_rec_match)
        time.sleep(5)
        if unwanted_video:

            self.log('Attempting to click the {0} button'.format(action))

            # Click the three dots
            menu = unwanted_video.find_element(By.CSS_SELECTOR, 'ytd-menu-renderer')
            menu.click()

            time.sleep(5)

            content_wrapper = self.driver.find_element(By.CSS_SELECTOR, 'div#contentWrapper')
            buttons = content_wrapper.find_elements(By.CSS_SELECTOR, 'ytd-menu-service-item-renderer')
            if action == 'not interested':
                button_text = 'Not interested'
            elif action == 'no channel':
                button_text = "Don't recommend channel"
            else:
                raise NotImplementedError
            found = False
            for button in buttons:
                if button_text in button.text:
                    button.click()
                    self.log('Clicked!')
                    found = True
                    break
            if not found:
                self.log('Button not found.')
                raise NotImplementedError
            # Indicating whether a video to scrub was actually found
            return True
        return False

    def scrub_homepage(self, sim_rec_match):
        """
        Load the homepage
        """
        # assert(self.driver.current_url == 'https://www.youtube.com')

        self.log('Checking homepage for video from unwanted channel.')

        # Copied from save_homepage
        channels_dict = {}
        html = self.driver.page_source
        initial_data = find_value(html, 'var ytInitialData = ', 0, '\n').rstrip(';')
        js_videos = find_jsons(initial_data, '"videoRenderer":{')
        for js_video in js_videos:
            try:
                js_vid = js_video['videoId']
                js_cid = js_video['longBylineText']['runs'][0]['navigationEndpoint']['browseEndpoint']['browseId']
                channels_dict[js_vid] = js_cid
            except KeyError:
                continue

        # Use webelements to find video ids in rank order
        video_ids = []
        elems = self.driver.find_elements(By.CSS_SELECTOR, 'a#video-title-link[href^="/watch?v="]')
        for elem in elems:
            link = elem.get_attribute('href')
            if len(link) > len('https://www.youtube.com/watch?v='):
                vid = link[len('https://www.youtube.com/watch?v='):]
                video_ids.append(vid)

        unwanted_video_id = None
        for i in range(len(video_ids)):
            if i > MAX_SCRUB_NET_SIZE:
                break
            video_id = video_ids[i]
            if video_id in channels_dict:
                channel_id = channels_dict[video_id]

                if channel_id in self.scrubbing_channels:
                    self.log('Found video {0} from unwanted channel {1}.'.format(video_id, channel_id))
                    unwanted_video_id = video_id
                    break
                elif sim_rec_match and i == 3:
                    self.log('SIM_REC_MATCH: Pretending that the fourth video ({0}, {1}) matches'.format(video_id, channel_id))
                    unwanted_video_id = video_id
                    break

        if unwanted_video_id:
            # FIND BUTTON/VIDEO CARD IN HTML
            recs = self.driver.find_elements(By.CSS_SELECTOR, 'div#contents div#content')
            unwanted_query = 'a[href*="/watch?v=' + unwanted_video_id + '"]'
            for rec in recs:
                try:
                    # Seeing if video id is findable in this video card
                    rec.find_element(By.CSS_SELECTOR, unwanted_query)
                    return rec
                except:
                    continue
        else:
            self.log('No videos from unwanted channels were found.')
            return None

    def attempt(self, fun):
        """
        Attempt a function that might need a few attempts to succeed
        If we don't get it by max_tries let's just actually fail and write to failures folder
        """
        counter = 0
        max_tries = 5
        success = False
        while success is False and counter < max_tries:
            try:
                fun()
                success = True
            except:
                counter += 1
        if not success:
            fun()

    def clear_history(self):
        self.attempt(self.__clear_history)

    def clear_not_interested(self):
        self.attempt(self.__clear_not_interested)

    def clear_likes_dislikes(self):
        self.attempt(self.__clear_likes_dislikes)

    def clear_subscriptions(self):
        self.attempt(self.__clear_subscriptions)

    # Modified from Tomlein et al. (2021)
    def __clear_history(self):
        clear_wait_secs = 10
        self.log('Clearing watch history.')

        self.driver.get('https://myactivity.google.com/item')

        clicked = self.__open_clear_history_popup()

        if not clicked:
            # Wait until hamburger element on page loads and click it
            WebDriverWait(self.driver, clear_wait_secs).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'div.gb_vc:nth-child(1)')))
            WebDriverWait(self.driver, clear_wait_secs).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.gb_vc:nth-child(1)')))
            self.driver.find_element_by_css_selector('div.gb_vc:nth-child(1)').click()
            self.__open_clear_history_popup()

        # Wait until the popup windows gets loaded
        WebDriverWait(self.driver, clear_wait_secs).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'div.iZdpV')))
        WebDriverWait(self.driver, clear_wait_secs).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.iZdpV')))

        # Find link for deleting all history in choices and click it
        choice_list = self.driver.find_elements_by_css_selector('div.iZdpV')
        for choice in choice_list:
            if choice.text == 'Always' or choice.text == 'All time':
                choice.click()
                break

        # Wait until next part of popup window loads
        WebDriverWait(self.driver, clear_wait_secs).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'div.Df8Did')))
        time.sleep(1)
        # Find all buttons
        buttons = self.driver.find_element_by_css_selector('div.Df8Did').find_elements_by_css_selector('span.VfPpkd-vQzf8d')
        for button in buttons:
            # In case there are multiple sources of history are present click `Next` and find `Delete` button to click
            if button.text == 'Next':
                # Click `Next`
                button.find_element_by_xpath('..').click()
                # Wait while new buttons load
                time.sleep(1)
                # Find all the buttons and click `Delete`
                other_buttons = self.driver.find_element_by_css_selector('div.Df8Did').find_elements_by_css_selector('span.VfPpkd-vQzf8d')
                for other_button in other_buttons:
                    if other_button.text == 'Delete':
                        other_button.find_element_by_xpath('..').click()
                        return
            # In case only one source of history is present click `Delete`
            elif button.text == 'Delete':
                button.find_element_by_xpath('..').click()
                break

    def __open_clear_history_popup(self):
        clear_wait_secs = 10

        # Wait until menu opens and find link for deleting all activity
        WebDriverWait(self.driver, clear_wait_secs).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'a.IlZEuc')))
        WebDriverWait(self.driver, clear_wait_secs).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.IlZEuc')))
        navigation_menu_links = self.driver.find_elements_by_css_selector('.IlZEuc')
        for link in navigation_menu_links:
            if link.text == 'Delete activity by':
                # Check if menu is open
                try:
                    link.click()
                    return True
                except ElementNotInteractableException:
                    self.driver.find_element_by_css_selector('div.gb_vc:nth-child(1)').click()
                    link.click()
                    return True
        return False

    def __clear_not_interested(self):
        self.log('Clearing "not interested" and "dont recommend channel" selections.')
        self.driver.get('https://myactivity.google.com/more-activity')

        time.sleep(5)

        delete_button = self.driver.find_element_by_css_selector('div[jsname=ks0aWd] button')
        delete_button.click()

        time.sleep(5)

        confirm_delete_button = self.driver.find_element_by_css_selector('[class="XfpsVe J9fJmf"] [class=Crf1o]')
        confirm_delete_button.click()

    def __clear_likes_dislikes(self):
        self.log('Clearing likes and dislikes.')
        self.driver.get('https://myactivity.google.com/page?utm_source=my-activity&hl=en&page=youtube_likes')

        time.sleep(5)

        delete_button = self.driver.find_element_by_css_selector('a[jsname=BWf65c]')
        delete_button.click()

        time.sleep(5)

        confirm_delete_button = self.driver.find_element_by_css_selector('[class="XfpsVe J9fJmf"] [class=Crf1o]')
        confirm_delete_button.click()

    def __clear_subscriptions(self):
        self.log('Clearing subscriptions.')
        self.driver.get('https://myactivity.google.com/page?utm_source=my-activity&hl=en&page=youtube_subscriptions')

        while True:
            try:
                time.sleep(5)
                x_button = self.driver.find_element_by_css_selector('div.YkIxob div.iM6vT')
                x_button.click()

                time.sleep(5)

                confirm_delete_button = self.driver.find_element_by_css_selector('[class="XfpsVe J9fJmf"] [class=Crf1o]')
                confirm_delete_button.click()

            except NoSuchElementException:
                break

    def fail_safely(self):
        fail_filepath = self.get_fail_filepath()
        self.log('Error! Saving html to ' + fail_filepath, True)
        # Sometimes, there are issues with writing the html file itself for further investigation later
        #    (e.g. delay from message renderer). But in these cases, we still would like to "fail safely"
        #    and move on to the next step.
        try:
            html = self.driver.page_source
            with open(fail_filepath, 'w') as f:
                f.write(html)
        except:
            self.log('Cannot write error html for some reason', True)
        self.fail_count += 1

    def write_s3(self):
        # write failure(s), log, results
        dt = datetime.datetime.now().strftime('%Y-%m-%d/%H:%M:%S')
        write_to_bucket(self.s3_bucket, self.results_filepath, 'outputs/{0}/{1}'.format(dt, self.results_filename))
        write_to_bucket(self.s3_bucket, self.log_filepath, 'outputs/{0}/{1}'.format(dt, self.log_filename))
        for i in range(self.fail_count):
            write_to_bucket(self.s3_bucket, self.get_fail_filepath(i),
                            'outputs/{0}/{1}'.format(dt, self.get_fail_filename(i)))

