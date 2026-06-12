"""Submission queue eligibility helpers."""

# standard imports
import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


AUTO_APPROVED_USERS_FILE = 'auto_approved_users.json'


@dataclass(frozen=True)
class QueueEligibilityResult:
    """
    Result of a queue eligibility evaluation.

    Attributes
    ----------
    queue_eligible : bool
        Whether the submission should receive the queue label.
    user_id : str
        GitHub user id of the issue author.
    reason : str
        Machine-readable reason for the eligibility decision.
    """

    queue_eligible: bool
    user_id: str
    reason: str


def normalize_user_id(user_id: object) -> str:
    """
    Normalize a GitHub user id for matching.

    Parameters
    ----------
    user_id : object
        GitHub user id to normalize.

    Returns
    -------
    str
        Trimmed user id string.
    """
    if user_id is None:
        return ''

    return str(user_id).strip()


def load_auto_approved_user_ids(auto_approved_users_file: Path) -> frozenset[str]:
    """
    Load auto-approved GitHub user ids from a JSON file.

    Parameters
    ----------
    auto_approved_users_file : pathlib.Path
        JSON file containing auto-approved user objects.

    Returns
    -------
    frozenset[str]
        Normalized GitHub user ids.
    """
    try:
        with auto_approved_users_file.open(encoding='utf-8') as auto_approved_users_f:
            auto_approved_users = json.load(auto_approved_users_f)
    except (OSError, json.JSONDecodeError):
        return frozenset()

    if not isinstance(auto_approved_users, list):
        return frozenset()

    return frozenset(
        normalized_user_id
        for user in auto_approved_users
        if isinstance(user, dict)
        if (normalized_user_id := normalize_user_id(user.get('user_id', '')))
    )


def evaluate_queue_eligibility(user_id: object,
                               auto_approved_user_ids: Iterable[object]) -> QueueEligibilityResult:
    """
    Evaluate whether a submission is eligible to be queued automatically.

    Parameters
    ----------
    user_id : object
        GitHub user id of the issue author.
    auto_approved_user_ids : Iterable[object]
        GitHub user ids eligible for automatic queueing.

    Returns
    -------
    QueueEligibilityResult
        Eligibility decision and supporting metadata.
    """
    normalized_user_id = normalize_user_id(user_id=user_id)
    if not normalized_user_id:
        return QueueEligibilityResult(
            queue_eligible=False,
            user_id='',
            reason='missing-user-id',
        )

    queue_eligible = normalized_user_id in {
        normalize_user_id(user_id=auto_approved_user_id)
        for auto_approved_user_id in auto_approved_user_ids
    }
    reason = 'auto-approved-user' if queue_eligible else 'not-auto-approved-user'

    return QueueEligibilityResult(
        queue_eligible=queue_eligible,
        user_id=normalized_user_id,
        reason=reason,
    )


def write_github_outputs(result: QueueEligibilityResult) -> None:
    """
    Write queue eligibility results in GitHub Actions output format.

    Parameters
    ----------
    result : QueueEligibilityResult
        Eligibility result to serialize.

    Returns
    -------
    None
    """
    outputs = {
        'queue_eligible': str(result.queue_eligible).lower(),
        'user_id': result.user_id,
        'reason': result.reason,
    }
    output_lines = [f'{key}={value}' for key, value in outputs.items()]
    output_path = os.environ.get('GITHUB_OUTPUT')

    if output_path:
        with open(output_path, 'a') as output_f:
            output_f.write('\n'.join(output_lines))
            output_f.write('\n')
    else:
        print('\n'.join(output_lines))


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for the queue eligibility check.

    Returns
    -------
    argparse.Namespace
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description='Check whether a submission is eligible for queueing.')
    parser.add_argument('--auto-approved-users-file', default=AUTO_APPROVED_USERS_FILE)
    parser.add_argument('--user-id', default=os.environ.get('ISSUE_AUTHOR_USER_ID', ''))
    return parser.parse_args()


def main() -> None:
    """
    Run the queue eligibility check and write GitHub Actions outputs.

    Returns
    -------
    None
    """
    args = parse_args()
    auto_approved_user_ids = load_auto_approved_user_ids(
        auto_approved_users_file=Path(args.auto_approved_users_file),
    )
    result = evaluate_queue_eligibility(
        user_id=args.user_id,
        auto_approved_user_ids=auto_approved_user_ids,
    )
    write_github_outputs(result=result)


if __name__ == '__main__':
    main()
