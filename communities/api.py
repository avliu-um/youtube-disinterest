import datetime
import os.path
import pandas as pd
from googleapiclient.discovery import build
import boto3
import json


YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'
dev_key_file = './yt_api_dev_key.txt'
text_file = open(dev_key_file, "r")
DEVELOPER_KEY = text_file.read()
text_file.close()


def test():
    print('hi')


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


# TODO: Encorporate into request/response logic
def write_to_bucket(source, dest):
    # Make sure to configure ~/.aws/configure file
    s3 = boto3.resource('s3')
    s3.Bucket('youtube-audit').upload_file(source, dest)


def main():

    channels = [
        "UCfDdlNLRVb1h3_7Xh-WhL3w"
    ]
    for channel in channels:
        api_channel(channel)


if __name__ == '__main__':
    main()
