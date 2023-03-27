from googleapiclient.discovery import build
import pandas as pd

YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'
dev_key_file = 'yt_api_dev_key.txt'
text_file = open(dev_key_file, "r")
DEVELOPER_KEY = text_file.read()
text_file.close()


# TODO: Use
def list_to_csv(data, file):
    d = pd.DataFrame({'id': data})
    d.to_csv(file, header=False, index=False)


# Get video ids, along with title and description, from a certain channel
def videos_from_channel(channel, order, video_duration):
    videos = []
    response = api_search_channel(channel, order, video_duration)
    for video in response:
        vid = None
        title = None
        des = None
        if 'id' in video and 'videoId' in video['id']:
            vid = video['id']['videoId']
        if 'snippet' in video and 'title' in video['snippet']:
            title = video['snippet']['title']
        if 'snippet' in video and 'description' in video['snippet']:
            des = video['snippet']['description']
        row = {'vid': vid, 'cid': channel, 'title': title, 'description': des}
        videos.append(row)
    return videos


# Search channel for videos
def api_search_channel(cid, order, video_duration, part="snippet", response_type="video", max_results=50):
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)
    request = youtube.search().list(
        part=part,
        order=order,
        type=response_type,
        channelId=cid,
        maxResults=max_results,
        videoDuration=video_duration
    )
    return execute_request(request)


def channel_attributes(channels):
    subs = []
    descriptions = []
    available = []
    for cid in channels:
        items = api_channel(cid)
        sub = None
        des = None
        if items and len(items)>0:
            item = items[0]
            if 'statistics' in item.keys():
                if 'subscriberCount' in item['statistics'].keys():
                    sub = item['statistics']['subscriberCount']
            if 'snippet' in item.keys():
                if 'description' in item['snippet'].keys():
                    des = item['snippet']['description']
            subs.append(sub)
            descriptions.append(des)
            available.append(True)
        else:
            subs.append(None)
            descriptions.append(None)
            available.append(False)
    df = pd.DataFrame({
        'cid': channels,
        'subs': subscriptions,
        'description': descriptions,
        'available': available
    })
    df['subs'] = df['subs'].fillna(-1)
    df['subs'] = df['subs'].astype(int)
    return df


def api_channel(cid, part="snippet,contentDetails,statistics"):
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)
    request = youtube.channels().list(
        part=part,
        id=cid
    )
    return execute_request(request)


def execute_request(request):
    response = request.execute()

    # Write everything
    items = None 
    if 'items' in response.keys():
        items = response['items']

    return items


def main():

    channels = [
        "UCfDdlNLRVb1h3_7Xh-WhL3w"
    ]
    for channel in channels:
        api_channel(channel)


if __name__ == '__main__':
    main()
