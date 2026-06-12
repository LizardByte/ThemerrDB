# standard imports
import json
import sys
from pathlib import Path

# local imports
from src import queue_eligibility


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def write_auto_approved_users_file(tmp_path, auto_approved_users):
    auto_approved_users_file = tmp_path / 'auto_approved_users.json'
    auto_approved_users_file.write_text(json.dumps(auto_approved_users), encoding='utf-8')
    return auto_approved_users_file


def test_load_auto_approved_user_ids_loads_user_ids(tmp_path):
    auto_approved_users_file = write_auto_approved_users_file(tmp_path, [
        {
            'user_id': 42013603,
            'username': 'ReenigneArcher',
        },
        {
            'user_id': ' 88998541 ',
            'username': 'renamed-user',
        },
    ])

    auto_approved_user_ids = queue_eligibility.load_auto_approved_user_ids(
        auto_approved_users_file=auto_approved_users_file,
    )

    assert auto_approved_user_ids == frozenset({'42013603', '88998541'})


def test_root_auto_approved_users_file_contains_expected_user_ids():
    auto_approved_user_ids = queue_eligibility.load_auto_approved_user_ids(
        auto_approved_users_file=REPOSITORY_ROOT / queue_eligibility.AUTO_APPROVED_USERS_FILE,
    )

    assert auto_approved_user_ids == frozenset({'42013603', '88998541', '30657709'})


def test_load_auto_approved_user_ids_ignores_malformed_entries(tmp_path):
    auto_approved_users_file = write_auto_approved_users_file(tmp_path, [
        [],
        {
            'username': 'missing-id',
        },
        {
            'user_id': None,
            'username': 'null-id',
        },
        {
            'user_id': '1234',
            'username': 'valid-user',
        },
    ])

    auto_approved_user_ids = queue_eligibility.load_auto_approved_user_ids(
        auto_approved_users_file=auto_approved_users_file,
    )

    assert auto_approved_user_ids == frozenset({'1234'})


def test_load_auto_approved_user_ids_fails_closed_for_missing_or_bad_file(tmp_path):
    missing_file = tmp_path / 'missing.json'
    bad_file = tmp_path / 'bad.json'
    bad_file.write_text('{', encoding='utf-8')

    assert queue_eligibility.load_auto_approved_user_ids(auto_approved_users_file=missing_file) == frozenset()
    assert queue_eligibility.load_auto_approved_user_ids(auto_approved_users_file=bad_file) == frozenset()


def test_load_auto_approved_user_ids_fails_closed_for_non_list_json(tmp_path):
    auto_approved_users_file = write_auto_approved_users_file(tmp_path, {
        'user_id': '1234',
    })

    auto_approved_user_ids = queue_eligibility.load_auto_approved_user_ids(
        auto_approved_users_file=auto_approved_users_file,
    )

    assert auto_approved_user_ids == frozenset()


def test_evaluate_queue_eligibility_allows_auto_approved_user_id():
    result = queue_eligibility.evaluate_queue_eligibility(
        user_id='42013603',
        auto_approved_user_ids={'42013603'},
    )

    assert result.queue_eligible
    assert result.user_id == '42013603'
    assert result.reason == 'auto-approved-user'


def test_evaluate_queue_eligibility_normalizes_user_ids():
    result = queue_eligibility.evaluate_queue_eligibility(
        user_id=88998541,
        auto_approved_user_ids={' 88998541 '},
    )

    assert result.queue_eligible
    assert result.user_id == '88998541'


def test_evaluate_queue_eligibility_rejects_users_outside_allowlist():
    result = queue_eligibility.evaluate_queue_eligibility(
        user_id='1234',
        auto_approved_user_ids={'42013603'},
    )

    assert not result.queue_eligible
    assert result.user_id == '1234'
    assert result.reason == 'not-auto-approved-user'


def test_evaluate_queue_eligibility_does_not_match_username():
    result = queue_eligibility.evaluate_queue_eligibility(
        user_id='ReenigneArcher',
        auto_approved_user_ids={'42013603'},
    )

    assert not result.queue_eligible
    assert result.reason == 'not-auto-approved-user'


def test_evaluate_queue_eligibility_fails_closed_without_user():
    result = queue_eligibility.evaluate_queue_eligibility(
        user_id='',
        auto_approved_user_ids={'42013603'},
    )

    assert not result.queue_eligible
    assert result.user_id == ''
    assert result.reason == 'missing-user-id'


def test_write_github_outputs_writes_to_output_file(tmp_path, monkeypatch):
    output_file = tmp_path / 'github_output'
    monkeypatch.setenv('GITHUB_OUTPUT', str(output_file))

    queue_eligibility.write_github_outputs(
        result=queue_eligibility.QueueEligibilityResult(
            queue_eligible=True,
            user_id='42013603',
            reason='auto-approved-user',
        ),
    )

    assert output_file.read_text() == (
        'queue_eligible=true\n'
        'user_id=42013603\n'
        'reason=auto-approved-user\n'
    )


def test_write_github_outputs_prints_without_output_file(monkeypatch, capsys):
    monkeypatch.delenv('GITHUB_OUTPUT', raising=False)

    queue_eligibility.write_github_outputs(
        result=queue_eligibility.QueueEligibilityResult(
            queue_eligible=False,
            user_id='1234',
            reason='not-auto-approved-user',
        ),
    )

    captured = capsys.readouterr()
    assert captured.out == (
        'queue_eligible=false\n'
        'user_id=1234\n'
        'reason=not-auto-approved-user\n'
    )


def test_parse_args_uses_cli_value(monkeypatch):
    monkeypatch.setenv('ISSUE_AUTHOR_USER_ID', 'env-user-id')
    monkeypatch.setattr(sys, 'argv', [
        'queue_eligibility',
        '--auto-approved-users-file',
        'custom-auto-approved-users.json',
        '--user-id',
        'cli-user-id',
    ])

    args = queue_eligibility.parse_args()

    assert args.auto_approved_users_file == 'custom-auto-approved-users.json'
    assert args.user_id == 'cli-user-id'


def test_parse_args_defaults_to_env_value(monkeypatch):
    monkeypatch.setenv('ISSUE_AUTHOR_USER_ID', 'env-user-id')
    monkeypatch.setattr(sys, 'argv', ['queue_eligibility'])

    args = queue_eligibility.parse_args()

    assert args.auto_approved_users_file == queue_eligibility.AUTO_APPROVED_USERS_FILE
    assert args.user_id == 'env-user-id'


def test_main_writes_queue_eligible_result(tmp_path, monkeypatch):
    auto_approved_users_file = write_auto_approved_users_file(tmp_path, [
        {
            'user_id': 42013603,
            'username': 'ReenigneArcher',
        },
    ])
    output_file = tmp_path / 'github_output'
    monkeypatch.setenv('GITHUB_OUTPUT', str(output_file))
    monkeypatch.setattr(sys, 'argv', [
        'queue_eligibility',
        '--auto-approved-users-file',
        str(auto_approved_users_file),
        '--user-id',
        '42013603',
    ])

    queue_eligibility.main()

    assert 'queue_eligible=true' in output_file.read_text()


def test_main_fails_closed_for_missing_user(monkeypatch, capsys):
    monkeypatch.delenv('GITHUB_OUTPUT', raising=False)
    monkeypatch.delenv('ISSUE_AUTHOR_USER_ID', raising=False)
    monkeypatch.setattr(sys, 'argv', ['queue_eligibility'])

    queue_eligibility.main()

    captured = capsys.readouterr()
    assert 'queue_eligible=false' in captured.out
    assert 'reason=missing-user-id' in captured.out
