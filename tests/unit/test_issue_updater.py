"""
test_issue_updater.py

This module contains unit tests for the issue_updater module. The issue_updater module is responsible for
verifying and updating requests to update the ThemerrDB database. The tests in this module ensure that the
issue_updater module is functioning correctly by validating URLs and checking that the correct IDs are returned.
"""
# standard imports
import json
import os
from queue import Queue
import threading
from unittest.mock import MagicMock, patch
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
    ('https://www.themoviedb.org/tv/1930-the-beverly-hillbillies', 'tv_show'),
])
def test_process_issue_update(db_url, db_type, issue_update_args, igdb_auth, tmdb_auth, youtube_auth, youtube_url):
    """Test the provided submission urls and verify they are the correct item type."""
    data = updater.process_issue_update(database_url=db_url, youtube_url=youtube_url)

    assert data == db_type


def test_process_issue_update_invalid_youtube(issue_update_args, tmdb_auth, youtube_auth, submission_invalid_youtube):
    """Tests if the provided YouTube url is invalid and raises an exception."""
    data = updater.process_issue_update()
    assert not data
    assert data is False


@pytest.mark.parametrize('url_suffix', [
    '',
    '&list=PLE0hg-LdSfycrpTtMImPSqFLle4yYNzWD',
])
def test_check_youtube(youtube_url, url_suffix, youtube_auth):
    """Tests if the provided YouTube url is valid and returns a valid url."""
    yt_url = updater.check_youtube(data=dict(youtube_theme_url=f'{youtube_url}{url_suffix}'))

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
    ('tv_show', 1930),
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


def test_main_issue_update_movie_collection(issue_update_args, submission_movie_collection, tmdb_auth):
    updater.main()
    file_path = os.path.join(os.getcwd(), 'database', 'movie_collections', 'themoviedb', '645.json')

    assert os.path.isfile(file_path)

    # ensure youtube_theme_url is correct
    with open(file_path, 'r') as f:
        data = json.load(f)

    assert data['youtube_theme_url'] == submission_movie_collection['youtube_theme_url']


def test_main_issue_update_tv_show(issue_update_args, submission_tv_show, tmdb_auth):
    updater.main()
    file_path = os.path.join(os.getcwd(), 'database', 'tv_shows', 'themoviedb', '1930.json')

    assert os.path.isfile(file_path)

    # ensure youtube_theme_url is correct
    with open(file_path, 'r') as f:
        data = json.load(f)

    assert data['youtube_theme_url'] == submission_tv_show['youtube_theme_url']


def test_main_issue_update_game(issue_update_args, submission_game, igdb_auth):
    updater.main()
    file_path = os.path.join(os.getcwd(), 'database', 'games', 'igdb', '1638.json')

    assert os.path.isfile(file_path)

    # ensure youtube_theme_url is correct
    with open(file_path, 'r') as f:
        data = json.load(f)

    assert data['youtube_theme_url'] == submission_game['youtube_theme_url']


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


@pytest.mark.parametrize('github_actions_env, expected_prefix', [
    ('true', '::warning::'),
    (None, 'WARNING: '),
])
def test_print_github_warning(github_actions_env, expected_prefix, monkeypatch, capsys):
    """Test that print_github_warning emits the correct format depending on environment."""
    if github_actions_env:
        monkeypatch.setenv('GITHUB_ACTIONS', github_actions_env)
    else:
        monkeypatch.delenv('GITHUB_ACTIONS', raising=False)

    updater.print_github_warning('test warning message')

    captured = capsys.readouterr()
    assert captured.out.strip() == f'{expected_prefix}test warning message'


@pytest.mark.parametrize('github_actions_env, expected_prefix', [
    ('true', '::error::'),
    (None, 'ERROR: '),
])
def test_print_github_error(github_actions_env, expected_prefix, monkeypatch, capsys):
    """Test that print_github_error emits the correct format depending on environment."""
    if github_actions_env:
        monkeypatch.setenv('GITHUB_ACTIONS', github_actions_env)
    else:
        monkeypatch.delenv('GITHUB_ACTIONS', raising=False)

    updater.print_github_error('test error message')

    captured = capsys.readouterr()
    assert captured.out.strip() == f'{expected_prefix}test error message'


