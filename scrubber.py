# -*- coding: utf-8 -*-


from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementNotInteractableException, \
    ElementClickInterceptedException

import sys, os, time, json, logging, re, datetime, csv
import pandas as pd

from util import find_value, find_json, find_jsons, append_df

# 30 minutes suggested (Tomlein et al. 2021)
MAX_WATCH_SECONDS = 1800
LOAD_BUFFER_SECONDS = 10
MAX_RECS = 10


# Much of this code is inspired by Siqi Wu's YouTube Polarizer: https://github.com/avalanchesiqi/youtube-polarizer
class Scrubber(object):

    TEST = False

    def __init__(self, profile_filepath):
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

        def __get_driver(chrome_arguments):
            """
            Initialize Selenium webdriver with Chrome options.
            """
            # TODO: Use OS Join
            adblock_filepath = 'conf/webdriver/adblock.crx'
            if sys.platform == 'win32':
                driver_path = 'conf/webdriver/chromedriver.exe'
            elif sys.platform == 'darwin':
                driver_path = 'conf/webdriver/chromedriver_mac64'
            else:
                driver_path = 'conf/webdriver/chromedriver_linux64'

            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument('--mute-audio')

            for chrome_argument in chrome_arguments:
                chrome_options.add_argument(chrome_argument)

            chrome_options.add_extension(adblock_filepath)
            driver = webdriver.Chrome(driver_path, options=chrome_options)
            driver.maximize_window()

            # TODO: This needs testing
            time.sleep(3)
            driver.get("chrome://extensions/?id=cjpalhdlnbpafiamejdnhcphjbkeiagm")
            time.sleep(3)
            driver.execute_script(
                "return document.querySelector('extensions-manager').shadowRoot.querySelector('#viewManager > extension"
                "s-detail-view.active').shadowRoot.querySelector('div#container.page-container > div.page-content > div"
                "#options-section extensions-toggle-row#allow-incognito').shadowRoot.querySelector('label#label input')"
                ".click()"
            )
            time.sleep(3)

            return driver

        with open(profile_filepath) as json_file:
            profile = json.load(json_file)

        self.community = profile['community']
        self.scrubbing_strategy = profile['scrubbing_strategy']
        self.note = profile['note']

        staining_videos = profile['staining_videos']
        # Hacky way of re-testing the staining video on the final staining iteration
        if len(staining_videos)>0:
            staining_videos.append(staining_videos[0])
        self.staining_videos = staining_videos
        self.scrubbing_extras = profile['scrubbing_extras']

        self.has_account = False
        if len(profile['account_username']) > 0 and len(profile['account_password']) > 0:
            self.account_username = profile['account_username']
            self.account_password = profile['account_password']
            self.has_account = True
        self.chrome_arguments = profile['chrome_arguments']

        self.unwanted_channels = None
        self.scrubbing_videos = None
        if self.scrubbing_strategy == 'dislike recommendation' or \
                self.scrubbing_strategy == 'not interested' or \
                self.scrubbing_strategy == 'no channel':
            # Get the list of channels from csv
            if type(self.scrubbing_extras) == str and self.scrubbing_extras[-4:] == '.csv':
                with open(self.scrubbing_extras, newline='') as f:
                    lines = f.readlines()
                    lines = [line.rstrip() for line in lines]
                    self.unwanted_channels = lines

            elif type(self.scrubbing_extras) == list:
                self.unwanted_channels = self.scrubbing_extras
            else:
                raise TypeError
            # Make sure it's actually a list of channels that start with 'UC...'
            for channel in self.unwanted_channels:
                assert(type(channel) == str)
                assert(channel[:2] == 'UC')
        elif self.scrubbing_strategy == 'watch':
            self.scrubbing_videos = self.scrubbing_extras
            assert(type(self.scrubbing_videos) == list)
            for video in self.scrubbing_videos:
                assert(type(video) == str)

        name = self.community + '_' + self.scrubbing_strategy + '_' + self.note
        name = name.replace('.', '_')
        name = name.replace(' ', '_')
        self.name = name
        self.results_filepath = os.path.join('.', 'results', '{0}.csv'.format(name))
        self.log_filepath = os.path.join('.', 'logs', '{0}.log'.format(name))

        open(self.results_filepath, 'x')
        self.logger = __get_logger(self.log_filepath)
        self.driver = __get_driver(self.chrome_arguments)

        self.phase = "setup"
        self.phase_level = 0
        self.level = 0
        self.disliked_videos = set()

        self.log('Created bot in community {0} and scrubbing strategy {1}'
                 .format(self.community, self.scrubbing_strategy))

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
            self.__youtube_login()
            success = self.__was_login_successful()
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
    def __youtube_login(self):
        """
        Perform the login
        """
        # Maximum wait time for page to load when logging in
        login_wait_secs = 30
        login_url = 'https://accounts.google.com/ServiceLogin?service=chromiumsync'

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

    # Copied from Tomlein et al. (2021)
    # An interesting way of checking whether we've logged in or not
    # The reasoning seems to be that if you are logged in then google doesn't change your url to some other page
    #   (e.g. create an account or something... idk)
    # I don't understand this, it certainly didn't prevent our non-registered login from going through
    def __was_login_successful(self):
        """
        (Not necessarily required if we're confident a login occurs) Confirm the login was successful
        """
        checking_url = 'https://myactivity.google.com/item'
        # self.driver.get(checking_url)
        # time.sleep(0.25)
        # return self.driver.current_url.count(checking_url) == 1
        return True

    def load_and_save_homepage(self):
        """
        Load the homepage, wait, and then save its recommendations
        """
        self.__load_homepage()
        time.sleep(LOAD_BUFFER_SECONDS)
        self.__save_homepage()

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
        num_homepage_recs = 10
        yt_video_url = 'https://www.youtube.com/watch?v='

        self.log('Saving homepage.')

        html = self.driver.page_source
        initial_data = find_value(html, 'var ytInitialData = ', 0, '\n').rstrip(';')
        videos = find_jsons(initial_data, '"videoRenderer":{')

        recs_data = []
        recs_ids = []
        for i in range(len(videos)):
            if i > MAX_RECS-1:
                break

            video = videos[i]
            video_id = video['videoId']
            channel_id = video['longBylineText']['runs'][0]['navigationEndpoint']['browseEndpoint']['browseId']
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
        self.__load_videopage(vid_id)
        time.sleep(LOAD_BUFFER_SECONDS)
        self.__save_videopage(vid_id)
        duration = self.__get_videopage_seconds()
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
        # Add it to our disliked videos list for later un-disliking
        url = self.driver.current_url
        video_id = url[len('https://www.youtube.com/watch?v='):]
        self.disliked_videos.add(video_id)

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
            except (NoSuchElementException, TimeoutException):
                counter += 1
                if counter > 5:
                    self.log('All attempts failed.')
                    raise
        self.log('All attempts failed.')
        raise RuntimeError(f'All attempts failed.')

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
        WebDriverWait(self.driver, 30).until(
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
        if 'level' not in row:
            row['level'] = self.level
        if 'time' not in row:
            row['time'] = datetime.datetime.now()
        return row

    def __write_recs(self, recs):
        """
        Write recommendations list into csv
        """
        assert (len(recs) > 0)
        recs_df = pd.DataFrame(recs)
        append_df(recs_df, self.results_filepath, False)

    def delete_most_recent(self):
        history_url = 'https://www.youtube.com/feed/history'

        self.log('Loading history page.')
        self.driver.get(history_url)

        time.sleep(5)

        WebDriverWait(self.driver, 30).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'div#contents'))
        )
        contents = self.driver.find_element(By.CSS_SELECTOR, 'div#contents')

        self.log('Deleting most recent.')
        button = contents.find_element(By.CSS_SELECTOR, 'button')
        button.click()

    def dislike_recommended(self):
        unwanted_video = self.scrub_homepage()
        time.sleep(5)
        if unwanted_video:
            unwanted_video.click()
            time.sleep(5)
            self.dislike_video()

    # Implementing this after realizing you can do "tell us why" --> "don't like video"
    #   after clicking on the actual not interested button
    def not_interested(self):
        found = self.menu_service('not interested')
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

    def no_channel(self):
        self.menu_service('no channel')

    def menu_service(self, action):
        unwanted_video = self.scrub_homepage()
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

    def scrub_homepage(self):
        """
        Load the homepage
        """
        # assert(self.driver.current_url == 'https://www.youtube.com')

        self.log('Checking homepage for video from unwanted channel.')

        html = self.driver.page_source
        initial_data = find_value(html, 'var ytInitialData = ', 0, '\n').rstrip(';')
        videos = find_jsons(initial_data, '"videoRenderer":{')

        unwanted_video_id = None
        for i in range(len(videos)):
            video = videos[i]
            video_id = video['videoId']
            channel_id = video['longBylineText']['runs'][0]['navigationEndpoint']['browseEndpoint']['browseId']
            if channel_id in self.unwanted_channels:
                self.log('Found video {0} from unwanted channel {1}.'.format(video_id, channel_id))
                unwanted_video_id = video_id
                break
            elif self.TEST and i == 3:
                self.log('TEST: Pretending that the fourth video ({0}, {1}) matches'.format(video_id, channel_id))
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
