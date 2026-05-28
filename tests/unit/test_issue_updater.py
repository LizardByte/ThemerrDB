"""
test_issue_updater.py

This module contains unit tests for the issue_updater module. The issue_updater module is responsible for
verifying and updating requests to update the ThemerrDB database. The tests in this module ensure that the
issue_updater module is functioning correctly by validating URLs and checking that the correct IDs are returned.
"""
# standard imports
from datetime import datetime as RealDateTime
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


@pytest.fixture
def mock_igdb_api(monkeypatch):
    """Mock IGDB API responses for deterministic game and game-group tests."""
    game = {
        'id': 1638,
        'igdb_id': 1638,
        'name': 'GoldenEye 007',
        'release_dates': [{'y': 1997}],
        'cover': {'url': '//images.igdb.com/igdb/image/upload/t_thumb/co1.jpg'},
        'summary': 'A game summary.',
        'url': 'https://www.igdb.com/games/goldeneye-007',
    }
    collection = {
        'id': 326,
        'name': 'James Bond',
        'slug': 'james-bond',
        'url': 'https://www.igdb.com/collections/james-bond',
    }
    franchise = {
        'id': 37,
        'name': 'James Bond',
        'slug': 'james-bond',
        'url': 'https://www.igdb.com/franchises/james-bond',
    }
    response_by_endpoint = {
        'games': game,
        'collections': collection,
        'franchises': franchise,
    }

    def api_request(endpoint, query):
        if endpoint == 'games' and not ('goldeneye-007' in query or '(1638)' in query):
            return json.dumps([])
        if endpoint in {'collections', 'franchises'} and not (
                'james-bond' in query or '(326)' in query or '(37)' in query):
            return json.dumps([])

        return json.dumps([response_by_endpoint[endpoint]])

    monkeypatch.setattr(updater, 'wrapper', type('Wrapper', (), {'api_request': staticmethod(api_request)})())
    monkeypatch.setattr(updater.igdb_limiter, 'wait', lambda: None)


@pytest.fixture
def mock_tmdb_api(monkeypatch):
    """Mock TMDB API responses for deterministic movie, collection, and TV tests."""
    response_by_path = {
        'movie/710': {
            'id': 710,
            'imdb_id': 'tt0113189',
            'title': 'GoldenEye',
            'release_date': '1995-11-16',
            'poster_path': '/goldeneye.jpg',
            'overview': 'A movie summary.',
        },
        'movie/10378': {
            'id': 10378,
            'imdb_id': 'tt1254207',
            'title': 'Big Buck Bunny',
            'release_date': '2008-04-10',
            'poster_path': '/big-buck-bunny.jpg',
            'overview': 'A movie summary.',
        },
        'collection/645': {
            'id': 645,
            'name': 'James Bond Collection',
            'poster_path': '/james-bond.jpg',
            'overview': 'A collection summary.',
        },
        'tv/1930': {
            'id': 1930,
            'name': 'The Beverly Hillbillies',
            'first_air_date': '1962-09-26',
            'poster_path': '/beverly-hillbillies.jpg',
            'overview': 'A TV summary.',
        },
    }

    def requests_loop(url, **kwargs):
        for path, payload in response_by_path.items():
            if f'/3/{path}?' in url:
                response = MagicMock()
                response.status_code = 200
                response.json.return_value = payload
                return response

        raise AssertionError(f'Unexpected TMDB URL: {url}')

    monkeypatch.setenv('TMDB_API_KEY_V3', 'test-key')
    monkeypatch.setattr(updater, 'requests_loop', requests_loop)


@pytest.fixture
def mock_youtube_api(monkeypatch):
    """Mock YouTube validation for deterministic URL canonicalization tests."""
    monkeypatch.setenv('YOUTUBE_API_KEY', 'youtube-key')
    mock_youtube_build(
        monkeypatch=monkeypatch,
        response={
            'items': [
                {
                    'contentDetails': {
                        'duration': 'PT30S',
                    },
                    'status': {
                        'privacyStatus': 'public',
                    },
                },
            ],
        },
    )


def test_igdb_authorization(monkeypatch):
    """Tests if access token is returned from igdb_authorization method."""
    class Response:
        def json(self):
            return {'access_token': 'token'}

    def post(url, data):
        assert url == 'https://id.twitch.tv/oauth2/token'
        assert data['client_id'] == 'client-id'
        assert data['client_secret'] == 'client-secret'
        return Response()

    monkeypatch.setattr(updater.requests, 'post', post)

    auth = updater.igdb_authorization(
        client_id='client-id',
        client_secret='client-secret'
    )

    assert auth['access_token'] == 'token'