@pytest.mark.parametrize('item_type', ['movie', 'movie_collection', 'tv_show'])
def test_process_item_id_tmdb_not_found_with_stale_file(item_type, tmp_path, monkeypatch):
    """Test that a removed TMDB item returns an empty dict and removes the stale database file."""
    item_id = '42903'

    tmp_db_path = tmp_path / 'database' / item_type / 'themoviedb'
    tmp_db_path.mkdir(parents=True)
    stale_file = tmp_db_path / f'{item_id}.json'
    stale_file.write_text(json.dumps({'id': int(item_id), 'title': 'Removed Item'}))

    monkeypatch.setitem(updater.databases[item_type], 'path', str(tmp_db_path))
    monkeypatch.setenv('TMDB_API_KEY_V3', 'test_key')

    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch('src.updater.requests_loop', return_value=mock_response):
        data = updater.process_item_id(item_type=item_type, item_id=item_id)

    assert data == {}
    assert not stale_file.exists()


@pytest.mark.parametrize('item_type', ['movie', 'movie_collection', 'tv_show'])
def test_process_item_id_tmdb_not_found_no_stale_file(item_type, tmp_path, monkeypatch):
    """Test that a removed TMDB item returns an empty dict even when no stale file exists."""
    item_id = '42903'

    tmp_db_path = tmp_path / 'database' / item_type / 'themoviedb'
    tmp_db_path.mkdir(parents=True)

    monkeypatch.setitem(updater.databases[item_type], 'path', str(tmp_db_path))
    monkeypatch.setenv('TMDB_API_KEY_V3', 'test_key')

    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch('src.updater.requests_loop', return_value=mock_response):
        data = updater.process_item_id(item_type=item_type, item_id=item_id)

    assert data == {}


def test_queue_handler_skips_empty_data():
    """Test that queue_handler does not crash or append anything when process_item_id returns empty dict."""
    original_items = list(updater.databases['movie']['all_items'])

    with patch('src.updater.process_item_id', return_value={}):
        updater.queue_handler(item=('movie', '42903'))

    assert updater.databases['movie']['all_items'] == original_items


def test_process_queue_task_done_called_on_exception():
    """Test that queue.task_done() is always called even when queue_handler raises an exception."""
    test_queue = Queue()
    test_queue.put(('movie', '99999'))

    task_done_called = threading.Event()
    original_task_done = test_queue.task_done

    def patched_task_done():
        original_task_done()
        task_done_called.set()

    test_queue.task_done = patched_task_done

    original_queue = updater.queue
    updater.queue = test_queue

    try:
        with patch('src.updater.queue_handler', side_effect=RuntimeError('simulated failure')):
            thread = threading.Thread(target=updater.process_queue, daemon=True)
            thread.start()
            assert task_done_called.wait(timeout=5), 'queue.task_done() was not called within timeout'
            test_queue.join()
    finally:
        updater.queue = original_queue


def test_requests_loop_no_retry_on_permanent_status():
    """Test that requests_loop does not retry when the status code is in no_retry_statuses."""
    mock_response = MagicMock()
    mock_response.status_code = 404

    call_count = 0

    def mock_method(url, headers):
        nonlocal call_count
        call_count += 1
        return mock_response

    result = updater.requests_loop(
        url='https://api.themoviedb.org/3/movie/42903',
        method=mock_method,
        max_tries=3,
        no_retry_statuses=[404],
    )

    assert result.status_code == 404
    assert call_count == 1


def test_requests_loop_retries_on_non_permanent_error():
    """Test that requests_loop retries the expected number of times for non-permanent errors."""
    mock_response = MagicMock()
    mock_response.status_code = 500

    call_count = 0

    def mock_method(url, headers):
        nonlocal call_count
        call_count += 1
        return mock_response

    result = updater.requests_loop(
        url='https://api.themoviedb.org/3/movie/42903',
        method=mock_method,
        max_tries=3,
        no_retry_statuses=[404],
    )

    assert result.status_code == 500
    assert call_count == 3
