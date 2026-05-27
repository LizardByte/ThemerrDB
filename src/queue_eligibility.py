"""Submission queue eligibility helpers."""

# standard imports
import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


CONTRIBUTION_THRESHOLD = 15
IGDB_HOST = 'igdb.com'
TMDB_HOST = 'themoviedb.org'

CATEGORY_BY_HOST_AND_PATH = {
    (IGDB_HOST, 'games'): 'games',
    (IGDB_HOST, 'collections'): 'game_collections',
    (IGDB_HOST, 'franchises'): 'game_franchises',
    (TMDB_HOST, 'movie'): 'movies',
    (TMDB_HOST, 'collection'): 'movie_collections',
    (TMDB_HOST, 'tv'): 'tv_shows',
}


@dataclass(frozen=True)
class QueueEligibilityResult:
    """
    Result of a queue eligibility evaluation.

    Attributes
    ----------
    queue_eligible : bool
        Whether the submission should receive the queue label.
    category : str
        Database category derived from the submission URL.
    contribution_count : int
        Existing contribution count for the submitter in the derived category.
    reason : str
        Machine-readable reason for the eligibility decision.
    """

    queue_eligible: bool
    category: str
    contribution_count: int
    reason: str


def get_submission_category(database_url: str) -> str:
    """
    Return the database category for a submission URL.

    Parameters
    ----------
    database_url : str
        Database URL from the issue submission.

    Returns
    -------
    str
        Top-level database category directory.

    Raises
    ------
    ValueError
        If the URL cannot be mapped to a known database category.
    """
    parsed_url = urlparse(database_url.strip())
    hostname = parsed_url.hostname or ''
    hostname = hostname.removeprefix('www.')
    path_parts = [part for part in parsed_url.path.split('/') if part]

    if not path_parts:
        raise ValueError(f'Unsupported database URL: {database_url}')

    category = CATEGORY_BY_HOST_AND_PATH.get((hostname, path_parts[0]))
    if not category:
        raise ValueError(f'Unsupported database URL: {database_url}')

    return category


def get_contribution_count(contributor_data: dict, user_id: str) -> int:
    """
    Return a contributor's total contributions from contributor metadata.

    Parameters
    ----------
    contributor_data : dict
        Parsed contents of a category ``contributors.json`` file.
    user_id : str
        GitHub user ID to look up.

    Returns
    -------
    int
        Sum of the contributor's added and edited item counts, or zero when the
        metadata is missing or malformed.
    """
    if not isinstance(contributor_data, dict):
        return 0

    contributor = contributor_data.get(str(user_id), {})
    if not isinstance(contributor, dict):
        return 0

    try:
        return int(contributor.get('items_added', 0)) + int(contributor.get('items_edited', 0))
    except (TypeError, ValueError):
        return 0


def load_contribution_count(database_root: Path, category: str, user_id: str) -> int:
    """
    Load a contributor's category contribution count from disk.

    Parameters
    ----------
    database_root : pathlib.Path
        Root directory containing category database folders.
    category : str
        Category directory to inspect.
    user_id : str
        GitHub user ID to look up.

    Returns
    -------
    int
        Contributor count for the category, or zero when the contributors file
        is absent or unreadable.
    """
    contributors_file = database_root / category / 'contributors.json'
    if not contributors_file.exists():
        return 0

    try:
        with contributors_file.open() as contributor_f:
            contributor_data = json.load(contributor_f)
    except (OSError, json.JSONDecodeError):
        return 0

    return get_contribution_count(contributor_data=contributor_data, user_id=user_id)


def evaluate_queue_eligibility(submission: dict,
                               database_root: Path,
                               user_id: str,
                               threshold: int = CONTRIBUTION_THRESHOLD) -> QueueEligibilityResult:
    """
    Evaluate whether a submission is eligible to be queued automatically.

    Parameters
    ----------
    submission : dict
        Parsed issue submission data.
    database_root : pathlib.Path
        Root directory containing category database folders.
    user_id : str
        GitHub user ID of the issue author.
    threshold : int, optional
        Minimum prior category contribution count that must be exceeded.

    Returns
    -------
    QueueEligibilityResult
        Eligibility decision and supporting metadata.
    """
    if not user_id:
        return QueueEligibilityResult(
            queue_eligible=False,
            category='',
            contribution_count=0,
            reason='missing-user-id',
        )

    try:
        category = get_submission_category(database_url=submission['database_url'])
    except (KeyError, ValueError):
        return QueueEligibilityResult(
            queue_eligible=False,
            category='',
            contribution_count=0,
            reason='unsupported-category',
        )

    contribution_count = load_contribution_count(
        database_root=database_root,
        category=category,
        user_id=user_id,
    )
    queue_eligible = contribution_count > threshold
    reason = 'eligible' if queue_eligible else 'below-threshold'

    return QueueEligibilityResult(
        queue_eligible=queue_eligible,
        category=category,
        contribution_count=contribution_count,
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
        'category': result.category,
        'contribution_count': str(result.contribution_count),
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
    parser.add_argument('--submission-file', default='submission.json')
    parser.add_argument('--database-root', default='database')
    parser.add_argument('--threshold', type=int, default=CONTRIBUTION_THRESHOLD)
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

    try:
        with open(args.submission_file) as submission_f:
            submission = json.load(submission_f)
    except (OSError, json.JSONDecodeError):
        result = QueueEligibilityResult(
            queue_eligible=False,
            category='',
            contribution_count=0,
            reason='submission-read-error',
        )
    else:
        result = evaluate_queue_eligibility(
            submission=submission,
            database_root=Path(args.database_root),
            user_id=args.user_id,
            threshold=args.threshold,
        )
    write_github_outputs(result=result)


if __name__ == '__main__':
    main()