def test_get_igdb_wrapper_initializes_lazily(monkeypatch):
    """Test that the IGDB wrapper is created only when requested."""
    created = []

    class Wrapper:
        def __init__(self, client_id, auth_token):
            created.append((client_id, auth_token))

    monkeypatch.setenv('TWITCH_CLIENT_ID', 'client-id')
    monkeypatch.setenv('TWITCH_CLIENT_SECRET', 'client-secret')
    monkeypatch.setattr(updater, 'wrapper', None)
    monkeypatch.setattr(updater, 'igdb_authorization', lambda client_id, client_secret: {'access_token': 'token'})
    monkeypatch.setattr(updater, 'IGDBWrapper', Wrapper)

    wrapper = updater.get_igdb_wrapper()

    assert isinstance(wrapper, Wrapper)
    assert updater.get_igdb_wrapper() is wrapper
    assert created == [('client-id', 'token')]


@pytest.mark.parametrize('item_id, expected', [
    ('goldeneye-007', ('slug', '"goldeneye-007"')),
    ('1638', ('id', '1638')),
    (1638, ('id', 1638)),
])
def test_get_igdb_query_filter_identifies_slug_and_id(item_id, expected):
    """Test IGDB query filter selection for slugs and numeric ids."""
    assert updater._get_igdb_query_filter(item_id=item_id) == expected


def test_load_item_data_dispatches_by_provider(monkeypatch):
    """Test provider helper dispatch for game and non-game item types."""
    calls = []

    def load_igdb_item_data(item_type, item_id):
        calls.append(('igdb', item_type, item_id))
        return 'igdb-path', item_id, {'id': item_id}

    def load_tmdb_item_data(item_type, item_id):
        calls.append(('tmdb', item_type, item_id))
        return 'tmdb-path', item_id, {'id': item_id}

    monkeypatch.setattr(updater, '_load_igdb_item_data', load_igdb_item_data)
    monkeypatch.setattr(updater, '_load_tmdb_item_data', load_tmdb_item_data)

    assert updater._load_item_data(item_type='game_collection', item_id='james-bond') == (
        'igdb-path',
        'james-bond',
        {'id': 'james-bond'},
    )
    assert updater._load_item_data(item_type='movie', item_id='710') == (
        'tmdb-path',
        '710',
        {'id': '710'},
    )
    assert calls == [
        ('igdb', 'game_collection', 'james-bond'),
        ('tmdb', 'movie', '710'),
    ]


def test_load_tmdb_item_data_builds_request_and_returns_payload(tmp_path, monkeypatch):
    """Test the TMDB helper builds the expected API request."""
    payload = {'id': 710, 'title': 'GoldenEye'}
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = payload
    requests = []

    def requests_loop(**kwargs):
        requests.append(kwargs)
        return response

    database_path = tmp_path / 'database' / 'movies' / 'themoviedb'
    monkeypatch.setenv('TMDB_API_KEY_V3', 'tmdb-key')
    monkeypatch.setitem(updater.databases['movie'], 'path', str(database_path))
    monkeypatch.setattr(updater, 'requests_loop', requests_loop)

    result = updater._load_tmdb_item_data(item_type='movie', item_id='710')

    assert result == (str(database_path), '710', payload)
    assert requests[0]['url'] == 'https://api.themoviedb.org/3/movie/710?api_key=tmdb-key'
    assert requests[0]['no_retry_statuses'] == [404]


def test_load_existing_item_data_writes_duplicate_marker(tmp_path, monkeypatch):
    """Test existing item loading also writes duplicate metadata for issue updates."""
    item_file = tmp_path / '1638.json'
    item_file.write_text(json.dumps({'id': 1638}), encoding='utf-8')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(updater, 'args', type('Args', (), {'issue_update': True})())

    assert updater._load_existing_item_data(item_file=str(tmp_path / 'missing.json')) == {}
    assert updater._load_existing_item_data(item_file=str(item_file)) == {'id': 1638}
    assert (tmp_path / 'duplicate.md').read_text(encoding='utf-8') == 'This item already exists in the database.'


