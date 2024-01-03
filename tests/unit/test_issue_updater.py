"""
test_issue_updater.py

This module contains unit tests for the issue_updater module. The issue_updater module is responsible for
verifying and updating requests to update the ThemerrDB database. The tests in this module ensure that the
issue_updater module is functioning correctly by validating URLs and checking that the correct IDs are returned.
"""
# standard imports
import json
import os
from urllib.parse import urlparse

# lib imports
import pytest

# local imports
from src import updater


# reusables
@pytest.fixture(scope='module')
def youtube_url():
    return 'https://www.youtube.com/watch?v=qGPBFvDz_HM'


def test_igdb_authorization(igdb_auth):
    """Tests if access token is returned from igdb_authorization method."""
    auth = updater.igdb_authorization(
        client_id=os.environ["TWITCH_CLIENT_ID"],
        client_secret=os.environ["TWITCH_CLIENT_SECRET"]
    )

    assert auth['access_token']


@pytest.mark.parametrize('db_url, db_type', [
    # url, expected item type
    ('https://www.igdb.com/games/goldeneye-007', 'game'),
    ('https://www.igdb.com/collections/james-bond', 'game_collection'),
    ('https://www.igdb.com/franchises/james-bond', 'game_franchise'),
    ('https://www.themoviedb.org/movie/10378-big-buck-bunny', 'movie'),
    ('https://www.themoviedb.org/collection/645-james-bond-collection', 'movie_collection'),
])
def test_process_issue_update(db_url, db_type, issue_update_args, igdb_auth, tmdb_auth, youtube_url):
    """Test the provides submission urls and verify they are the correct item type."""
    data = updater.process_issue_update(database_url=db_url, youtube_url=youtube_url)

    assert data == db_type


def test_check_youtube(youtube_url):
    """Tests if the provided YouTube url is valid and returns a valid url."""
    yt_url = updater.check_youtube(data=dict(youtube_theme_url=youtube_url))

    host = urlparse(yt_url).hostname
    scheme = urlparse(yt_url).scheme

    assert host == 'www.youtube.com'
    assert scheme == 'https'


@pytest.mark.parametrize('item_type, item_id', [
    ('game', 'goldeneye-007'),
    ('game', 1638),
    ('game_collection', 'james-bond'),
    ('game_collection', 326),
    ('game_franchise', 'james-bond'),
    ('game_franchise', 37),
    ('movie', 710),
    ('movie_collection', 645),
])
def test_process_item_id(item_type, item_id, igdb_auth, tmdb_auth, youtube_url):
    """Tests if the provided game_slug is valid and the created dictionary contains the required keys."""
    data = updater.process_item_id(
        item_type=item_type,
        item_id=item_id,
        youtube_url=youtube_url
    )

    assert data['id']
    assert data['youtube_theme_url']


def test_main_daily_update(daily_update_args, igdb_auth, tmdb_auth):
    updater.main()


def test_main_issue_update_movie(issue_update_args, submission_movie, tmdb_auth):
    updater.main()
    file_path = os.path.join(os.getcwd(), 'database', 'movies', 'themoviedb', '10378.json')

    assert os.path.isfile(file_path)

    # ensure youtube_theme_url is correct
    with open(file_path, 'r') as f:
        data = json.load(f)

    assert data['youtube_theme_url'] == submission_movie['youtube_theme_url']


def test_main_issue_update_game(issue_update_args, submission_game, igdb_auth):
    updater.main()
    file_path = os.path.join(os.getcwd(), 'database', 'games', 'igdb', '1638.json')

    assert os.path.isfile(file_path)

    # ensure youtube_theme_url is correct
    with open(file_path, 'r') as f:
        data = json.load(f)

    assert data['youtube_theme_url'] == submission_game['youtube_theme_url']


def test_main_issue_update_movie_collection(issue_update_args, submission_movie_collection, tmdb_auth):
    updater.main()
    file_path = os.path.join(os.getcwd(), 'database', 'movie_collections', 'themoviedb', '645.json')

    assert os.path.isfile(file_path)

    # ensure youtube_theme_url is correct
    with open(file_path, 'r') as f:
        data = json.load(f)

    assert data['youtube_theme_url'] == submission_movie_collection['youtube_theme_url']


def test_main_issue_update_game_collection(issue_update_args, submission_game_collection, igdb_auth):
    updater.main()
    file_path = os.path.join(os.getcwd(), 'database', 'game_collections', 'igdb', '326.json')

    assert os.path.isfile(file_path)

    # ensure youtube_theme_url is correct
    with open(file_path, 'r') as f:
        data = json.load(f)

    assert data['youtube_theme_url'] == submission_game_collection['youtube_theme_url']


def test_main_issue_update_game_franchise(issue_update_args, submission_game_franchise, igdb_auth):
    updater.main()
    file_path = os.path.join(os.getcwd(), 'database', 'game_franchises', 'igdb', '37.json')

    assert os.path.isfile(file_path)

    # ensure youtube_theme_url is correct
    with open(file_path, 'r') as f:
        data = json.load(f)

    assert data['youtube_theme_url'] == submission_game_franchise['youtube_theme_url']


def test_process_submission(submission_movie):
    """Tests if the submission file is processed correctly."""
    data = updater.process_submission()

    assert data['database_url'] == submission_movie['database_url']
    assert data['youtube_theme_url'] == submission_movie['youtube_theme_url']


def test_process_submission_invalid_key(submission_invalid_key, exceptions_file):
    """Tests if the submission file is processed correctly."""
    with pytest.raises(Exception):
        updater.process_submission()

    assert os.path.isfile(exceptions_file)

    with open(exceptions_file, 'r') as f:
        contents = f.read()

    assert contents


def test_process_submission_empty_value(submission_empty_value, exceptions_file):
    """Tests if the submission file is processed correctly."""
    with pytest.raises(Exception):
        updater.process_submission()

    assert os.path.isfile(exceptions_file)

    with open(exceptions_file, 'r') as f:
        contents = f.read()

    assert contents
