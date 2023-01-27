# standard imports
import argparse
from datetime import datetime
import json
import os
from queue import Queue
import re
import threading
import time
from typing import Callable, Optional

# lib imports
from igdb.wrapper import IGDBWrapper
import requests
import youtube_dl

# load env
from dotenv import load_dotenv
load_dotenv()

# default paths
igdb_dir = os.path.join('database', 'games', 'igdb')
tmdb_dir = os.path.join('database', 'movies', 'themoviedb')

# setup queue
queue = Queue()

all_games_dict = []
all_movies_dict = []

# exclude these from daily update
exclude_files_for_daily_update = [
    'all.json',
    'contributors.json',
]


def igdb_authorization(client_id: str, client_secret: str) -> dict:
    """
    Get the igdb authorization.

    Parameters
    ----------
    client_id : str
        Twitch developer client id.
    client_secret : str
        Twitch developer client secret.

    Returns
    -------
    dict
        Dictionary containing access token and expiration.
    """
    auth_headers = dict(
        Accept='application/json',
        client_id=client_id,
        client_secret=client_secret,
        grant_type='client_credentials'
    )

    token_url = 'https://id.twitch.tv/oauth2/token'

    authorization = requests.post(url=token_url, data=auth_headers).json()
    return authorization


# setup igdb authorization and wrapper
auth = igdb_authorization(
    client_id=os.environ["TWITCH_CLIENT_ID"],
    client_secret=os.environ["TWITCH_CLIENT_SECRET"]
)
wrapper = IGDBWrapper(client_id=os.environ["TWITCH_CLIENT_ID"], auth_token=auth['access_token'])


def requests_loop(url: str, method: Callable = requests.get, max_tries: int = 10) -> requests.Response:
    count = 0
    while count <= max_tries:
        try:
            response = method(url=url)
            if response.status_code == requests.codes.ok:
                return response
        except requests.exceptions.RequestException:
            time.sleep(2**count)
            count += 1


def process_queue() -> None:
    """
    Add items to the queue.
    This is an endless loop to add items to the queue.
    Examples
    --------
    >>> threads = threading.Thread(target=process_queue, daemon=True)
    ...
    """
    while True:
        item = queue.get()
        queue_handler(item=item)  # process the item from the queue
        queue.task_done()  # tells the queue that we are done with this item


def queue_handler(item: tuple) -> None:
    if item[0] == 'game':
        data = process_igdb_id(game_id=item[1])
        all_games_dict.append(dict(
            id=data['id'],
            name=data['name']
        ))
    elif item[0] == 'movie':
        data = process_tmdb_id(tmdb_id=item[1])
        all_movies_dict.append(dict(
            id=data['id'],
            title=data['title']
        ))


# create multiple threads for processing themes faster
# number of threads
for t in range(10):
    try:
        # for each thread, start it
        t = threading.Thread(target=process_queue)
        # when we set daemon to true, that thread will end when the main thread ends
        t.daemon = True
        # start the daemon thread
        t.start()
    except RuntimeError as e:
        print(f'RuntimeError encountered: {e}')
        break


def process_igdb_id(game_slug: Optional[str] = None,
                    game_id: Optional[int] = None,
                    youtube_url: Optional[str] = None) -> dict:
    if game_slug:
        where_type = 'slug'
        where = f'"{game_slug}"'
    elif game_id:
        where_type = 'id'
        where = game_id
    else:
        raise Exception('game_slug or game_id is required')

    print(f'Searching igdb for {where_type}: {where}')

    destination_filenames = []

    # empty dictionary to handle future cases
    og_data = dict()

    fields = [
        'cover.url',
        'name',
        'release_dates.y',
        'slug',
        'summary',
        'url'
    ]
    limit = 1
    offset = 0

    byte_array = wrapper.api_request(
        endpoint='games',
        query=f'fields {", ".join(fields)}; where {where_type} = ({where}); limit {limit}; offset {offset};'
    )

    json_result = json.loads(byte_array)  # this is a list of dictionaries

    try:
        game_id = json_result[0]['id']
    except (KeyError, IndexError) as e:
        raise Exception(f'Error getting game id: {e}')
    else:
        json_data = json_result[0]

    print(f'processing id {game_id}')

    igdb_file = os.path.join(igdb_dir, f"{game_id}.json")
    if os.path.isfile(igdb_file):
        with open(file=igdb_file, mode='r') as og_f:
            og_data = json.load(fp=og_f)  # get currently saved data

    try:
        json_data['id']
    except KeyError as e:
        raise Exception(f'Error processing game: {e}')
    else:
        try:
            args.issue_update
        except NameError:
            pass
        else:
            if args.issue_update:
                # create the issue comment and title files
                issue_comment = f"""
| Property | Value |
| --- | --- |
| title | {json_data['name']} |
| year | {json_data['release_dates'][0]['y']} |
| summary | {json_data['summary']} |
| id | {json_data['id']} |
| poster | ![poster](https:{json_data['cover']['url'].replace('/t_thumb/', '/t_cover_big/')}) |
"""
                with open("comment.md", "a") as comment_f:
                    comment_f.write(issue_comment)

                issue_title = f"[GAME]: {json_data['name']} ({json_data['release_dates'][0]['y']})"
                with open("title.md", "w") as title_f:
                    title_f.write(issue_title)

                # update dates
                now = int(datetime.utcnow().timestamp())
                try:
                    og_data['youtube_theme_added']
                except KeyError:
                    og_data['youtube_theme_added'] = now
                finally:
                    og_data['youtube_theme_edited'] = now

                # update user ids
                original_submission = False
                try:
                    og_data['youtube_theme_added_by']
                except KeyError:
                    original_submission = True
                    og_data['youtube_theme_added_by'] = os.environ['ISSUE_AUTHOR_USER_ID']
                finally:
                    og_data['youtube_theme_edited_by'] = os.environ['ISSUE_AUTHOR_USER_ID']

                # update contributor info
                update_contributor_info(original=original_submission, base_dir=igdb_dir)

        # update the existing dictionary with new values from json_data
        og_data.update(json_data)
        if youtube_url:
            og_data['youtube_theme_url'] = youtube_url

        destination_filenames.append(os.path.join('igdb', f'{og_data["id"]}.json'))  # set the item filename

        for filename in destination_filenames:
            destination_file = os.path.join('database', 'games', filename)
            destination_dir = os.path.dirname(destination_file)

            os.makedirs(name=destination_dir, exist_ok=True)  # create directory if it doesn't exist

            with open(destination_file, "w") as dest_f:
                json.dump(obj=og_data, indent=4, fp=dest_f, sort_keys=True)

    return og_data


