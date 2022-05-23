from scrubber import Scrubber
import os
import time


def test_was_login_successessful():
    good_filepath = 'profiles/unit_tests/login.json'
    bot = Scrubber(good_filepath)
    time.sleep(5)
    assert(not bot.was_login_successful())
    time.sleep(5)
    bot.youtube_login()
    assert(bot.was_login_successful())


def test_many_fails():
    test_filepath = 'profiles/unit_tests/many_fails.json'
    bot = Scrubber(test_filepath)

    for seed_vid in bot.staining_videos:
        duration = bot.load_and_save_videopage(seed_vid)
        bot.watch_video(duration)

    assert(bot.fail_count > 1)
    assert(len(os.listdir('outputs/fails')) > 1)


if __name__ == '__main__':
    os.makedirs('outputs')
    os.makedirs('outputs/fails')
    test_was_login_successessful()