@pytest.mark.parametrize('item_type, json_data, expected', [
    (
        'game',
        {
            'name': 'GoldenEye 007',
            'release_dates': [{'y': 1997}],
            'cover': {'url': '//images.igdb.com/igdb/image/upload/t_thumb/co1.jpg'},
            'summary': 'Line 1\nLine 2',
        },
        {
            'issue_title': '[GAME]: GoldenEye 007 (1997)',
            'poster': '![poster](https://images.igdb.com/igdb/image/upload/t_cover_big/co1.jpg)',
            'summary': 'Line 1<br>Line 2',
            'title': 'GoldenEye 007',
            'year': 1997,
        },
    ),
    (
        'movie',
        {
            'title': 'GoldenEye',
            'release_date': '1995-11-16',
            'poster_path': '/goldeneye.jpg',
            'overview': 'A movie summary.',
        },
        {
            'issue_title': '[MOVIE]: GoldenEye (1995)',
            'poster': '![poster](https://image.tmdb.org/t/p/w185/goldeneye.jpg)',
            'summary': 'A movie summary.',
            'title': 'GoldenEye',
            'year': '1995',
        },
    ),
    (
        'movie_collection',
        {
            'name': 'James Bond Collection',
            'poster_path': '/james-bond.jpg',
            'overview': 'A collection summary.',
        },
        {
            'issue_title': '[MOVIE COLLECTION]: James Bond Collection',
            'poster': '![poster](https://image.tmdb.org/t/p/w185/james-bond.jpg)',
            'summary': 'A collection summary.',
            'title': 'James Bond Collection',
            'year': '',
        },
    ),
    (
        'tv_show',
        {
            'name': 'The Beverly Hillbillies',
            'first_air_date': '1962-09-26',
            'poster_path': '/beverly-hillbillies.jpg',
            'overview': 'A TV summary.',
        },
        {
            'issue_title': '[TV SHOW]: The Beverly Hillbillies (1962)',
            'poster': '![poster](https://image.tmdb.org/t/p/w185/beverly-hillbillies.jpg)',
            'summary': 'A TV summary.',
            'title': 'The Beverly Hillbillies',
            'year': '1962',
        },
    ),
])
def test_build_issue_metadata_for_item_types(item_type, json_data, expected):
    """Test issue metadata helper output for representative item types."""
    assert updater._build_issue_metadata(item_type=item_type, json_data=json_data) == expected


def test_write_issue_metadata_files(tmp_path, monkeypatch):
    """Test issue metadata file writing without running full item processing."""
    monkeypatch.chdir(tmp_path)

    updater._write_issue_metadata_files(
        item_type='game_collection',
        json_data={'id': 326, 'name': 'James Bond'},
    )

    assert (tmp_path / 'title.md').read_text(encoding='utf-8') == '[GAME COLLECTION]: James Bond'
    comment = (tmp_path / 'comment.md').read_text(encoding='utf-8')
    assert '| title | James Bond |' in comment
    assert '| id | 326 |' in comment


def test_update_issue_audit_data_sets_original_submission_fields(tmp_path, monkeypatch, youtube_url):
    """Test audit metadata updates for a new issue submission."""
    class FixedDateTime(RealDateTime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 1, 1, tzinfo=tz)

    item_dir = tmp_path / 'database' / 'games' / 'igdb'
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('ISSUE_AUTHOR_USER_ID', 'user-1')
    monkeypatch.setitem(updater.databases['game'], 'path', str(item_dir))
    monkeypatch.setattr(updater, 'datetime', FixedDateTime)
    og_data = {'youtube_theme_url': youtube_url}

    updater._update_issue_audit_data(og_data=og_data, item_type='game', youtube_url=youtube_url)

    assert og_data['youtube_theme_added'] == og_data['youtube_theme_edited']
    assert og_data['youtube_theme_added_by'] == 'user-1'
    assert og_data['youtube_theme_edited_by'] == 'user-1'
    contributor_data = json.loads((tmp_path / 'database' / 'games' / 'contributors.json').read_text())
    assert contributor_data['user-1'] == {'items_added': 1, 'items_edited': 0}
    assert (tmp_path / 'auto_close.md').read_text() == 'The YouTube url provided is the same as the current one.'


def test_write_item_files_writes_primary_and_imdb_copy(tmp_path, monkeypatch):
    """Test item file writing for movie primary and IMDb lookup files."""
    database_path = tmp_path / 'database' / 'movies' / 'themoviedb'
    imdb_dir = tmp_path / 'database' / 'movies' / 'imdb'
    item_data = {'id': 710, 'imdb_id': 'tt0113189', 'title': 'GoldenEye'}
    monkeypatch.setattr(updater, 'imdb_path', str(imdb_dir))

    updater._write_item_files(database_path=str(database_path), item_type='movie', og_data=item_data)

    assert json.loads((database_path / '710.json').read_text()) == item_data
    assert json.loads((imdb_dir / 'tt0113189.json').read_text()) == item_data


def test_load_issue_submission_values_uses_supplied_values(monkeypatch):
    """Test fully supplied issue-update values bypass submission processing."""
    monkeypatch.setattr(
        updater,
        'process_submission',
        lambda: pytest.fail('submission file should not be read'),
    )

    assert updater._load_issue_submission_values(database_url='database-url', youtube_url='youtube-url') == (
        'database-url',
        'youtube-url',
    )


