# standard imports
import json
import os

# lib imports
import pytest

# local imports
from src import updater

# load env
from dotenv import load_dotenv
load_dotenv()

os.environ['CI_TEST'] = 'True'
os.environ['ISSUE_AUTHOR_USER_ID'] = '1234'

LEADERBOARD_UPDATE_FALSE_MESSAGE = "leaderboard_update should be False"
GOLDENEYE_IGDB_URL = 'https://www.igdb.com/games/goldeneye-007'
RICKROLL_YOUTUBE_URL = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'


@pytest.fixture(scope='session')
def igdb_auth():
    """Skip tests if no auth id or secret."""
    auth_id = os.getenv('TWITCH_CLIENT_ID')
    auth_secret = os.getenv('TWITCH_CLIENT_SECRET')

    if not auth_id or not auth_secret:
        # skip if no auth id or secret
        pytest.skip('"TWITCH_CLIENT_ID" or "TWITCH_CLIENT_SECRET" not set in environment variables.')


@pytest.fixture(scope='session')
def tmdb_auth():
    """Skip tests if no api key."""
    auth_id = os.getenv('TMDB_API_KEY_V3')

    if not auth_id:
        # skip if no api key
        pytest.skip('"TMDB_API_KEY_V3" not set in environment variables.')


@pytest.fixture(scope='session')
def youtube_auth():
    """Skip tests if no api key."""
    api_key = os.getenv('YOUTUBE_API_KEY')

    if not api_key:
        # skip if no api key
        pytest.skip('"YOUTUBE_API_KEY" not set in environment variables.')


@pytest.fixture(scope='function')
def daily_update_args():
    parser = updater.parse_args(['--daily_update'])
    assert parser.daily_update, "daily_update should be True"
    assert updater.args.daily_update, "daily_update should be True"

    assert not parser.issue_update, "issue_update should be False"
    assert not updater.args.issue_update, "issue_update should be False"

    assert not parser.leaderboard_update, LEADERBOARD_UPDATE_FALSE_MESSAGE
    assert not updater.args.leaderboard_update, LEADERBOARD_UPDATE_FALSE_MESSAGE

    return parser


@pytest.fixture(scope='function')
def issue_update_args():
    parser = updater.parse_args(['--issue_update'])
    assert not parser.daily_update, "daily_update should be False"
    assert not updater.args.daily_update, "daily_update should be False"

    assert parser.issue_update, "issue_update should be True"
    assert updater.args.issue_update, "issue_update should be True"

    assert not parser.leaderboard_update, LEADERBOARD_UPDATE_FALSE_MESSAGE
    assert not updater.args.leaderboard_update, LEADERBOARD_UPDATE_FALSE_MESSAGE

    return parser


@pytest.fixture(scope='function')
def submission_workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def create_submission_file(data: dict):
    """Create a submission file for testing."""
    submission_file = os.path.join(os.getcwd(), 'submission.json')

    with open(submission_file, 'w') as f:
        f.write(json.dumps(data))

    return submission_file


@pytest.fixture(scope='function')
def submission_movie(submission_workspace):
    submission_data = {
        'database_url': 'https://www.themoviedb.org/movie/10378-big-buck-bunny',
        'youtube_theme_url': RICKROLL_YOUTUBE_URL,
    }

    submission_file = create_submission_file(data=submission_data)

    yield submission_data

    os.remove(submission_file)


@pytest.fixture(scope='function')
def submission_game(submission_workspace):
    submission_data = {
        'database_url': GOLDENEYE_IGDB_URL,
        'youtube_theme_url': RICKROLL_YOUTUBE_URL,
    }

    submission_file = create_submission_file(data=submission_data)

    yield submission_data

    os.remove(submission_file)


@pytest.fixture(scope='function')
def submission_movie_collection(submission_workspace):
    submission_data = {
        'database_url': 'https://www.themoviedb.org/collection/645-james-bond-collection',
        'youtube_theme_url': RICKROLL_YOUTUBE_URL,
    }

    submission_file = create_submission_file(data=submission_data)

    yield submission_data

    os.remove(submission_file)


@pytest.fixture(scope='function')
def submission_tv_show(submission_workspace):
    submission_data = {
        'database_url': 'https://www.themoviedb.org/tv/1930-the-beverly-hillbillies',
        'youtube_theme_url': RICKROLL_YOUTUBE_URL,
    }

    submission_file = create_submission_file(data=submission_data)

    yield submission_data

    os.remove(submission_file)


@pytest.fixture(scope='function')
def submission_game_collection(submission_workspace):
    submission_data = {
        'database_url': 'https://www.igdb.com/collections/james-bond',
        'youtube_theme_url': RICKROLL_YOUTUBE_URL,
    }

    submission_file = create_submission_file(data=submission_data)

    yield submission_data

    os.remove(submission_file)


@pytest.fixture(scope='function')
def submission_game_franchise(submission_workspace):
    submission_data = {
        'database_url': 'https://www.igdb.com/franchises/james-bond',
        'youtube_theme_url': RICKROLL_YOUTUBE_URL,
    }

    submission_file = create_submission_file(data=submission_data)

    yield submission_data

    os.remove(submission_file)


@pytest.fixture(scope='function')
def submission_invalid_key(submission_workspace):
    submission_data = {
        'database_url': GOLDENEYE_IGDB_URL,
        'invalid_key': RICKROLL_YOUTUBE_URL,
    }

    submission_file = create_submission_file(data=submission_data)

    yield submission_data

    os.remove(submission_file)


@pytest.fixture(scope='function')
def submission_empty_value(submission_workspace):
    submission_data = {
        'database_url': GOLDENEYE_IGDB_URL,
        'youtube_theme_url': '',
    }

    submission_file = create_submission_file(data=submission_data)

    yield submission_data

    os.remove(submission_file)


@pytest.fixture(scope='function')
def submission_invalid_youtube(submission_workspace):
    submission_data = {
        'database_url': GOLDENEYE_IGDB_URL,
        'youtube_theme_url': 'https://www.youtube.com/watch?v=invalid',
    }

    submission_file = create_submission_file(data=submission_data)

    yield submission_data

    os.remove(submission_file)


@pytest.fixture(scope='function')
def exceptions_file(submission_workspace):
    exceptions_file = os.path.join(os.getcwd(), 'exceptions.md')

    yield exceptions_file

    os.remove(exceptions_file)
