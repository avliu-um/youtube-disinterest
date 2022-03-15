from burster import Burster
import time
import argparse


def burst_experiment(profile_filepath):
    bot = Burster(profile_filepath)
    if bot.has_account:
        bot.login()

    bot.log('Creating a filter bubble.')

    for seed_vid in bot.seed_videos:
        bot.load_and_save_homepage()
        time.sleep(5)
        duration = bot.load_and_save_videopage(seed_vid)
        bot.watch_video(duration)
        bot.level += 1

    bot.log('Moving to bursting stage.')

    bot.phase = "burst"
    bot.level = 0
    for burst_vid in bot.burst_videos:
        time.sleep(5)
        bot.load_and_save_homepage()
        time.sleep(5)
        duration = bot.load_and_save_videopage(burst_vid)
        time.sleep(5)
        if bot.burst_method == "watch":
            bot.watch_video(duration)
        elif bot.burst_method == 'like' or \
                bot.burst_method == 'dislike' or \
                bot.burst_method == 'subscribe':
            bot.video_action(bot.burst_method)
        else:
            bot.log('Burst method {0} not implemented yet!!!'.format(bot.burst_method))
            raise NotImplementedError
        bot.level += 1

    bot.log('Done.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--filepath', type=str, required=True,
                        help='The filepath to the configuration file')
    args = parser.parse_args()
    filepath = args.filepath

    burst_experiment(filepath)


if __name__ == '__main__':
    main()
