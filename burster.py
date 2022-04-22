# -*- coding: utf-8 -*-


from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementNotInteractableException, \
    ElementClickInterceptedException

import sys, os, time, json, logging, re, datetime
import pandas as pd

from util import find_value, find_json, find_jsons, append_df

# 30 minutes suggested (Tomlein et al. 2021)
MAX_WATCH_SECONDS = 1800
LOAD_BUFFER_SECONDS = 10


# Much of this code is inspired by Siqi Wu's YouTube Polarizer: https://github.com/avalanchesiqi/youtube-polarizer
class Burster(object):

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

            self.account_username = profile['account_username']
            self.account_password = profile['account_password']

            self.has_account = False
            if self.account_username and self.account_password:
                self.has_account = True

            self.seed_videos = profile['seed_videos']
            self.seed_category = profile['seed_category']
            self.burst_videos = profile['burst_videos']
            self.burst_category = profile['burst_category']
            self.burst_method = profile['burst_method']
            self.limit_type = profile['limit_type']
            self.limit_number = profile['limit_number']
            self.run_id = profile['run_id']
            self.chrome_arguments = profile['chrome_arguments']

        self.phase = "create"
        self.level = 0

        if 'filename' in profile.keys():
            filename = profile['filename']
        else:
            # e.g. 'test.yt.username' --> 'test-yt-username'
            filename = self.account_username
        filename = '{0}_{1}'.format(filename, self.run_id).replace('.', '-')
        self.results_filepath = os.path.join('.', 'results', '{0}.csv'.format(filename))
        self.log_filepath = os.path.join('.', 'logs', '{0}.log'.format(filename))

        open(self.results_filepath, 'x')
        self.logger = __get_logger(self.log_filepath)
        self.driver = __get_driver(self.chrome_arguments)

    def log(self, message):
        """
        Print and log the same message
        """
        self.logger.info(message)
        print(message)

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
        # yt_channel_url = 'https://www.youtube.com/channel/'

        # Wait until everything's loaded
        WebDriverWait(self.driver, 30).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'div#contents'))
        )
        contents = self.driver.find_element(By.CSS_SELECTOR, 'div#contents')
        # Get ALL video box thingys (notice we use find_elements, not find_element)
        recs = contents.find_elements(By.CSS_SELECTOR, 'div#content')

        recs_data = []
        recs_ids = []
        rank = 0
        for rec in recs:
            # 0 based indexing
            if rank > num_homepage_recs-1:
                break
            try:
                video_link = rec.find_element(By.CSS_SELECTOR, 'a[href*="/watch?v="]').get_attribute('href')
                # We don't get the channel because we discovered that it can show up as 'c', 'channel', or 'user'
                # channel_link = rec.find_element(By.CSS_SELECTOR, 'a[href*="/c/"]').get_attribute('href')
            except NoSuchElementException:
                continue
            video_id = video_link[len(yt_video_url):]
            # channel_id = channel_link[len(yt_channel_url):]
            rec_data = {'video_id': video_id, 'rank': rank, 'component': 'homepage'}
            rec_data = self.__attach_context(rec_data)
            recs_data.append(rec_data)
            recs_ids.append(video_id)
            rank += 1

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

    def __save_videopage(self, parent_id):
        """
        Find and write recommendations on the videopage (both video ID's and channel ID's)
        Examines the js code (rather than raw html) because channel ID's are only available there
        """
        max_recs = 10

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
            if rank > max_recs-1:
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
                            'parent_video_id': parent_id}
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
        self.log('Watching video for {0} seconds.'.format(watch_seconds))
        time.sleep(watch_seconds)

    # Modified from Tomlein et al. (2021)
    def video_action(self, action):
        """
        Attempt the 'action' of pressing one of the buttons right below the video screen
        By 'action' we mean 'like', 'dislike', or 'subscribe'
        """
        counter = 1
        max_tries = 5

        self.log('Attempting to press the {0} button.'.format(action))
        while counter < max_tries:
            try:
                success = self.__interact_with_action_button(action)
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
    def __interact_with_action_button(self, action):
        """
        Get and click on the button (if not clicked on already)
        """
        button, already_pressed = self.__get_action_button(action)
        if already_pressed:
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
        if 'bot_id' not in row:
            row['bot_id'] = self.account_username
        if 'phase' not in row:
            row['phase'] = self.phase
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



    def delete_video(self):
        history_url = 'https://www.youtube.com/feed/history'

        self.log('Loading history page.')
        self.driver.get(history_url)

        time.sleep(5)

        WebDriverWait(self.driver, 30).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'div#contents'))
        )
        contents = self.driver.find_element(By.CSS_SELECTOR, 'div#contents')

        button = contents.find_element(By.CSS_SELECTOR, 'button')
        button.click()

        time.sleep(5)

    def dislike_recommended(self, unwanted_channels):
        unwanted_video = self.scrub_homepage(unwanted_channels)
        time.sleep(5)
        if unwanted_video:
            unwanted_video.click()
            time.sleep(5)
            self.video_action('dislike')
        time.sleep(5)

    def menu_service(self, unwanted_channels, action):
        unwanted_video = self.scrub_homepage(unwanted_channels)
        time.sleep(5)
        if unwanted_video:
            # Click the three dots
            menu = unwanted_video.find_element(By.CSS_SELECTOR, 'ytd-menu-renderer')
            menu.click()

            time.sleep(5)

            # Click not interested button
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
                    found = True
                    break
            if not found:
                self.log('Button not found!')

            time.sleep(5)

    def scrub_homepage(self, unwanted_channels):
        """
        Load the homepage
        """
        homepage_url = 'https://www.youtube.com'

        self.log('Loading homepage.')
        self.driver.get(homepage_url)

        html = self.driver.page_source
        initial_data = find_value(html, 'var ytInitialData = ', 0, '\n').rstrip(';')
        videos = find_jsons(initial_data, '"videoRenderer":{')

        # If true, we try and scrub the first video that comes up
        TEST = True

        unwanted_video_id = None
        for i in range(len(videos)):
            video = videos[i]
            video_id = video['videoId']
            channel_id = video['longBylineText']['runs'][0]['navigationEndpoint']['browseEndpoint']['browseId']
            if (TEST and i == 3) or (channel_id in unwanted_channels):
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

        return None



