# standard imports
import json
import sys

# lib imports
import pytest

# local imports
from src import queue_eligibility


@pytest.mark.parametrize('database_url, category', [
    ('https://www.igdb.com/games/goldeneye-007', 'games'),
    ('https://www.igdb.com/collections/james-bond', 'game_collections'),
    ('https://www.igdb.com/franchises/james-bond', 'game_franchises'),
    ('https://www.themoviedb.org/movie/10378-big-buck-bunny', 'movies'),
    ('https://www.themoviedb.org/collection/645-james-bond-collection', 'movie_collections'),
    ('https://www.themoviedb.org/tv/1930-the-beverly-hillbillies', 'tv_shows'),
])
def test_get_submission_category(database_url, category):
    assert queue_eligibility.get_submission_category(database_url=database_url) == category


def test_get_submission_category_raises_for_unsupported_url():
    with pytest.raises(ValueError):
        queue_eligibility.get_submission_category(database_url='https://example.com/movie/1')


def test_get_submission_category_raises_for_missing_path():
    with pytest.raises(ValueError):
        queue_eligibility.get_submission_category(database_url='https://www.igdb.com')


def test_get_contribution_count_fails_closed_for_bad_data():
    assert queue_eligibility.get_contribution_count(contributor_data=[], user_id='1234') == 0
    assert queue_eligibility.get_contribution_count(contributor_data={'1234': []}, user_id='1234') == 0
    assert queue_eligibility.get_contribution_count(
        contributor_data={'1234': {'items_added': 'bad'}},
        user_id='1234',
    ) == 0


def test_evaluate_queue_eligibility_requires_more_than_threshold(tmp_path):
    category_dir = tmp_path / 'movies'
    category_dir.mkdir()
    contributors_file = category_dir / 'contributors.json'
    contributors_file.write_text(json.dumps({
        'exact': {
            'items_added': 5,
            'items_edited': 10,
        },
        'eligible': {
            'items_added': 6,
            'items_edited': 10,
        },
    }))

    submission = {
        'database_url': 'https://www.themoviedb.org/movie/10378-big-buck-bunny',
    }

    exact_result = queue_eligibility.evaluate_queue_eligibility(
        submission=submission,
        database_root=tmp_path,
        user_id='exact',
    )
    eligible_result = queue_eligibility.evaluate_queue_eligibility(
        submission=submission,
        database_root=tmp_path,
        user_id='eligible',
    )

    assert exact_result.contribution_count == 15
    assert not exact_result.queue_eligible
    assert eligible_result.contribution_count == 16
    assert eligible_result.queue_eligible


def test_evaluate_queue_eligibility_uses_submission_category(tmp_path):
    movie_dir = tmp_path / 'movies'
    tv_dir = tmp_path / 'tv_shows'
    movie_dir.mkdir()
    tv_dir.mkdir()
    (movie_dir / 'contributors.json').write_text(json.dumps({
        '1234': {
            'items_added': 20,
            'items_edited': 0,
        },
    }))
    (tv_dir / 'contributors.json').write_text(json.dumps({
        '1234': {
            'items_added': 1,
            'items_edited': 0,
        },
    }))

    result = queue_eligibility.evaluate_queue_eligibility(
        submission={
            'database_url': 'https://www.themoviedb.org/tv/1930-the-beverly-hillbillies',
        },
        database_root=tmp_path,
        user_id='1234',
    )

    assert result.category == 'tv_shows'
    assert result.contribution_count == 1
    assert not result.queue_eligible


def test_evaluate_queue_eligibility_fails_closed_without_user(tmp_path):
    result = queue_eligibility.evaluate_queue_eligibility(
        submission={'database_url': 'https://www.themoviedb.org/movie/10378-big-buck-bunny'},
        database_root=tmp_path,
        user_id='',
    )

    assert not result.queue_eligible
    assert result.reason == 'missing-user-id'


@pytest.mark.parametrize('submission', [
    {},
    {'database_url': 'https://example.com/movie/1'},
])
def test_evaluate_queue_eligibility_fails_closed_for_bad_submission(tmp_path, submission):
    result = queue_eligibility.evaluate_queue_eligibility(
        submission=submission,
        database_root=tmp_path,
        user_id='1234',
    )

    assert not result.queue_eligible
    assert result.reason == 'unsupported-category'


