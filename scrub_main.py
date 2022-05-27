from scrubber import Scrubber
import time
import argparse, json


# scrub_iter_limit: Cap on the number of scrubbing actions
def scrub_experiment(attributes, scrub_iter_limit=40):
    bot = Scrubber(**attributes)

    try:
        bot.log('BEGIN!\n')
        setup(bot)
        time.sleep(5)
        stain(bot)
        time.sleep(5)
        scrub(bot, scrub_iter_limit)
        time.sleep(5)
        teardown(bot)
        bot.log('\nDONE!')
    except:
        bot.fail_safely()
    finally:
        bot.write_s3()


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


# scrub_iter_limit is the limit on the number of scrub iterations for the rec-based scrubbing strategies
def scrub(bot, scrub_iter_limit=40):

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
            # Usually silent, but allows for more control when testing
            if bot.phase_level > scrub_iter_limit:
                break
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
        # If you delete a video from watch history it deletes ALL occurences of that video
        for i in range(len(set(bot.staining_videos))):
            if bot.phase_level > scrub_iter_limit:
                break
            bot.log('Phase level: {0}'.format(bot.phase_level))
            bot.load_and_save_homepage()
            time.sleep(5)
            bot.delete_most_recent()
            time.sleep(5)
            bot.phase_level += 1
            bot.level += 1
    elif bot.scrubbing_strategy == 'dislike':
        for seed_vid in bot.staining_videos:
            if bot.phase_level > scrub_iter_limit:
                break
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
        for i in range(scrub_iter_limit):
            bot.log('Phase level: {0}'.format(bot.phase_level))
            bot.load_and_save_homepage()
            time.sleep(5)
            bot.dislike_recommended()
            time.sleep(5)
            bot.phase_level += 1
            bot.level += 1
    elif bot.scrubbing_strategy == 'not interested':
        for i in range(scrub_iter_limit):
            bot.log('Phase level: {0}'.format(bot.phase_level))
            bot.load_and_save_homepage()
            time.sleep(5)
            bot.not_interested()
            time.sleep(5)
            bot.phase_level += 1
            bot.level += 1
    elif bot.scrubbing_strategy == 'no channel':
        for i in range(scrub_iter_limit):
            bot.log('Phase level: {0}'.format(bot.phase_level))
            bot.load_and_save_homepage()
            time.sleep(5)
            bot.no_channel()
            time.sleep(5)
            bot.phase_level += 1
            bot.level += 1

    # Control
    elif bot.scrubbing_strategy == 'none':
        for i in range(scrub_iter_limit):
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--community', type=str, required=True)
    parser.add_argument('--scrubbing_strategy', type=str, required=True)
    parser.add_argument('--note', type=str)
    parser.add_argument('--staining_videos_csv', type=str, required=True)
    parser.add_argument('--scrubbing_extras_csv', type=str, required=False,
                        help='Required if strategy is rec-based')
    parser.add_argument('--account_username', type=str, required=True)
    parser.add_argument('--account_password', type=str, required=True)
    args = parser.parse_args()

    attributes = vars(args)

    scrub_experiment(attributes)


if __name__ == '__main__':
    main()