def process_tmdb_id(tmdb_id: int, youtube_url: Optional[str] = None) -> dict:
    print(f'processing id {tmdb_id}')

    destination_filenames = []

    # empty dictionary to handle future cases
    og_data = dict()

    tmdb_file = os.path.join(tmdb_dir, f"{tmdb_id}.json")
    if os.path.isfile(tmdb_file):
        with open(file=tmdb_file, mode='r') as og_f:
            og_data = json.load(fp=og_f)  # get currently saved data

    # get the data from tmdb api
    url = f'https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={os.environ["TMDB_API_KEY_V3"]}'
    response = requests_loop(url=url, method=requests.get)

    if response.status_code != 200:
        raise Exception(f'tmdb api returned a non 200 status code of: {response.status_code}')

    json_data = response.json()
    try:
        json_data['id']
    except KeyError as e:
        raise Exception(f'Error processing movie: {e}')
    else:
        try:
            args.issue_update
        except NameError:
            pass
        else:
            if args.issue_update:
                # create the issue comment and title files
                issue_comment = f"""
| Property | Value |
| --- | --- |
| title | {json_data['title']} |
| year | {json_data['release_date'][0:4]} |
| summary | {json_data['overview']} |
| id | {json_data['id']} |
| poster | ![poster](https://image.tmdb.org/t/p/w185{json_data['poster_path']}) |
"""
                with open("comment.md", "a") as comment_f:
                    comment_f.write(issue_comment)

                issue_title = f"[MOVIE]: {json_data['title']} ({json_data['release_date'][0:4]})"
                with open("title.md", "w") as title_f:
                    title_f.write(issue_title)

                # update dates
                now = int(datetime.utcnow().timestamp())
                try:
                    og_data['youtube_theme_added']
                except KeyError:
                    og_data['youtube_theme_added'] = now
                finally:
                    og_data['youtube_theme_edited'] = now

                # update user ids
                original_submission = False
                try:
                    og_data['youtube_theme_added_by']
                except KeyError:
                    original_submission = True
                    og_data['youtube_theme_added_by'] = os.environ['ISSUE_AUTHOR_USER_ID']
                finally:
                    og_data['youtube_theme_edited_by'] = os.environ['ISSUE_AUTHOR_USER_ID']

                # update contributor info
                update_contributor_info(original=original_submission, base_dir=tmdb_dir)

        # update the existing dictionary with new values from json_data
        og_data.update(json_data)
        if youtube_url:
            og_data['youtube_theme_url'] = youtube_url

        destination_filenames.append(os.path.join('themoviedb', f'{og_data["id"]}.json'))  # set the item filename
        try:
            if og_data["imdb_id"]:
                # set the item filename
                destination_filenames.append(os.path.join('imdb', f'{og_data["imdb_id"]}.json'))
        except KeyError as e:
            print(f'Error getting imdb_id: {e}')

        for filename in destination_filenames:
            destination_file = os.path.join('database', 'movies', filename)
            destination_dir = os.path.dirname(destination_file)

            os.makedirs(name=destination_dir, exist_ok=True)  # create directory if it doesn't exist

            with open(destination_file, "w") as dest_f:
                json.dump(obj=og_data, indent=4, fp=dest_f, sort_keys=True)

    return og_data