def test_load_issue_submission_values_reads_missing_values(monkeypatch):
    """Test missing issue-update values are loaded and canonicalized from submission data."""
    submission = {
        'database_url': '  https://www.igdb.com/games/goldeneye-007  ',
        'youtube_theme_url': 'raw-youtube-url',
    }
    monkeypatch.setattr(updater, 'process_submission', lambda: submission)
    monkeypatch.setattr(updater, 'check_youtube', lambda data: f"canonical-{data['youtube_theme_url']}")

    assert updater._load_issue_submission_values(database_url=None, youtube_url=None) == (
        'https://www.igdb.com/games/goldeneye-007',
        'canonical-raw-youtube-url',
    )


def test_match_database_url_returns_item_and_prior_misses():
    """Test database URL matching returns the first supported item type."""
    item_type, item_id, exceptions = updater._match_database_url(
        database_url='https://www.themoviedb.org/movie/710-goldeneye',
    )

    assert (item_type, item_id) == ('movie', '710')
    assert [exception[0] for exception in exceptions] == ['game', 'game_collection', 'game_franchise']


def test_match_database_url_returns_all_misses_for_unsupported_url():
    """Test unsupported database URLs expose every failed pattern."""
    item_type, item_id, exceptions = updater._match_database_url(database_url='https://example.com/nope')

    assert item_type is None
    assert item_id is None
    assert [exception[0] for exception in exceptions] == list(updater.DATABASE_URL_PATTERNS)


@pytest.mark.parametrize('db_url, db_type', [
    # url, expected item type
    ('https://www.igdb.com/games/goldeneye-007', 'game'),
    ('https://www.igdb.com/collections/james-bond', 'game_collection'),
    ('https://www.igdb.com/franchises/james-bond', 'game_franchise'),
    ('https://www.themoviedb.org/movie/10378-big-buck-bunny', 'movie'),
    ('https://www.themoviedb.org/collection/645-james-bond-collection', 'movie_collection'),
    ('https://www.themoviedb.org/tv/1930-the-beverly-hillbillies', 'tv_show'),
])
def test_process_issue_update(
        db_url,
        db_type,
        issue_update_args,
        mock_igdb_api,
        mock_tmdb_api,
        youtube_url,
        tmp_path,
        monkeypatch,
):
    """Test the provided submission urls and verify they are the correct item type."""
    monkeypatch.chdir(tmp_path)

    data = updater.process_issue_update(database_url=db_url, youtube_url=youtube_url)

    assert data == db_type


def test_process_issue_update_invalid_youtube(issue_update_args, submission_invalid_youtube):
    """Tests if the provided YouTube url is invalid and raises an exception."""
    data = updater.process_issue_update()
    assert not data
    assert data is False


