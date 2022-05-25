from scrubber import Scrubber
from scrub_main import scrub_experiment
import os
import time
import pandas as pd


# Attempting to dislike a video that we know is inappropriate
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

    bot.load_and_save_videopage(bot.staining_videos[0])
    bot.dislike_video()


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

    bot.clear_history()
    bot.delete_most_recent()
    pass


def test_not_interested():
    attributes = {
        'community': 'testing',
        'scrubbing_strategy': 'not interested',
        'note': '',
        'staining_videos_csv': 'communities/testing/samples/videos_non_existent.csv',
        'scrubbing_extras_csv': 'communities/testing/placeholder_channels.csv',
        'account_username': 'sean.carter.99.test',
        'account_password': '99problems'
    }
    bot = Scrubber(**attributes, sim_rec_match=True)

    bot.login()

    bot.not_interested()

def test_dislike_recommended():
    attributes = {
        'community': 'testing',
        'scrubbing_strategy': 'dislike recommendation',
        'note': '',
        'staining_videos_csv': 'communities/testing/samples/videos_non_existent.csv',
        'scrubbing_extras_csv': 'communities/testing/placeholder_channels.csv',
        'account_username': 'sean.carter.99.test',
        'account_password': '99problems'
    }
    bot = Scrubber(**attributes, sim_rec_match=True)

    bot.login()

    bot.load_and_save_homepage()
    bot.dislike_recommended()
    time.sleep(5)


def full_strategy_tests():
    my_row = 2

    runs_filepath = 'runs/strategy_test_runs.csv'
    runs = pd.read_csv(runs_filepath).to_dict('index')
    attributes = runs[my_row]

    strategy = attributes['scrubbing_strategy']
    print('testing strategy: {0}'.format(strategy))

    bot = Scrubber(**attributes, sim_rec_match=True)

    scrub_experiment(bot, scrub_iter_limit=2)

if __name__ == '__main__':
    os.makedirs('outputs')
    os.makedirs('outputs/fails')
    test_dislike_recommended()
