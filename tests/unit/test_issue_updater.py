"""
test_issue_updater.py

This module contains unit tests for the issue_updater module. The issue_updater module is responsible for
verifying and updating requests to update the ThemerrDB database. The tests in this module ensure that the
issue_updater module is functioning correctly by validating URLs and checking that the correct IDs are returned.
"""
# standard imports
import os

# local imports
import updater


# reusables
sample_youtube_url = 'https://www.youtube.com/watch?v=qGPBFvDz_HM'


def test_igdb_authorization():
    """Tests if access token is returned from igdb_authorization method."""
    auth = updater.igdb_authorization(
        client_id=os.environ["TWITCH_CLIENT_ID"],
        client_secret=os.environ["TWITCH_CLIENT_SECRET"]
    )

    assert auth['access_token']


def test_process_issue_update():
    """Test the provides submission urls and verify they are the correct item type."""
    database_urls = [
        # url, expected item type
        ('https://www.igdb.com/games/goldeneye-007', 'game'),
        ('https://www.igdb.com/collections/james-bond', 'game_collection'),
        ('https://www.igdb.com/franchises/james-bond', 'game_franchise'),
        ('https://www.themoviedb.org/movie/10378-big-buck-bunny', 'movie'),
        ('https://www.themoviedb.org/collection/645-james-bond-collection', 'movie_collection'),
    ]

    for item in database_urls:
        data = updater.process_issue_update(database_url=item[0], youtube_url=sample_youtube_url)

        assert data == item[1]


def test_check_youtube():
    """Tests if the provided YouTube url is valid and returns a valid url."""
    youtube_url = updater.check_youtube(data=dict(youtube_theme_url='https://www.youtube.com/watch?v=qGPBFvDz_HM'))

    assert youtube_url.startswith('https://www.youtube')


def test_process_item_id_game_by_slug():
    """Tests if the provided game_slug is valid and the created dictionary contains the required keys."""
    data = updater.process_item_id(
        item_type='game',
        item_id='goldeneye-007',
        youtube_url=sample_youtube_url
    )

    assert data['id']
    assert data['youtube_theme_url']


def test_process_item_id_game_by_id():
    """Tests if the provided game_id is valid and the created dictionary contains the required keys."""
    data = updater.process_item_id(
        item_type='game',
        item_id=1638,
        youtube_url=sample_youtube_url
    )

    assert data['id']
    assert data['youtube_theme_url']


def test_process_item_id_game_collection_by_slug():
    """Tests if the provided game_slug is valid and the created dictionary contains the required keys."""
    data = updater.process_item_id(
        item_type='game_collection',
        item_id='james-bond',
        youtube_url=sample_youtube_url
    )

    assert data['id']
    assert data['youtube_theme_url']


def test_process_item_id_game_collection_by_id():
    """Tests if the provided game_id is valid and the created dictionary contains the required keys."""
    data = updater.process_item_id(
        item_type='game_collection',
        item_id=326,
        youtube_url=sample_youtube_url
    )

    assert data['id']
    assert data['youtube_theme_url']


def test_process_item_id_game_franchise_by_slug():
    """Tests if the provided game_slug is valid and the created dictionary contains the required keys."""
    data = updater.process_item_id(
        item_type='game_franchise',
        item_id='james-bond',
        youtube_url=sample_youtube_url
    )

    assert data['id']
    assert data['youtube_theme_url']


def test_process_item_id_game_franchise_by_id():
    """Tests if the provided game_id is valid and the created dictionary contains the required keys."""
    data = updater.process_item_id(
        item_type='game_franchise',
        item_id=37,
        youtube_url=sample_youtube_url
    )

    assert data['id']
    assert data['youtube_theme_url']


def test_process_item_id_movie():
    """Tests if the provided movie is valid and the created dictionary contains the required keys."""
    data = updater.process_item_id(
        item_type='movie',
        item_id=710,
        youtube_url=sample_youtube_url
    )

    assert data['id']
    assert data['youtube_theme_url']


def test_process_item_id_movie_collection():
    """Tests if the provided movie collection is valid and the created dictionary contains the required keys."""
    data = updater.process_item_id(
        item_type='movie_collection',
        item_id=645,
        youtube_url=sample_youtube_url
    )

    assert data['id']
    assert data['youtube_theme_url']
