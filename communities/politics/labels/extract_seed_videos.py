import bz2, json
from collections import defaultdict


def main():
    cid_ideology_dict = {}
    cid_title_dict = {}
    cid_vid_view_dict = defaultdict(list)
    with bz2.BZ2File('./mbfc_usa_news_videos.json.bz2', 'r') as fin:
        for line in fin:
            line = line.decode('utf-8')
            video_json = json.loads(line.rstrip())
            vid = video_json['vid']
            channel_id = video_json['channel_id']
            media_title = video_json['media_title']
            media_ideology = video_json['media_ideology']
            view_count = int(video_json['view_count'])
            cid_title_dict[channel_id] = media_title
            cid_ideology_dict[channel_id] = media_ideology
            cid_vid_view_dict[channel_id].append((vid, view_count))

    num_video = 0
    with open('mbfc_seed_videos.json', 'w') as fout:
        for cid in cid_ideology_dict:
            fout.write('{0}\n'.format(json.dumps({'channel_id': cid,
                                                  'media_title': cid_title_dict[cid],
                                                  'media_ideology': cid_ideology_dict[cid],
                                                  'vid_view': list(cid_vid_view_dict[cid])}
                                                 )))
            num_video += len(cid_vid_view_dict[cid])
    print('we find {0} media and {1:,} seed videos'.format(len(cid_ideology_dict), num_video))


if __name__ == '__main__':
    main()
