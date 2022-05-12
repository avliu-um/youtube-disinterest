import datetime
import os.path

import pandas as pd

from googleapiclient.discovery import build
from util import append_df

YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'
dev_key_file = '../yt_api_dev_key.txt'
text_file = open(dev_key_file, "r")
DEVELOPER_KEY = text_file.read()
text_file.close()



# Search channel for videos
def api_search_channel(cid, order, video_duration, part="snippet", type="video", max_results=50):
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)
    request = youtube.search().list(
        part=part,
        order=order,
        type=type,
        channelId=cid,
        maxResults=max_results,
        videoDuration=video_duration
    )

def api_channel(cid, part="snippet,contentDetails,statistics"):
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)
    request = youtube.channels().list(
        part=part,
        id=cid
    )
    return execute_request(request)

def execute_request(request):
    response = request.execute()
    # TODO: WRITE REQUEST AND RESPONSE
    return response

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