@pytest.mark.parametrize('url_suffix', [
    '',
    '&list=PLE0hg-LdSfycrpTtMImPSqFLle4yYNzWD',
])
def test_check_youtube(youtube_url, url_suffix, mock_youtube_api):
    """Tests if the provided YouTube url is valid and returns a valid url."""
    yt_url = updater.check_youtube(data={'youtube_theme_url': f'{youtube_url}{url_suffix}'})

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
def test_process_item_id(item_type, item_id, mock_igdb_api, mock_tmdb_api, youtube_url, tmp_path, monkeypatch):
    """Tests if the provided game_slug is valid and the created dictionary contains the required keys."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(updater, 'args', type('Args', (), {'issue_update': False})())

    data = updater.process_item_id(
        item_type=item_type,
        item_id=item_id,
        youtube_url=youtube_url
    )

    assert data['id']
    assert data['youtube_theme_url']


def test_main_daily_update(daily_update_args, mock_igdb_api, mock_tmdb_api, monkeypatch):
    class FutureDateTime(RealDateTime):
        @classmethod
        def now(cls, tz=None):
            return cls(2999, 1, 1, tzinfo=tz)

    monkeypatch.setattr(updater, 'datetime', FutureDateTime)

    updater.main()


def test_main_issue_update_movie(issue_update_args, submission_movie, mock_tmdb_api, mock_youtube_api):
    updater.main()
    file_path = os.path.join(os.getcwd(), 'database', 'movies', 'themoviedb', '10378.json')

    assert os.path.isfile(file_path)

    # ensure youtube_theme_url is correct
    with open(file_path, 'r') as f:
        data = json.load(f)

    assert data['youtube_theme_url'] == submission_movie['youtube_theme_url']


def test_main_issue_update_movie_collection(
        issue_update_args, submission_movie_collection, mock_tmdb_api, mock_youtube_api):
    updater.main()
    file_path = os.path.join(os.getcwd(), 'database', 'movie_collections', 'themoviedb', '645.json')

    assert os.path.isfile(file_path)

    # ensure youtube_theme_url is correct
    with open(file_path, 'r') as f:
        data = json.load(f)

    assert data['youtube_theme_url'] == submission_movie_collection['youtube_theme_url']


def test_main_issue_update_tv_show(issue_update_args, submission_tv_show, mock_tmdb_api, mock_youtube_api):
    updater.main()
    file_path = os.path.join(os.getcwd(), 'database', 'tv_shows', 'themoviedb', '1930.json')

    assert os.path.isfile(file_path)

    # ensure youtube_theme_url is correct
    with open(file_path, 'r') as f:
        data = json.load(f)

    assert data['youtube_theme_url'] == submission_tv_show['youtube_theme_url']


def test_main_issue_update_game(issue_update_args, submission_game, mock_igdb_api, mock_youtube_api):
    updater.main()
    file_path = os.path.join(os.getcwd(), 'database', 'games', 'igdb', '1638.json')

    assert os.path.isfile(file_path)

    # ensure youtube_theme_url is correct
    with open(file_path, 'r') as f:
        data = json.load(f)

    assert data['youtube_theme_url'] == submission_game['youtube_theme_url']


def test_main_issue_update_game_collection(
        issue_update_args, submission_game_collection, mock_igdb_api, mock_youtube_api):
    updater.main()
    file_path = os.path.join(os.getcwd(), 'database', 'game_collections', 'igdb', '326.json')

    assert os.path.isfile(file_path)

    # ensure youtube_theme_url is correct
    with open(file_path, 'r') as f:
        data = json.load(f)

    assert data['youtube_theme_url'] == submission_game_collection['youtube_theme_url']


def test_main_issue_update_game_franchise(
        issue_update_args, submission_game_franchise, mock_igdb_api, mock_youtube_api):
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


@pytest.mark.parametrize('item_type, item_id, response, expected', [
    (
        'movie',
        '710',
        {
            'id': 710,
            'imdb_id': 'tt0113189',
            'title': 'GoldenEye',
        },
        {
            'id': 710,
            'imdb_id': 'tt0113189',
            'title': 'GoldenEye',
        },
    ),
    (
        'game',
        '1638',
        {
            'id': 1638,
            'name': 'GoldenEye 007',
        },
        {
            'id': 1638,
            'title': 'GoldenEye 007',
        },
    ),
])
def test_queue_handler_appends_processed_item(item_type, item_id, response, expected, monkeypatch):
    """Test that queue_handler appends processed movie and non-movie records."""
    monkeypatch.setitem(updater.databases[item_type], 'all_items', [])

    with patch('src.updater.process_item_id', return_value=response) as process_item_id:
        updater.queue_handler(item=(item_type, item_id))

    process_item_id.assert_called_once_with(item_type=item_type, item_id=item_id)
    assert updater.databases[item_type]['all_items'] == [expected]


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


def test_requests_loop_returns_allowed_status():
    """Test that requests_loop returns immediately for allowed statuses."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    def mock_method(url, headers):
        return mock_response

    result = updater.requests_loop(
        url='https://api.themoviedb.org/3/movie/1',
        method=mock_method,
    )

    assert result == mock_response


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


def test_requests_loop_logs_request_exception(monkeypatch, capsys):
    """Test that requests_loop handles request exceptions and returns the last response."""
    monkeypatch.setattr(updater.tmdb_limiter, 'wait', lambda: None)
    monkeypatch.setattr(updater.time, 'sleep', lambda seconds: None)

    def mock_method(url, headers):
        raise updater.requests.exceptions.RequestException('network unavailable')

    result = updater.requests_loop(
        url='https://api.themoviedb.org/3/movie/1',
        method=mock_method,
        max_tries=1,
    )

    captured = capsys.readouterr()
    assert result is None
    assert 'network unavailable' in captured.out


def test_start_queue_workers_stops_on_runtime_error(monkeypatch, capsys):
    """Test that worker startup stops cleanly when a thread cannot be started."""
    class FailingThread:
        daemon = False

        def __init__(self, target):
            assert target == updater.process_queue

        def start(self):
            raise RuntimeError('thread failed')

    monkeypatch.setattr(updater.threading, 'Thread', FailingThread)

    updater.start_queue_workers(worker_count=2)

    captured = capsys.readouterr()
    assert 'RuntimeError encountered: thread failed' in captured.out


