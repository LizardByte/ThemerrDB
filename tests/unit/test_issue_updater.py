"""
test_issue_updater.py

This module contains unit tests for the issue_updater module. The issue_updater module is responsible for
verifying and updating requests to update the ThemerrDB database. The tests in this module ensure that the
issue_updater module is functioning correctly by validating URLs and checking that the correct IDs are returned.
"""
# local imports
import issue_updater

valid_submission = dict(
    igdb_url='https://www.igdb.com/games/goldeneye-007',
    themoviedb_url='https://www.themoviedb.org/movie/710-goldeneye',
    youtube_theme_url='https://www.youtube.com/watch?v=qGPBFvDz_HM'
)


# todo - use igdb api instead of scraping
# def test_valid_igdb_url():
#     """Tests if the provided IGDB url is valid and returns the correct ID."""
#     issue_updater.check_igdb(data=valid_submission)
#
#     assert issue_updater.item['igdb_id'] is '1638'


def test_valid_themoviedb_url():
    """Tests if the provided TheMovieDB url is valid and returns the correct ID."""
    issue_updater.check_themoviedb(data=valid_submission)

    assert issue_updater.item['id'] == 710
    assert issue_updater.item['imdb_id'] == 'tt0113189'


def test_valid_youtube_url():
    """Tests if the provided YouTube url is valid and returns a valid url."""
    issue_updater.check_youtube(data=valid_submission)

    assert issue_updater.item['youtube_theme_url'].startswith('https://www.youtube')
