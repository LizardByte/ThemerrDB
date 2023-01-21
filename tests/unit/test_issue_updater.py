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

valid_submission = dict(
    igdb_url='https://www.igdb.com/games/goldeneye-007',
    themoviedb_url='https://www.themoviedb.org/movie/710-goldeneye',
    youtube_theme_url='https://www.youtube.com/watch?v=qGPBFvDz_HM'
)


def test_igdb_authorization():
    """Tests if access token is returned from igdb_authorization method."""
    auth = updater.igdb_authorization(
        client_id=os.environ["TWITCH_CLIENT_ID"],
        client_secret=os.environ["TWITCH_CLIENT_SECRET"]
    )

    assert auth['access_token']


def test_check_youtube():
    """Tests if the provided YouTube url is valid and returns a valid url."""
    youtube_url = updater.check_youtube(data=valid_submission)

    assert youtube_url.startswith('https://www.youtube')


def test_process_igdb_id():
    """Tests if the provided game_slug is valid and the created dictionary contains the required keys."""
    data = updater.process_igdb_id(
        game_slug='goldeneye-007',
        youtube_url='https://www.youtube.com/watch?v=qGPBFvDz_HM'
    )

    assert data['id']
    assert data['youtube_theme_url']


def test_process_tmdb_id():
    """Tests if the provided movie is valid and the created dictionary contains the required keys."""
    data = updater.process_tmdb_id(
        tmdb_id=710,
        youtube_url='https://www.youtube.com/watch?v=qGPBFvDz_HM'
    )

    assert data['id']
    assert data['youtube_theme_url']