def test_process_item_id_igdb_missing_result_raises(tmp_path, monkeypatch):
    """Test that IGDB lookup failures are reported through exception_writer."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setitem(updater.databases['game'], 'path', str(tmp_path / 'database' / 'games' / 'igdb'))
    monkeypatch.setattr(updater.igdb_limiter, 'wait', lambda: None)
    monkeypatch.setattr(updater, 'wrapper', type('Wrapper', (), {
        'api_request': lambda self, endpoint, query: json.dumps([]),
    })())
    monkeypatch.setattr(updater, 'args', type('Args', (), {'issue_update': False})())

    with pytest.raises(Exception, match='Error getting game id'):
        updater.process_item_id(item_type='game', item_id='missing')


def test_process_item_id_tmdb_non_200_raises(tmp_path, monkeypatch):
    """Test that unexpected TMDB statuses fail through exception_writer."""
    errors = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('TMDB_API_KEY_V3', 'test-key')
    monkeypatch.setitem(updater.databases['movie'], 'path', str(tmp_path / 'database' / 'movies' / 'themoviedb'))
    monkeypatch.setattr(updater, 'args', type('Args', (), {'issue_update': False})())

    mock_response = MagicMock()
    mock_response.status_code = 500
    monkeypatch.setattr(updater, 'requests_loop', lambda **kwargs: mock_response)

    def exception_writer(error, name, end_program=False):
        errors.append((str(error), name, end_program))

    monkeypatch.setattr(updater, 'exception_writer', exception_writer)

    data = updater.process_item_id(item_type='movie', item_id='1')

    assert data == {}
    assert errors == [('tmdb api returned a non 200 status code of: 500', 'tmdb', True)]


def test_process_item_id_missing_id_raises(tmp_path, monkeypatch):
    """Test that missing API ids are rejected before writing database files."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('TMDB_API_KEY_V3', 'test-key')
    monkeypatch.setitem(updater.databases['movie'], 'path', str(tmp_path / 'database' / 'movies' / 'themoviedb'))
    monkeypatch.setattr(updater, 'args', type('Args', (), {'issue_update': False})())

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'title': 'Missing ID'}
    monkeypatch.setattr(updater, 'requests_loop', lambda **kwargs: mock_response)

    with pytest.raises(Exception, match='Error processing game'):
        updater.process_item_id(item_type='movie', item_id='1')


def test_process_item_id_without_args_writes_movie_and_logs_missing_imdb(tmp_path, monkeypatch, capsys):
    """Test the non-issue-update path when args has not been initialized."""
    movie_dir = tmp_path / 'database' / 'movies' / 'themoviedb'
    imdb_dir = tmp_path / 'database' / 'movies' / 'imdb'
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('TMDB_API_KEY_V3', 'test-key')
    monkeypatch.setitem(updater.databases['movie'], 'path', str(movie_dir))
    monkeypatch.setattr(updater, 'imdb_path', str(imdb_dir))
    monkeypatch.delattr(updater, 'args', raising=False)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'id': 1,
        'title': 'No IMDb',
        'release_date': '2026-01-01',
        'poster_path': '/poster.jpg',
        'overview': 'Overview',
    }
    monkeypatch.setattr(updater, 'requests_loop', lambda **kwargs: mock_response)

    data = updater.process_item_id(item_type='movie', item_id='1')

    captured = capsys.readouterr()
    assert data['id'] == 1
    assert (movie_dir / '1.json').is_file()
    assert "Error getting imdb_id" in captured.out


@pytest.mark.parametrize('item_type,item_id,expected_endpoint,response,expected_title', [
    (
        'game',
        'goldeneye-007',
        'games',
        {
            'id': 1638,
            'igdb_id': 1638,
            'name': 'GoldenEye 007',
            'release_dates': [{'y': 1997}],
            'cover': {'url': '//images.igdb.com/igdb/image/upload/t_thumb/co1.jpg'},
            'summary': 'Line 1\nLine 2',
            'url': 'https://www.igdb.com/games/goldeneye-007',
        },
        '[GAME]: GoldenEye 007 (1997)',
    ),
    (
        'game_collection',
        'james-bond',
        'collections',
        {
            'id': 326,
            'name': 'James Bond',
            'slug': 'james-bond',
            'url': 'https://www.igdb.com/collections/james-bond',
        },
        '[GAME COLLECTION]: James Bond',
    ),
    (
        'game_franchise',
        'james-bond',
        'franchises',
        {
            'id': 37,
            'name': 'James Bond',
            'slug': 'james-bond',
            'url': 'https://www.igdb.com/franchises/james-bond',
        },
        '[GAME FRANCHISE]: James Bond',
    ),
])
def test_process_item_id_igdb_issue_update_writes_metadata(
        item_type,
        item_id,
        expected_endpoint,
        response,
        expected_title,
        tmp_path,
        monkeypatch,
        youtube_url,
):
    """Test issue-update metadata for IGDB item types."""
    item_dir = tmp_path / 'database' / f'{item_type}s' / 'igdb'
    if item_type == 'game':
        item_dir = tmp_path / 'database' / 'games' / 'igdb'
    elif item_type == 'game_collection':
        item_dir = tmp_path / 'database' / 'game_collections' / 'igdb'
    elif item_type == 'game_franchise':
        item_dir = tmp_path / 'database' / 'game_franchises' / 'igdb'

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('ISSUE_AUTHOR_USER_ID', '1234')
    monkeypatch.setitem(updater.databases[item_type], 'path', str(item_dir))
    monkeypatch.setattr(updater.igdb_limiter, 'wait', lambda: None)
    monkeypatch.setattr(updater, 'args', type('Args', (), {'issue_update': True})())

    def api_request(endpoint, query):
        assert endpoint == expected_endpoint
        assert item_id in query
        return json.dumps([response])

    monkeypatch.setattr(updater, 'wrapper', type('Wrapper', (), {'api_request': staticmethod(api_request)})())

    data = updater.process_item_id(item_type=item_type, item_id=item_id, youtube_url=youtube_url)

    assert data['youtube_theme_added_by'] == '1234'
    assert data['youtube_theme_edited_by'] == '1234'
    assert data['youtube_theme_url'] == youtube_url
    assert (tmp_path / 'title.md').read_text() == expected_title
    assert (item_dir / f'{response["id"]}.json').is_file()


