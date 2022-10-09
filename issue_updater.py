# standard imports
import argparse
import json
import os
import re

# lib imports
from imdb import Cinemagoer
import requests
import youtube_dl

item = dict()
item_type = None
item_filenames = []

# default headers, to avoid potential 403 errors or the like
headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0"}


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


def check_imdb(data: dict):
    print('Checking imdb')
    url = data['imdb_url'].strip()
    print(f'imdb_url: {url}')

    ia = Cinemagoer()

    imdb_id = re.search(r'https://www\.imdb.com/title/(tt\d+)/*.*', url).group(1)
    print(f'imdb_id: {imdb_id}')

    # if the following doesn't raise an exception, we have a valid imdb id
    imdb_movie = ia.get_movie(movieID=imdb_id)

    if imdb_id == f'tt{imdb_movie.getID()}':
        item['imdb_id'] = imdb_id
        item_filenames.append(os.path.join('imdb', f'{imdb_id}.json'))  # set the item filename
    else:
        raise Exception(f'IMDB id ({imdb_id}) found in url does not match returned id: {imdb_movie.getID()}')


def check_themoviedb(data: dict):
    print('Checking themoviedb')
    url = data['themoviedb_url'].strip()
    print(f'themoviedb_url: {url}')

    themoviedb_id = re.search(r'https://www\.themoviedb.org/movie/(\d+)-*.*', url).group(1)
    print(f'themoviedb_id: {themoviedb_id}')

    # todo - gain access to themoviedb api and validate that we have a proper id
    #  for now just check if we get a valid response
    response = requests.get(url=url, headers=headers)

    if response.status_code != 200:
        raise Exception(f'themoviedb_url returned a non 200 status code of: {response.status_code}')

    item['themoviedb_id'] = themoviedb_id
    item_filenames.append(os.path.join('themoviedb', f'{themoviedb_id}.json'))  # set the item filename


def check_thetvdb(data: dict):
    print('Checking thetvdb')
    url = data['thetvdb_url'].strip()
    print(f'thetvdb_url: {url}')

    thetvdb_slug = re.search(r'https://thetvdb.com/movies/(.+)/*', url).group(1)
    print(f'thetvdb_slug: {thetvdb_slug}')

    response = requests.get(url=url, headers=headers)

    if response.status_code != 200:
        raise Exception(f'tvdb_url returned a non 200 status code of: {response.status_code}')

    thetvdb_id = re.search(r'name=\"id\"\s*value=\"(\d*)\"', str(response.content)).group(1)
    print(f'thetvdb_id: {thetvdb_id}')

    item['thetvdb_id'] = thetvdb_id
    item_filenames.append(os.path.join('thetvdb', f'{thetvdb_id}.json'))  # set the item filename


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
    with open(file='submission.json') as f:
        data = json.load(f)

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

    # check validity of provided YouTube url and update item dictionary
    check_youtube(data=submission)

    if args.add_game:
        item_type = 'game'

        check_igdb(data=submission)  # check validity of IGDB url and update item dictionary

        required_keys.append('igdb_id')

    elif args.add_movie:
        item_type = 'movie'

        # todo - process submission
        check_imdb(data=submission)
        check_themoviedb(data=submission)
        check_thetvdb(data=submission)

        required_keys.append('imdb_id')
        required_keys.append('themoviedb_id')
        required_keys.append('thetvdb_id')

    for key in required_keys:
        if key not in item:
            raise Exception(f'Final item is missing required key: {key}')

    print(item)
    print(item_filenames)

    for filename in item_filenames:
        destination_file = os.path.join(f'{item_type}s', filename)
        destination_dir = os.path.dirname(destination_file)

        print(destination_dir)

        os.makedirs(name=destination_dir, exist_ok=True)  # create directory if it doesn't exist

        with open(destination_file, "w") as f:
            f.write(json.dumps(item))
