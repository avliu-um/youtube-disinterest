import datetime
import os.path

import pandas as pd

from googleapiclient.discovery import build
from util import append_df

DEVELOPER_KEY = 'AIzaSyD2N0qxNJtj3NKT2DBursxa6kzA6DZBC_Y'
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'


def get_recommendations(vid):
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)
    request = youtube.search().list(
        part="snippet",
        relatedToVideoId=vid,
        type="video"
    )
    response = request.execute()

    results = []
    rec_ids = []
    for i in range(len(response['items'])):
        item = response['items'][i]
        result_vid = item['id']['videoId']
        try:
            result_cid = item['snippet']['channelId']
        # Sometimes the API will recommend a video from a channel that is no longer available
        except KeyError:
            result_cid = None
        rec_data = {'video_id': result_vid, 'channel_id': result_cid, 'rank': i, 'component': 'api',
                    'time': datetime.datetime.now(), 'parent_id': vid}
        rec_ids.append(result_vid)
        results.append(rec_data)

    recs_df = pd.DataFrame(results)
    append_df(recs_df, os.path.join('.', 'results', 'api.csv'), False)

    print('Recommended videos: {0}'.format(rec_ids))


def main():
    videos = [
        "3UwtCFh7SAc"
    ]
    for video in videos:
        get_recommendations(video)


if __name__ == '__main__':
    main()
