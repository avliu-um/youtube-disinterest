from scrubber import Scrubber
import time
import argparse
import os

TEST = True

# This is the iteration limit for scrubbing actions that involve interacting with recommendations
# TODO: Pretest
REC_ITER_LIMIT = 40
# This is the iteration limit for the control group that does nothing but refresh the homepage
CONTROL_ITER_LIMIT = 40

if TEST:
    REC_ITER_LIMIT = 1
    CONTROL_ITER_LIMIT = 1


def scrub_experiment(bot):
    bot.log('SETUP PHASE')

    if bot.has_account:
        bot.login()
    time.sleep(5)

    bot.log('\nSTAIN PHASE')
    bot.set_phase('stain')

    for seed_vid in bot.staining_videos:
        bot.load_and_save_homepage()
        time.sleep(5)
        duration = bot.load_and_save_videopage(seed_vid)
        bot.watch_video(duration)
        bot.phase_level += 1
    # Used in the teardown phase
    final_stain_vid = bot.staining_videos[-1]

    bot.log('\nSCRUB PHASE')
    bot.set_phase('scrub')

    # Watch-based
    if bot.scrubbing_strategy == 'watch':
        for burst_vid in bot.scrubbing_videos:
            bot.load_and_save_homepage()
            time.sleep(5)
            duration = bot.load_and_save_videopage(burst_vid)
            time.sleep(5)
            bot.watch_video(duration)

    # History-based
    elif bot.scrubbing_strategy == 'delete':
        for i in range(len(bot.staining_videos)):
            bot.load_and_save_homepage()
            time.sleep(5)
            bot.delete_most_recent()
            time.sleep(5)
    elif bot.scrubbing_strategy == 'dislike':
        for seed_vid in bot.staining_videos:
            bot.load_and_save_homepage()
            time.sleep(5)
            bot.load_and_save_videopage(seed_vid)
            time.sleep(5)
            bot.dislike_video()

    elif bot.scrubbing_strategy == 'none':
        for i in range(CONTROL_ITER_LIMIT):
            bot.load_and_save_homepage()
            time.sleep(5)

    # Recommendation-based
    elif bot.scrubbing_strategy == 'dislike recommendation':
        for i in range(REC_ITER_LIMIT):
            bot.load_and_save_homepage()
            time.sleep(5)
            bot.dislike_recommended()
            time.sleep(5)
    elif bot.scrubbing_strategy == 'not interested':
        for i in range(REC_ITER_LIMIT):
            bot.load_and_save_homepage()
            time.sleep(5)
            bot.menu_service('not interested')
            time.sleep(5)
    elif bot.scrubbing_strategy == 'no channel':
        for i in range(REC_ITER_LIMIT):
            bot.load_and_save_homepage()
            time.sleep(5)
            bot.menu_service('no channel')
            time.sleep(5)

    else:
        raise NotImplementedError

    bot.log('\nTEARDOWN PHASE')
    bot.set_phase('teardown')

    bot.load_and_save_homepage()
    bot.load_and_save_videopage(final_stain_vid)

    if not TEST:
        bot.clear_history()
    if bot.scrubbing_strategy == 'dislike' or bot.scrubbing_strategy == 'dislike recommended':
        bot.clear_disliked_videos()

    bot.log('\nDONE!')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--filepath', type=str, required=True,
                        help='The filepath to the configuration file')
    args = parser.parse_args()
    bot_filepath = args.filepath
    bot = Scrubber(bot_filepath)

    try:
        scrub_experiment(bot)
    except:
        fail_filepath = os.path.join('.', 'failures', bot.name + '.html')
        bot.log('Error! Saving html to ' + fail_filepath, True)

        html = bot.driver.page_source
        with open(fail_filepath, 'w') as f:
            f.write(html)


if __name__ == '__main__':
    main()
