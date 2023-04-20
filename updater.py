# standard imports
import argparse
from datetime import datetime
import json
from operator import itemgetter
import os
from queue import Queue
import re
import subprocess
import plotly
import threading
import time
from typing import Callable, Optional

# lib imports
from igdb.wrapper import IGDBWrapper
import requests
import yt_dlp as youtube_dl

# load env
from dotenv import load_dotenv
load_dotenv()

# databases
databases = dict(
    igdb=dict(
        all_items=[],
        path=os.path.join('database', 'games', 'igdb'),
        title='Games',
        type='game',
    ),
    tmdb=dict(
        all_items=[],
        path=os.path.join('database', 'movies', 'themoviedb'),
        title='Movies',
        type='movie',
    )
)
imdb_path = os.path.join('database', 'movies', 'imdb')

# setup queue
queue = Queue()


def exception_writer(error: Exception, name: str, end_program: bool = False) -> None:
    print(f'Error processing {name}: {error}')

    files = ['comment.md', 'exceptions.md']
    for file in files:
        with open(file, "a") as f:
            f.write(f'# :bangbang: **Exception Occurred** :bangbang:\n\n```txt\n{error}\n```\n\n')

    if end_program:
        raise error


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


def requests_loop(url: str,
                  headers: Optional[dict] = None,
                  method: Callable = requests.get,
                  max_tries: int = 8,
                  allow_statuses: list = [requests.codes.ok]) -> requests.Response:
    count = 1
    while count <= max_tries:
        print(f'Processing {url} ... (attempt {count + 1} of {max_tries})')
        try:
            response = method(url=url, headers=headers)
        except requests.exceptions.RequestException as e:
            print(f'Error processing {url} - {e}')
            time.sleep(2**count)
            count += 1
        except Exception as e:
            print(f'Error processing {url} - {e}')
            time.sleep(2**count)
            count += 1
        else:
            if response.status_code in allow_statuses:
                return response
            else:
                print(f'Error processing {url} - {response.status_code}')
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
    data = process_item_id(item_type=item[0], item_id=item[1])
    if item[0] == 'game':
        databases['igdb']['all_items'].append(dict(
            id=data['id'],
            title=data['name']  # igdb refers to this as name, but let's use title for consistency
        ))
    elif item[0] == 'movie':
        databases['tmdb']['all_items'].append(dict(
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
    except RuntimeError as r_e:
        print(f'RuntimeError encountered: {r_e}')
        break


def process_item_id(item_type: str,
                    item_id: Optional[int] = None,
                    game_slug: Optional[str] = None,
                    youtube_url: Optional[str] = None) -> dict:
    destination_filenames = []

    # empty dictionary to handle future cases
    og_data = dict()
    json_data = dict()

    database_path = None
    if item_type == 'game':
        database_path = databases['igdb']['path']

        if game_slug:
            where_type = 'slug'
            where = f'"{game_slug}"'
        elif item_id:
            where_type = 'id'
            where = item_id
        else:
            raise Exception('game_slug or game_id is required')

        print(f'Searching igdb for {where_type}: {where}')

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
            item_id = json_result[0]['id']
        except (KeyError, IndexError) as e:
            raise Exception(f'Error getting game id: {e}')
        else:
            json_data = json_result[0]
    elif item_type == 'movie':
        database_path = databases['tmdb']['path']

        # get the data from tmdb api
        url = f'https://api.themoviedb.org/3/movie/{item_id}?api_key={os.environ["TMDB_API_KEY_V3"]}'
        response = requests_loop(url=url, method=requests.get)

        if response.status_code != 200:
            raise Exception(f'tmdb api returned a non 200 status code of: {response.status_code}')

        json_data = response.json()

    item_file = os.path.join(database_path, f"{item_id}.json")
    if os.path.isfile(item_file):
        with open(file=item_file, mode='r') as og_f:
            og_data = json.load(fp=og_f)  # get currently saved data

    print(f'processing {item_type} id {item_id}')

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
                poster = ''
                issue_title = '[UNKNOWN]'
                summary = ''
                if item_type == 'game':
                    issue_title = f"[GAME]: {json_data['name']} ({json_data['release_dates'][0]['y']})"
                    poster = f"https:{json_data['cover']['url'].replace('/t_thumb/', '/t_cover_big/')}"
                    summary = json_data['summary'].replace('\n', '<br>')
                elif item_type == 'movie':
                    issue_title = f"[MOVIE]: {json_data['title']} ({json_data['release_date'][0:4]})"
                    poster = f"https://image.tmdb.org/t/p/w185{json_data['poster_path']}"
                    summary = json_data['overview'].replace('\n', '<br>')
                issue_comment = f"""
| Property | Value |
| --- | --- |
| title | {json_data['name'] if item_type == 'game' else json_data['title']} |
| year | {json_data['release_dates'][0]['y'] if item_type == 'game' else json_data['release_date'][0:4]} |
| summary | {summary} |
| id | {json_data['id']} |
| poster | ![poster]({poster}) |
"""
                with open("comment.md", "a") as comment_f:
                    comment_f.write(issue_comment)

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
                update_contributor_info(original=original_submission, base_dir=database_path)

        # update the existing dictionary with new values from json_data
        og_data.update(json_data)
        if youtube_url:
            og_data['youtube_theme_url'] = youtube_url

        # clean old data
        clean_old_data(data=og_data, item_type=item_type)

        destination_filenames.append(os.path.join(database_path, f'{og_data["id"]}.json'))  # set the item filename

        if item_type == 'movie':
            try:
                if og_data["imdb_id"]:
                    # set the item filename
                    destination_filenames.append(os.path.join(imdb_path, f'{og_data["imdb_id"]}.json'))
            except KeyError as e:
                print(f'Error getting imdb_id: {e}')

        for filename in destination_filenames:
            destination_dir = os.path.dirname(filename)

            os.makedirs(name=destination_dir, exist_ok=True)  # create directory if it doesn't exist

            with open(filename, "w") as dest_f:
                json.dump(obj=og_data, indent=4, fp=dest_f, sort_keys=True)

    return og_data


def clean_old_data(data: dict, item_type: str) -> None:
    # remove old data
    if item_type == 'game':
        try:
            del data['igdb_id']
        except KeyError:
            pass


def update_contributor_info(original: bool, base_dir: str) -> None:
    contributor_file_path = os.path.join(os.path.dirname(base_dir), 'contributors.json')
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


def process_issue_update() -> None:
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


def check_igdb(data: dict, youtube_url: str) -> None:
    print('Checking igdb')
    url = data['igdb_url'].strip()
    print(f'igdb_url: {url}')

    try:
        game_slug = re.search(r'https://www\.igdb.com/games/(.+)/*.*', url).group(1)
    except AttributeError as e:
        exception_writer(error=e, name='igdb')
    else:
        print(f'game_slug: {game_slug}')
        process_item_id(item_type='game', game_slug=game_slug, youtube_url=youtube_url)


def check_themoviedb(data: dict, youtube_url: str) -> None:
    print('Checking themoviedb')
    url = data['themoviedb_url'].strip()
    print(f'themoviedb_url: {url}')

    try:
        themoviedb_id = re.search(r'https://www\.themoviedb.org/movie/(\d+)-*.*', url).group(1)
    except AttributeError as e:
        exception_writer(error=e, name='themoviedb')
    else:
        print(f'themoviedb_id: {themoviedb_id}')
        process_item_id(item_type='movie', item_id=themoviedb_id, youtube_url=youtube_url)


def check_youtube(data: dict) -> str:
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
            exception_writer(error=e, name='youtube')
        else:
            if 'entries' in result:
                # Can be a playlist or a list of videos
                video_data = result['entries'][0]
            else:
                # Just a video
                video_data = result

            webpage_url = video_data['webpage_url']

            return webpage_url


def process_submission() -> dict:
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
        # migration tasks go here

        for db in databases:
            all_db_items = os.listdir(path=databases[db]['path'])
            for next_item_file in all_db_items:
                next_item_id = next_item_file.rsplit('.', 1)[0]
                queue.put((databases[db]['type'], next_item_id))

        # finish queue before writing `all` files
        queue.join()

        for db in databases:
            items_per_page = 10
            all_items = sorted(databases[db]['all_items'], key=itemgetter('title'), reverse=False)
            chunks = [all_items[x:x + items_per_page] for x in range(0, len(all_items), items_per_page)]
            for chunk in chunks:
                chunk_file = os.path.join(os.path.dirname(databases[db]['path']),
                                          f'all_page_{chunks.index(chunk) + 1}.json')
                with open(file=chunk_file, mode='w') as chunk_f:
                    json.dump(obj=chunk, fp=chunk_f)
            pages = dict(pages=len(chunks))
            pages_file = os.path.join(os.path.dirname(databases[db]['path']), 'pages.json')
            with open(file=pages_file, mode='w') as pages_f:
                json.dump(obj=pages, fp=pages_f)

            # build database size plot
            # x = date
            # y = items
            timestamps = []  # timestamps
            x_values = []
            y_values = []
            for item_ in all_items:
                with open(file=os.path.join(databases[db]['path'], f'{item_["id"]}.json')) as item_f:
                    item_data = json.load(item_f)
                timestamps.append(item_data['youtube_theme_added'])

            # timestamps list from min to max
            timestamps.sort()

            # convert timestamps to human-readable date
            timestamps_human = [datetime.fromtimestamp(x).strftime('%Y-%m-%d') for x in timestamps]

            total_count = 0
            for i in timestamps_human:
                if i not in x_values:
                    new_total = timestamps_human.count(i) + total_count
                    x_values.append(i)
                    y_values.append(new_total)
                    total_count = new_total

            # get the current date in human-readable format
            current_date = datetime.utcnow().strftime('%Y-%m-%d')
            if timestamps_human[-1] != current_date:
                x_values.append(current_date)  # add the current date
                y_values.append(y_values[-1])  # add the last value again to indicate no increase

            fig = dict(
                data=[dict(
                    x=x_values,
                    y=y_values,
                )],
                layout=dict(  # https://plotly.com/javascript/reference/layout/
                    autosize=True,  # makes chart responsive, works better than the responsive config option
                    font=dict(
                        color='#777',
                        family='Open Sans',
                    ),
                    hoverlabel=dict(
                        bgcolor='#252525',
                    ),
                    hovermode='x unified',  # show all Y values on hover
                    legend=dict(
                        entrywidth=0,
                        entrywidthmode='pixels',
                        orientation='h',
                    ),
                    margin=dict(
                        b=40,  # bottom
                        l=60,  # left
                        r=20,  # right
                        t=40,  # top
                    ),
                    paper_bgcolor='rgba(0,0,0,0)',  # transparent
                    plot_bgcolor='rgba(0,0,0,0)',  # transparent
                    showlegend=False,
                    title=databases[db]['title'],
                    uirevision=True,
                    xaxis=dict(
                        autorange=True,
                        gridcolor='#404040',
                        fixedrange=True,  # disable zoom of axis
                        layer='below traces',
                        showspikes=False,
                        zeroline=False,
                    ),
                    yaxis=dict(
                        fixedrange=True,  # disable zoom of axis
                        gridcolor='#404040',
                        layer='below traces',
                        title=dict(
                            standoff=10,  # separation between title and axis labels
                            text='Themes',
                        ),
                        zeroline=False,
                    ),
                )
            )

            # orca is used to write plotly charts to image files
            if os.name == 'nt':  # command is different on windows
                cmd = 'orca.cmd'
            else:
                cmd = 'orca'
            node_bin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'node_modules', '.bin')

            # write fig to json file, orca fails with large json entered on command line
            json_file = os.path.join(os.path.dirname(databases[db]['path']),
                                     f'{databases[db]["title"].lower()}_plot.json')
            with open(file=json_file, mode='w') as plot_f:
                json.dump(obj=fig, fp=plot_f, cls=plotly.utils.PlotlyJSONEncoder)

            subprocess.run(
                args=[
                    os.path.join(node_bin_dir, cmd),
                    'graph', json_file,  # it's possible to pass in multiple json files here, but this is just one
                    '--output-dir', os.path.dirname(databases[db]['path']),
                    '--output', f'{databases[db]["title"].lower()}_plot',
                    '--format', 'svg'
                ]
            )