def test_load_contribution_count_returns_zero_for_missing_file(tmp_path):
    contribution_count = queue_eligibility.load_contribution_count(
        database_root=tmp_path,
        category='movies',
        user_id='1234',
    )

    assert contribution_count == 0


def test_load_contribution_count_fails_closed_for_bad_contributor_file(tmp_path):
    category_dir = tmp_path / 'movies'
    category_dir.mkdir()
    (category_dir / 'contributors.json').write_text('{')

    contribution_count = queue_eligibility.load_contribution_count(
        database_root=tmp_path,
        category='movies',
        user_id='1234',
    )

    assert contribution_count == 0


def test_write_github_outputs_writes_to_output_file(tmp_path, monkeypatch):
    output_file = tmp_path / 'github_output'
    monkeypatch.setenv('GITHUB_OUTPUT', str(output_file))

    queue_eligibility.write_github_outputs(
        result=queue_eligibility.QueueEligibilityResult(
            queue_eligible=True,
            category='movies',
            contribution_count=16,
            reason='eligible',
        ),
    )

    assert output_file.read_text() == (
        'queue_eligible=true\n'
        'category=movies\n'
        'contribution_count=16\n'
        'reason=eligible\n'
    )


def test_write_github_outputs_prints_without_output_file(monkeypatch, capsys):
    monkeypatch.delenv('GITHUB_OUTPUT', raising=False)

    queue_eligibility.write_github_outputs(
        result=queue_eligibility.QueueEligibilityResult(
            queue_eligible=False,
            category='tv_shows',
            contribution_count=1,
            reason='below-threshold',
        ),
    )

    captured = capsys.readouterr()
    assert captured.out == (
        'queue_eligible=false\n'
        'category=tv_shows\n'
        'contribution_count=1\n'
        'reason=below-threshold\n'
    )


def test_parse_args_uses_cli_and_env(monkeypatch):
    monkeypatch.setenv('ISSUE_AUTHOR_USER_ID', '1234')
    monkeypatch.setattr(sys, 'argv', [
        'queue_eligibility',
        '--submission-file',
        'custom-submission.json',
        '--database-root',
        'custom-database',
        '--threshold',
        '3',
    ])

    args = queue_eligibility.parse_args()

    assert args.submission_file == 'custom-submission.json'
    assert args.database_root == 'custom-database'
    assert args.threshold == 3
    assert args.user_id == '1234'


def test_main_writes_queue_eligible_result(tmp_path, monkeypatch):
    submission_file = tmp_path / 'submission.json'
    output_file = tmp_path / 'github_output'
    database_root = tmp_path / 'database'
    category_dir = database_root / 'movies'
    category_dir.mkdir(parents=True)

    submission_file.write_text(json.dumps({
        'database_url': 'https://www.themoviedb.org/movie/10378-big-buck-bunny',
    }))
    (category_dir / 'contributors.json').write_text(json.dumps({
        '1234': {
            'items_added': 16,
            'items_edited': 0,
        },
    }))

    monkeypatch.setenv('GITHUB_OUTPUT', str(output_file))
    monkeypatch.setattr(sys, 'argv', [
        'queue_eligibility',
        '--submission-file',
        str(submission_file),
        '--database-root',
        str(database_root),
        '--user-id',
        '1234',
    ])

    queue_eligibility.main()

    assert 'queue_eligible=true' in output_file.read_text()


def test_main_fails_closed_for_unreadable_submission(monkeypatch, capsys):
    monkeypatch.delenv('GITHUB_OUTPUT', raising=False)
    monkeypatch.setattr(sys, 'argv', [
        'queue_eligibility',
        '--submission-file',
        'missing-submission.json',
        '--user-id',
        '1234',
    ])

    queue_eligibility.main()

    captured = capsys.readouterr()
    assert 'queue_eligible=false' in captured.out
    assert 'reason=submission-read-error' in captured.out