def update_contributor_info(original: bool, base_dir: str):
    contributor_file_path = os.path.join(base_dir, 'contributors.json')
    with open(contributor_file_path, 'r') as contributor_f:
        contributor_data = json.load(contributor_f)
        try:
            contributor_data[os.environ['ISSUE_AUTHOR_USER_ID']]
        except KeyError:
            contributor_data[os.environ['ISSUE_AUTHOR_USER_ID']] = dict(
                items_added=1,
                items_edited=0
            )
        else:
            if original:
                contributor_data[os.environ['ISSUE_AUTHOR_USER_ID']]['items_added'] += 1
            else:
                contributor_data[os.environ['ISSUE_AUTHOR_USER_ID']]['items_edited'] += 1

    with open(contributor_file_path, 'w') as contributor_f:
        json.dump(obj=contributor_data, indent=4, fp=contributor_f, sort_keys=True)


def process_issue_update():
    # process submission file
    submission = process_submission()

    # check validity of provided YouTube url and update item dictionary
    youtube_url = check_youtube(data=submission)

    if args.game:
        check_igdb(data=submission, youtube_url=youtube_url)  # check validity of IGDB url and update item dictionary
    elif args.movie:
        check_themoviedb(data=submission, youtube_url=youtube_url)
    else:
        raise SystemExit('item_type not defined. Invalid label?')


def check_igdb(data: dict, youtube_url: str):
    print('Checking igdb')
    url = data['igdb_url'].strip()
    print(f'igdb_url: {url}')

    game_slug = re.search(r'https://www\.igdb.com/games/(.+)/*.*', url).group(1)
    print(f'game_slug: {game_slug}')

    process_igdb_id(game_slug=game_slug, youtube_url=youtube_url)


def check_themoviedb(data: dict, youtube_url: str):
    print('Checking themoviedb')
    url = data['themoviedb_url'].strip()
    print(f'themoviedb_url: {url}')

    themoviedb_id = re.search(r'https://www\.themoviedb.org/movie/(\d+)-*.*', url).group(1)
    print(f'themoviedb_id: {themoviedb_id}')

    process_tmdb_id(tmdb_id=themoviedb_id, youtube_url=youtube_url)


def check_youtube(data: dict):
    url = data['youtube_theme_url'].strip()

    # url provided, now process it using youtube_dl
    youtube_dl_params = dict(
        outmpl='%(id)s.%(ext)s',
        youtube_include_dash_manifest=False,
    )

    ydl = youtube_dl.YoutubeDL(params=youtube_dl_params)

    with ydl:
        try:
            result = ydl.extract_info(
                url=url,
                download=False  # We just want to extract the info
            )
        except youtube_dl.utils.DownloadError as e:
            print(f'Error processing youtube url: {e}')
            with open("comment.md", "w") as exceptions_f:
                exceptions_f.write(f'# :bangbang: **Exception Occurred** :bangbang:\n\n```txt\n{e}\n```\n\n')
        else:
            if 'entries' in result:
                # Can be a playlist or a list of videos
                video_data = result['entries'][0]
            else:
                # Just a video
                video_data = result

            webpage_url = video_data['webpage_url']

            return webpage_url


def process_submission():
    with open(file='submission.json') as file:
        data = json.load(file)

    return data


if __name__ == '__main__':
    # setup arguments using argparse
    parser = argparse.ArgumentParser(description="Add theme song to database.")
    parser.add_argument('--daily_update', action='store_true', help='Run in daily update mode.')
    parser.add_argument('--issue_update', action='store_true', help='Run in issue update mode.')
    parser.add_argument('--game', action='store_true', help='Add Game theme song.')
    parser.add_argument('--movie', action='store_true', help='Add Movie theme song.')

    args = parser.parse_args()

    if args.issue_update:
        if not args.game and not args.movie:
            raise Exception('"--game" or "--movie" arg must be passed.')
        elif args.game and args.movie:
            raise Exception('"--game" or "--movie" arg must be passed, not both.')

        process_issue_update()

    elif args.daily_update:
        all_movies = os.listdir(path=tmdb_dir)

        for file in all_movies:
            if file not in exclude_files_for_daily_update:
                item_id = file.rsplit('.', 1)[0]
                queue.put(('movie', item_id))

        all_games = os.listdir(path=igdb_dir)

        for file in all_games:
            if file not in exclude_files_for_daily_update:
                item_id = file.rsplit('.', 1)[0]
                queue.put(('game', item_id))

        queue.join()

        all_games_file = os.path.join('database', 'games', 'igdb', 'all.json')
        with open(file=all_games_file, mode='w') as all_games_f:
            json.dump(obj=all_games_dict, fp=all_games_f, sort_keys=True)

        all_movies_file = os.path.join('database', 'movies', 'themoviedb', 'all.json')
        with open(file=all_movies_file, mode='w') as all_movies_f:
            json.dump(obj=all_movies_dict, fp=all_movies_f, sort_keys=True)
