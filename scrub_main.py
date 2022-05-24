from scrubber import Scrubber
import time
import datetime
import argparse
import os
import json
from util import write_to_bucket

# This is the iteration limit for scrubbing actions that involve interacting with recommendations
SCRUB_ITER_LIMIT = 40


def setup(bot):

    bot.log('SETUP PHASE')

    bot.login()


def stain(bot):

    bot.log('\nSTAIN PHASE')
    bot.set_phase('stain')

    for seed_vid in bot.staining_videos:
        bot.log('Phase level: {0}'.format(bot.phase_level))
        bot.load_and_save_homepage()
        time.sleep(5)
        duration = bot.load_and_save_videopage(seed_vid)
        bot.watch_video(duration)
        bot.phase_level += 1
        bot.level += 1


def scrub(bot):

    bot.log('\nSCRUB PHASE')
    bot.set_phase('scrub')

    bot.phase_level = 0

    # videopage experiment stage 2
    bot.log('Phase level: {0}'.format(bot.phase_level))
    bot.log('Videopage experiment stage 2')
    bot.load_and_save_videopage(bot.videopage_experiment_vid)
    time.sleep(5)
    bot.phase_level += 1
    bot.level += 1

    # Watch-based
    if bot.scrubbing_strategy == 'watch':
        for burst_vid in bot.scrubbing_videos:
            bot.log('Phase level: {0}'.format(bot.phase_level))
            bot.load_and_save_homepage()
            time.sleep(5)
            duration = bot.load_and_save_videopage(burst_vid)
            time.sleep(5)
            bot.watch_video(duration)
            bot.phase_level += 1
            bot.level += 1

    # History-based
    elif bot.scrubbing_strategy == 'delete':
        for i in range(len(bot.staining_videos)):
            bot.log('Phase level: {0}'.format(bot.phase_level))
            bot.load_and_save_homepage()
            time.sleep(5)
            bot.delete_most_recent()
            time.sleep(5)
            bot.phase_level += 1
            bot.level += 1
    elif bot.scrubbing_strategy == 'dislike':
        for seed_vid in bot.staining_videos:
            bot.log('Phase level: {0}'.format(bot.phase_level))
            bot.load_and_save_homepage()
            time.sleep(5)
            bot.load_and_save_videopage(seed_vid)
            time.sleep(5)
            bot.dislike_video()
            bot.phase_level += 1
            bot.level += 1

    # Recommendation-based
    elif bot.scrubbing_strategy == 'dislike recommendation':
        for i in range(SCRUB_ITER_LIMIT):
            bot.log('Phase level: {0}'.format(bot.phase_level))
            bot.load_and_save_homepage()
            time.sleep(5)
            bot.dislike_recommended()
            time.sleep(5)
            bot.phase_level += 1
            bot.level += 1
    elif bot.scrubbing_strategy == 'not interested':
        for i in range(SCRUB_ITER_LIMIT):
            bot.log('Phase level: {0}'.format(bot.phase_level))
            bot.load_and_save_homepage()
            time.sleep(5)
            bot.not_interested()
            time.sleep(5)
            bot.phase_level += 1
            bot.level += 1
    elif bot.scrubbing_strategy == 'no channel':
        for i in range(SCRUB_ITER_LIMIT):
            bot.log('Phase level: {0}'.format(bot.phase_level))
            bot.load_and_save_homepage()
            time.sleep(5)
            bot.no_channel()
            time.sleep(5)
            bot.phase_level += 1
            bot.level += 1

    # Control
    elif bot.scrubbing_strategy == 'none':
        for i in range(SCRUB_ITER_LIMIT):
            bot.log('Phase level: {0}'.format(bot.phase_level))
            bot.load_and_save_homepage()
            time.sleep(5)
            bot.phase_level += 1
            bot.level += 1

    else:
        raise NotImplementedError


def teardown(bot):

    bot.log('\nTEARDOWN PHASE')
    bot.set_phase('teardown')

    bot.phase_level = 0

    # videopage experiment stage 3
    bot.log('Videopage experiment stage 3')
    bot.load_and_save_videopage(bot.videopage_experiment_vid)
    time.sleep(5)

    bot.clear_history()
    time.sleep(5)
    bot.clear_not_interested()
    time.sleep(5)
    bot.clear_likes_dislikes()
    time.sleep(5)
    bot.clear_subscriptions()
    time.sleep(5)


def scrub_experiment(bot):
    bot.log('BEGIN!\n')
    setup(bot)
    time.sleep(5)
    stain(bot)
    time.sleep(5)
    scrub(bot)
    time.sleep(5)
    teardown(bot)
    bot.log('\nDONE!')

# Legacy
# This parses arguments in a json under the profiles folder
# We've now moved to passing in attributes as a whole without parsing json
def parse_profile_json():
    parser = argparse.ArgumentParser()
    parser.add_argument('--filepath', type=str, required=True,
                        help='The filepath to the configuration file')
    args = parser.parse_args()
    bot_filepath = args.filepath

    with open(bot_filepath) as json_file:
        profile = json.load(json_file)

    scrubbing_extras = None
    if 'scrubbing_extras' in profile.keys():
        scrubbing_extras = profile['scrubbing_extras']

    bot = Scrubber(
        community=profile['community'],
        scrubbing_strategy=profile['scrubbing_strategy'],
        note=profile['note'],
        account_username=profile['account_username'],
        account_password=profile['account_password'],
        staining_videos_csv=profile['staining_videos'],
        scrubbing_extras_csv=scrubbing_extras
    )

    return bot

def main():
    # Creating the outputs directory
    os.makedirs('outputs')
    os.makedirs('outputs/fails')

    bot = parse_profile_json()

    try:
        scrub_experiment(bot)
    except:
        fail_filepath = bot.get_fail_filepath()
        bot.log('Error! Saving html to ' + fail_filepath, True)
        html = bot.driver.page_source
        with open(fail_filepath, 'w') as f:
            f.write(html)
        bot.fail_count += 1
    finally:
        # write failure(s), log, results
        dt = datetime.datetime.now().strftime('%Y-%m-%d/%H:%M:%S')
        write_to_bucket(bot.results_filepath, 'outputs/{0}/{1}'.format(dt, bot.results_filename))
        write_to_bucket(bot.log_filepath, 'outputs/{0}/{1}'.format(dt, bot.log_filename))
        for i in range(bot.fail_count):
            write_to_bucket(bot.get_fail_filepath(i), 'outputs/{0}/{1}'.format(dt, bot.get_fail_filename(i)))


if __name__ == '__main__':
    main()
