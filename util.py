# -*- coding: utf-8 -*-

import json, re
import pandas as pd
import boto3


def find_value(html, key, num_chars=2, separator='"'):
    """ Find matched string in html page.
    """
    if html.find(key) == -1:
        return ''
    else:
        pos_begin = html.find(key) + len(key) + num_chars
        pos_end = html.find(separator, pos_begin)
        return html[pos_begin: pos_end]


def find_json(json_str, key):
    """ Find a valid json object based on key in the string.
    """
    if json_str.find(key) == -1:
        return {}
    else:
        pos_end = pos_begin = json_str.find(key) + len(key)
        num_bracket = 1

        # MOTIVATING ISSUE: Videos with brackets in them mess up the string parsing!
        #    e.g. https://www.youtube.com/watch?v=TyX0twnnyHA
        in_quotes = False

        for pos_idx in range(pos_begin, len(json_str)):

            curr_char = json_str[pos_idx]
            if curr_char == '"':
                # Make sure not a literal quote, e.g. quote used in the title
                # pos_idx is an index of the ENTIRE js response, so not likely to be less than 2
                if json_str[pos_idx-1:pos_idx+1] != '\\"' and pos_idx > 1:
                    if not in_quotes:
                        in_quotes = True
                    else:
                        in_quotes = False

            if not in_quotes:
                if curr_char == '{':
                    num_bracket += 1
                elif curr_char == '}':
                    num_bracket -= 1
                    if num_bracket == 0:
                        pos_end = pos_idx
                        break

        return fix_json(json_str[pos_begin - 1: pos_end + 1])


def find_jsons(json_str, key):
    """ Find a list of multiple jsons that start with a given key
        e.g. "... 'a':[1,2,3], ... 'a':[4,5,6], ... 'a':[7,8,9] ... " --> [ [1,2,3], [4,5,6], [7,8,9] ]
    """
    answer = []
    if json_str.find(key) == -1:
        return []
    else:
        key_idx = json_str.find(key)
        while key_idx > -1:
            answer.append(find_json(json_str, key))
            shift_idx = key_idx + len(key)
            json_str = json_str[shift_idx:]
            key_idx = json_str.find(key)
    return answer


def search_dict(partial, key):
    if isinstance(partial, dict):
        for k, v in partial.items():
            if k == key:
                yield v
            else:
                for o in search_dict(v, key):
                    yield o
    elif isinstance(partial, list):
        for i in partial:
            for o in search_dict(i, key):
                yield o


def fix_json(json_str):
    """ Fix the json string because python json module cannot handle double quotes well.
    """
    while True:
        try:
            json_obj = json.loads(json_str)
            break
        except Exception as e:
            unexp = int(re.findall(r'\(char (\d+)\)', str(e))[0])
            while unexp >= 1:
                if json_str[unexp - 1] == '"':
                    json_str = json_str[: unexp - 1] + json_str[unexp:]
                    break
                unexp -= 1
    return json_obj


def append_df(df, existing_file_name, index):
    try:
        existing_df = pd.read_csv(existing_file_name)
    except pd.errors.EmptyDataError:
        existing_df = pd.DataFrame()
    # Non-overlapping columns are filled with NaN values
    final_df = pd.concat([existing_df, df])
    final_df.to_csv(existing_file_name, index=index)


def write_to_bucket(source, dest):
    # Make sure to configure ~/.aws/configure file
    s3 = boto3.resource('s3')
    s3.Bucket('youtube-audit').upload_file(source, dest)