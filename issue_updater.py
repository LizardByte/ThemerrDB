# standard imports
import argparse
import json
import os
import re

# lib imports
import requests
import youtube_dl

# load env
from dotenv import load_dotenv
load_dotenv()

item = dict()
item_type = None
item_filenames = []

# todo - this is no longer working for igdb, need to use igdb api
# default headers, to avoid potential 403 errors or the like
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:108.0) Gecko/20100101 Firefox/108.0"}


def check_igdb(data: dict):
    print('Checking igdb')
    url = data['igdb_url'].strip()
    print(f'igdb_url: {url}')

    game_slug = re.search(r'https://www\.igdb.com/games/(.+)/*.*', url).group(1)
    print(f'game_slug: {game_slug}')

    response = requests.get(url=url, headers=headers)  # requires headers to be faked

    if response.status_code != 200:
        raise Exception(f'igdb_url returned a non 200 status code of: {response.status_code}')

    game_id = re.search(r'data-game-id=\"(\d+)\"', str(response.content)).group(1)
    print(f'igdb_id: {game_id}')

    item['igdb_id'] = game_id
    item_filenames.append(os.path.join('igdb', f'{game_id}.json'))  # set the item filename


def check_themoviedb(data: dict):
    print('Checking themoviedb')
    url = data['themoviedb_url'].strip()
    print(f'themoviedb_url: {url}')

    themoviedb_id = re.search(r'https://www\.themoviedb.org/movie/(\d+)-*.*', url).group(1)
    print(f'themoviedb_id: {themoviedb_id}')

    # get the data from tmdb api
    url = f'https://api.themoviedb.org/3/movie/{themoviedb_id}?api_key={os.environ["TMDB_API_KEY_V3"]}'
    response = requests.get(url=url)
    json_data = response.json()

    if response.status_code != 200:
        raise Exception(f'themoviedb_url returned a non 200 status code of: {response.status_code}')

    # update the item dictionary
    item.update(json_data)
    item_filenames.append(os.path.join('themoviedb', f'{json_data["id"]}.json'))  # set the item filename
    try:
        item_filenames.append(os.path.join('imdb', f'{json_data["imdb_id"]}.json'))  # set the item filename
    except KeyError as e:
        print(f'Error getting imdb_id: {e}')


def check_youtube(data: dict):
    url = data['youtube_theme_url'].strip()

    # url provided, now process it using youtube_dl
    youtube_dl_params = dict(
        outmpl='%(id)s.%(ext)s',
        youtube_include_dash_manifest=False,
    )

    ydl = youtube_dl.YoutubeDL(params=youtube_dl_params)

    with ydl:
        result = ydl.extract_info(
            url=url,
            download=False  # We just want to extract the info
        )
        if 'entries' in result:
            # Can be a playlist or a list of videos
            video_data = result['entries'][0]
        else:
            # Just a video
            video_data = result

    webpage_url = video_data['webpage_url']

    item['youtube_theme_url'] = webpage_url  # add the url to the item dictionary


def process_submission():
    with open(file='submission.json') as file:
        data = json.load(file)

    return data


if __name__ == '__main__':
    # setup arguments using argparse
    parser = argparse.ArgumentParser(description="Add theme song to database.")
    parser.add_argument('--add_game', '--add-game', action='store_true', help='Add Game theme song.')
    parser.add_argument('--add_movie', '--add-movie', action='store_true', help='Add Movie theme song.')

    args = parser.parse_args()

    if not args.add_game and not args.add_movie:
        raise Exception('"--add_game" or "--add_movie" arg must be passed.')
    elif args.add_game and args.add_movie:
        raise Exception('"--add_game" or "--add_movie" arg must be passed, not both.')

    required_keys = ['youtube_theme_url']

    # process submission file
    submission = process_submission()

    if args.add_game:
        item_type = 'game'
        check_igdb(data=submission)  # check validity of IGDB url and update item dictionary
        required_keys.append('igdb_id')

    elif args.add_movie:
        item_type = 'movie'
        check_themoviedb(data=submission)
        required_keys.append('id')

    # check validity of provided YouTube url and update item dictionary
    check_youtube(data=submission)

    for key in required_keys:
        if key not in item:
            raise Exception(f'Final item is missing required key: {key}')

    print(item)
    print(f'item will be saved to the following locations: {item_filenames}')

    for filename in item_filenames:
        destination_file = os.path.join(f'{item_type}s', filename)
        destination_dir = os.path.dirname(destination_file)

        print(destination_dir)

        os.makedirs(name=destination_dir, exist_ok=True)  # create directory if it doesn't exist

        with open(destination_file, "w") as f:
            f.write(json.dumps(item))
