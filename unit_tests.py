from scrubber import Scrubber
from scrub_main import scrub_experiment
import os
import time
import pandas as pd

from selenium.webdriver.common.by import By
import re


default_attributes = {
        'community': 'testing',
        'scrubbing_strategy': 'dislike recommendation',
        'note': '',
        'staining_videos_csv': 'communities/testing/samples/videos_non_existent.csv',
        'scrubbing_extras_csv': 'communities/testing/placeholder_channels.csv',
        'account_username': 'sean.carter.99.test',
        'account_password': '99problems'
}

# Attempting to dislike a video that we know is inappropriate
# Should log error message, save the html, and move on
def test_dislike_inappropriate():
    attributes = {
        'community': 'testing',
        'scrubbing_strategy': 'dislike',
        'note': 'inappropriate',
        'staining_videos_csv': 'communities/testing/samples/videos_inappropriate.csv',
        'account_username': 'sean.carter.99.test',
        'account_password': '99problems'
    }
    bot = Scrubber(**attributes)
    bot.login()
    time.sleep(5)

    bot.load_and_save_videopage(bot.staining_videos[0])
    time.sleep(5)
    bot.dislike_video()
    time.sleep(5)


def test_was_login_successful():
    attributes = {
        'community': 'testing',
        'scrubbing_strategy': 'none',
        'note': 'login',
        'staining_videos_csv': 'communities/testing/samples/videos_non_existent.csv',
        'account_username': 'sean.carter.99.test',
        'account_password': '99problems'
    }
    bot = Scrubber(**attributes)

    time.sleep(5)
    assert(not bot.was_login_successful())
    time.sleep(5)
    bot.youtube_login()
    assert(bot.was_login_successful())


def test_many_fails():
    attributes = {
        'community': 'testing',
        'scrubbing_strategy': 'none',
        'note': 'many-fails',
        'staining_videos_csv': 'communities/testing/samples/videos_non_existent.csv',
        'account_username': 'sean.carter.99.test',
        'account_password': '99problems'
    }
    bot = Scrubber(**attributes)

    for seed_vid in bot.staining_videos:
        duration = bot.load_and_save_videopage(seed_vid)
        bot.watch_video(duration)
    assert(bot.fail_count > 1)
    assert(len(os.listdir('outputs/fails')) > 1)


# Should log error message and save the html (twice), and move on
# Simoltaneously test many failures, and writing to s3
def test_delete_empty():
    attributes = {
        'community': 'testing',
        'scrubbing_strategy': 'delete',
        'note': 'delete-empty',
        'staining_videos_csv': 'communities/testing/samples/videos_non_existent.csv',
        'account_username': 'sean.carter.99.test',
        'account_password': '99problems'
    }
    bot = Scrubber(**attributes)
    bot.login()
    time.sleep(5)
    bot.clear_history()
    time.sleep(5)

    bot.delete_most_recent()
    time.sleep(5)
    bot.delete_most_recent()
    time.sleep(5)

    bot.write_s3()

def test_delete():
    attributes = {
        'community': 'testing',
        'scrubbing_strategy': 'delete',
        'note': 'delete-empty',
        'staining_videos_csv': 'communities/testing/samples/videos_non_existent.csv',
        'account_username': 'sean.carter.99.test',
        'account_password': '99problems'
    }
    bot = Scrubber(**attributes)

    bot.login()
    time.sleep(5)

    bot.delete_most_recent()
    time.sleep(5)
    bot.delete_most_recent()
    time.sleep(5)

    bot.write_s3()


def test_not_interested():
    attributes = {
        'community': 'testing',
        'scrubbing_strategy': 'no channel',
        'note': '',
        'staining_videos_csv': 'communities/testing/samples/videos_non_existent.csv',
        'scrubbing_extras_csv': 'communities/testing/placeholder_channels.csv',
        'account_username': 'sean.carter.99.test',
        'account_password': '99problems'
    }
    bot = Scrubber(**attributes)

    bot.login()

    bot.no_channel(sim_rec_match=True)

    time.sleep(5)


def test_dislike_recommended():
    attributes = default_attributes
    bot = Scrubber(**attributes)

    bot.login()

    bot.load_and_save_homepage()
    bot.dislike_recommended(sim_rec_match=True)
    time.sleep(5)


def test_rec_scrub_top_news():
    attributes = default_attributes
    attributes['scrubbing_extras_csv'] = 'communities/politics/channels_left.csv'
    bot = Scrubber(**attributes)

    bot.driver.get('file:///Users/avliu/Documents/Research/youtube_audits/burst/bad_webpages/fail_politics-left_no-channel_0_0.html')

    bot.no_channel(sim_rec_match=True)
    time.sleep(5)

def test_delete_issue():
    attributes = default_attributes
    bot = Scrubber(**attributes)

    bad_delete_url = 'file:///Users/avliu/Documents/Research/youtube_audits/burst/bad_webpages/fail_politics-left_delete_2_11.html'

    bot.delete_most_recent(bad_delete_url)
    time.sleep(5)

def test_rec_scrub_issue():
    attributes = default_attributes

    attributes['scrubbing_extras_csv'] = 'communities/politics/channels_left.csv'

    bot = Scrubber(**attributes)

    bad_webpage = 'file:///Users/avliu/Documents/Research/youtube_audits/burst/bad_webpages/fail_politics-left_dislike-recommendation_0_1.html'
    bot.driver.get(bad_webpage)

    bot.not_interested()
    time.sleep(5)


def test_homepage():
    attributes = default_attributes
    attributes['note'] = 'homepage'
    bot = Scrubber(**attributes)
    bot.login()
    bot.load_and_save_homepage()


def full_strategy_tests():
    my_row = 6

    runs_filepath = 'runs/strategy_test_runs.csv'
    runs = pd.read_csv(runs_filepath).to_dict('index')
    attributes = runs[my_row]

    strategy = attributes['scrubbing_strategy']
    print('testing strategy: {0}'.format(strategy))

    scrub_experiment(attributes, scrub_iter_limit=2)


def run_real():
    attributes = {
        'community': 'alt-right',
        'scrubbing_strategy': 'none',
        'note': '0',
        'staining_videos_csv': 'communities/alt-right/samples/videos_22.csv',
        'account_username': 'sean.carter.99.test',
        'account_password': '99problems'
    }
    scrub_experiment(attributes)


def test_undetected_chromedriver():
    import undetected_chromedriver as uc
    driver = uc.Chrome()
    driver.get('https://nowsecure.nl')
    time.sleep(10)

def test_dislike():
    import undetected_chromedriver as uc
    driver = uc.Chrome()
    driver.get('file:///Users/avliu/Documents/Research/youtube_audits/other/antitheist_outputs/10:08:23/fail_antitheist_dislike_1_0.html')
    time.sleep(5)

    buttons = driver.find_elements(By.CSS_SELECTOR, 'div#menu-container button.yt-icon-button')
    time.sleep(3)

    for elem in buttons:
        label = elem.get_attribute('aria-label')
        if re.search('\A[Dd]islike', label):
            pressed = elem.get_attribute('aria-pressed') == 'true'
            return elem, pressed


if __name__ == '__main__':
    test_delete_issue()
