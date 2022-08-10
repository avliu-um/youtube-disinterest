from scrubber import Scrubber
import time
import argparse, json
from selenium.webdriver.common.by import By


# Functions run across ALL bots

# Designed to help with first login of audit, where we have to deal with the email page

def first_login(attributes):
    bot = Scrubber(**attributes)
    
    bot.youtube_login_2()
    time.sleep(5)

    try: 
        email_button = bot.driver.find_element(By.CSS_SELECTOR, 'div.vxx8jf')
        email_button.click()
        time.sleep(5)
        bot.log('successful login')
    except:
        bot.log('Unable to find the verification email button', True)
    finally:
        # Wait on my go to stop 
        # input('Input any button to end this \n')
        
        # 2 hours * 60 minutes * 60 seconds
        time.sleep(7200)


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
    parser.add_argument('--s3_bucket', type=str, required=False,
                        help='default is "youtube-audit-bucket"')

    args = parser.parse_args()

    attributes = vars(args)

    first_login(attributes)


if __name__ == '__main__':
    main()