def test_process_item_id_issue_update_marks_existing_duplicate_and_auto_close(tmp_path, monkeypatch, youtube_url):
    """Test existing issue updates write duplicate and auto-close metadata in an isolated database."""
    item_dir = tmp_path / 'database' / 'games' / 'igdb'
    item_dir.mkdir(parents=True)
    item_file = item_dir / '1638.json'
    item_file.write_text(json.dumps({
        'id': 1638,
        'youtube_theme_added_by': 'existing-user',
        'youtube_theme_url': youtube_url,
    }))
    contributor_file = tmp_path / 'database' / 'games' / 'contributors.json'
    contributor_file.write_text(json.dumps({
        '1234': {
            'items_added': 0,
            'items_edited': 0,
        },
    }))

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('ISSUE_AUTHOR_USER_ID', '1234')
    monkeypatch.setitem(updater.databases['game'], 'path', str(item_dir))
    monkeypatch.setattr(updater.igdb_limiter, 'wait', lambda: None)
    monkeypatch.setattr(updater, 'args', type('Args', (), {'issue_update': True})())

    def api_request(endpoint, query):
        assert endpoint == 'games'
        assert '1638' in query
        return json.dumps([{
            'id': 1638,
            'name': 'GoldenEye 007',
            'release_dates': [{'y': 1997}],
            'cover': {'url': '//images.igdb.com/igdb/image/upload/t_thumb/co1.jpg'},
            'summary': 'Line 1',
            'url': 'https://www.igdb.com/games/goldeneye-007',
        }])

    monkeypatch.setattr(updater, 'wrapper', type('Wrapper', (), {'api_request': staticmethod(api_request)})())

    data = updater.process_item_id(item_type='game', item_id=1638, youtube_url=youtube_url)

    contributor_data = json.loads(contributor_file.read_text())
    assert data['youtube_theme_added_by'] == 'existing-user'
    assert data['youtube_theme_edited_by'] == '1234'
    assert contributor_data['1234'] == {
        'items_added': 0,
        'items_edited': 1,
    }
    assert (tmp_path / 'duplicate.md').read_text() == 'This item already exists in the database.'
    assert (tmp_path / 'auto_close.md').read_text() == 'The YouTube url provided is the same as the current one.'


def test_clean_old_data_handles_missing_and_present_igdb_id():
    """Test game cleanup with and without legacy igdb_id values."""
    data_with_legacy_id = {'id': 1, 'igdb_id': 1}
    updater.clean_old_data(data=data_with_legacy_id, item_type='game')
    assert data_with_legacy_id == {'id': 1}

    data_without_legacy_id = {'id': 1}
    updater.clean_old_data(data=data_without_legacy_id, item_type='game')
    assert data_without_legacy_id == {'id': 1}


def test_update_contributor_info_increments_existing_original(tmp_path, monkeypatch):
    """Test original submissions increment items_added for existing contributors."""
    contributor_dir = tmp_path / 'database' / 'games'
    contributor_dir.mkdir(parents=True)
    contributor_file = contributor_dir / 'contributors.json'
    contributor_file.write_text(json.dumps({
        '1234': {
            'items_added': 1,
            'items_edited': 2,
        },
    }))
    monkeypatch.setenv('ISSUE_AUTHOR_USER_ID', '1234')

    updater.update_contributor_info(original=True, base_dir=str(contributor_dir / 'igdb'))

    contributor_data = json.loads(contributor_file.read_text())
    assert contributor_data['1234'] == {
        'items_added': 2,
        'items_edited': 2,
    }


