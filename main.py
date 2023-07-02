import logging
import sys

from Scraper.TwitchScraper import TwitchScraper
from config import API_KEY, API_SECRET, API_TOKEN

if __name__ == '__main__':
    logging.basicConfig(filename='api_log.log', encoding='utf-8', level=logging.INFO)

    if len(sys.argv) < 2:
        print('Username required!')
        exit(-1)

    twitchScraper: TwitchScraper = TwitchScraper(API_KEY, API_SECRET, API_TOKEN)

    broadcaster: str = twitchScraper.get_user(sys.argv[1])
    twitchScraper.get_all_clips(broadcaster)