def test_update_contributor_info_increments_existing_edit(tmp_path, monkeypatch):
    """Test edits increment items_edited for existing contributors."""
    contributor_dir = tmp_path / 'database' / 'games'
    contributor_dir.mkdir(parents=True)
    contributor_file = contributor_dir / 'contributors.json'
    contributor_file.write_text(json.dumps({
        '1234': {
            'items_added': 1,
            'items_edited': 2,
        },
    }))
    monkeypatch.setenv('ISSUE_AUTHOR_USER_ID', '1234')

    updater.update_contributor_info(original=False, base_dir=str(contributor_dir / 'igdb'))

    contributor_data = json.loads(contributor_file.read_text())
    assert contributor_data['1234'] == {
        'items_added': 1,
        'items_edited': 3,
    }


def test_process_issue_update_reports_unsupported_database_url(tmp_path, monkeypatch, youtube_url):
    """Test that unsupported database URLs report every regex miss."""
    monkeypatch.chdir(tmp_path)

    result = updater.process_issue_update(
        database_url='https://example.com/nope',
        youtube_url=youtube_url,
    )

    assert result is False
    exceptions = (tmp_path / 'exceptions.md').read_text()
    assert exceptions.count('Exception Occurred') == 6


def mock_youtube_build(monkeypatch, response=None, exception=None):
    """Patch googleapiclient discovery build with a fake YouTube service."""
    class Request:
        def execute(self):
            if exception:
                raise exception
            return response

    class Videos:
        def list(self, part, id):
            assert part == 'snippet,contentDetails,status'
            assert len(id) == 11
            return Request()

    class YouTube:
        def videos(self):
            return Videos()

    def build(service_name, version, **kwargs):
        assert service_name == 'youtube'
        assert version == 'v3'
        assert kwargs == {'developerKey': 'youtube-key'}
        return YouTube()

    monkeypatch.setattr(updater, 'build', build)


def test_check_youtube_returns_none_without_api_key(tmp_path, monkeypatch, youtube_url):
    """Test that check_youtube rejects requests when the API key is missing."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv('YOUTUBE_API_KEY', raising=False)

    result = updater.check_youtube(data={'youtube_theme_url': youtube_url})

    assert result is None
    assert 'YOUTUBE_API_KEY environment variable is not set' in (tmp_path / 'exceptions.md').read_text()


@pytest.mark.parametrize('response,error_text', [
    ({'items': []}, 'Video not found or unavailable'),
    ({'items': [{}, {}]}, "multiple videos found"),
])
def test_check_youtube_rejects_bad_api_results(tmp_path, monkeypatch, youtube_url, response, error_text):
    """Test YouTube API responses that cannot identify exactly one video."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('YOUTUBE_API_KEY', 'youtube-key')
    mock_youtube_build(monkeypatch=monkeypatch, response=response)

    result = updater.check_youtube(data={'youtube_theme_url': youtube_url})

    assert result is None
    assert error_text in (tmp_path / 'exceptions.md').read_text()


def test_check_youtube_writes_validation_errors_and_returns_canonical_url(tmp_path, monkeypatch, youtube_url):
    """Test that validation errors are recorded while returning the canonical URL."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('YOUTUBE_API_KEY', 'youtube-key')
    mock_youtube_build(
        monkeypatch=monkeypatch,
        response={
            'items': [
                {
                    'contentDetails': {
                        'duration': 'PT10S',
                        'contentRating': {
                            'ytRating': 'ytAgeRestricted',
                        },
                    },
                    'status': {
                        'privacyStatus': 'private',
                    },
                },
            ],
        },
    )

    result = updater.check_youtube(data={'youtube_theme_url': youtube_url})

    exceptions = (tmp_path / 'exceptions.md').read_text()
    assert result == youtube_url
    assert 'Video is too short' in exceptions
    assert 'Video is age-restricted' in exceptions
    assert 'Video must be public' in exceptions


def test_check_youtube_handles_http_error(tmp_path, monkeypatch, youtube_url):
    """Test that YouTube HttpError exceptions are reported."""
    class FakeHttpError(Exception):
        reason = 'quota exceeded'

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('YOUTUBE_API_KEY', 'youtube-key')
    monkeypatch.setattr(updater, 'HttpError', FakeHttpError)
    mock_youtube_build(monkeypatch=monkeypatch, exception=FakeHttpError())

    result = updater.check_youtube(data={'youtube_theme_url': youtube_url})

    assert result is None
    assert 'YouTube API error: quota exceeded' in (tmp_path / 'exceptions.md').read_text()


def test_check_youtube_handles_unexpected_error(tmp_path, monkeypatch, youtube_url):
    """Test that unexpected YouTube API errors are reported."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('YOUTUBE_API_KEY', 'youtube-key')
    mock_youtube_build(monkeypatch=monkeypatch, exception=RuntimeError('service failed'))

    result = updater.check_youtube(data={'youtube_theme_url': youtube_url})

    assert result is None
    assert 'service failed' in (tmp_path / 'exceptions.md').read_text()
