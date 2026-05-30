# standard imports
import argparse
import base64
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
import json
from operator import itemgetter
import os
from queue import Queue
import re
import sys
import threading
import time
from typing import Callable, Optional, Union
from threading import Lock
from urllib.parse import quote

# lib imports
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from igdb.wrapper import IGDBWrapper
import isodate
import requests
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# load env
from dotenv import load_dotenv
load_dotenv()

# setup matplotlib
matplotlib.use('Agg')

# args placeholder
args = None

# databases
databases = {
    'game': {
        'all_items': [],
        'path': os.path.join('database', 'games', 'igdb'),
        'title': 'Games',
        'type': 'game',
        'api_endpoint': 'games',
        'api_fields': [
            'cover.url',
            'name',
            'release_dates.y',
            'slug',
            'summary',
            'url'
        ]
    },
    'game_collection': {
        'all_items': [],
        'path': os.path.join('database', 'game_collections', 'igdb'),
        'title': 'Game Collections',
        'type': 'game_collection',
        'api_endpoint': 'collections',
        'api_fields': [
            'name',
            'slug',
            'url'
        ]
    },
    'game_franchise': {
        'all_items': [],
        'path': os.path.join('database', 'game_franchises', 'igdb'),
        'title': 'Game Franchises',
        'type': 'game_franchise',
        'api_endpoint': 'franchises',
        'api_fields': [
            'name',
            'slug',
            'url'
        ]
    },
    'movie': {
        'all_items': [],
        'path': os.path.join('database', 'movies', 'themoviedb'),
        'title': 'Movies',
        'type': 'movie',
        'api_endpoint': 'movie',
    },
    'movie_collection': {
        'all_items': [],
        'path': os.path.join('database', 'movie_collections', 'themoviedb'),
        'title': 'Movie Collections',
        'type': 'movie_collection',
        'api_endpoint': 'collection',
    },
    'tv_show': {
        'all_items': [],
        'path': os.path.join('database', 'tv_shows', 'themoviedb'),
        'title': 'TV Shows',
        'type': 'tv_show',
        'api_endpoint': 'tv',
    },
}
imdb_path = os.path.join('database', 'movies', 'imdb')

AVATAR_SIZE = 96
TOP_CONTRIBUTORS_LIMIT = 5
TOP_CONTRIBUTORS_CATEGORY_LIMIT = 3
TOP_CONTRIBUTORS_BASENAME = 'top_contributors'
TOP_CONTRIBUTORS_FILENAME = f'{TOP_CONTRIBUTORS_BASENAME}.svg'
JSON_EXTENSION = '.json'
PNG_CONTENT_TYPE = 'image/png'
APPROVE_THEME_LABEL = 'approve-theme'
CONTRIBUTION_BADGE_LABEL = 'contributions'
CONTRIBUTION_BADGE_STYLE = 'for-the-badge'
DEFAULT_GITHUB_REPOSITORY = 'LizardByte/ThemerrDB'
CONTRIBUTOR_IMAGE_WIDTH = 900
CONTRIBUTOR_IMAGE_MARGIN = 24
CONTRIBUTOR_CARD_GAP = 16
CONTRIBUTOR_SECTION_HEADER_HEIGHT = 40
CONTRIBUTOR_ROW_HEIGHT = 32
CONTRIBUTOR_CATEGORIES = (
    'movies',
    'tv_shows',
    'games',
    'movie_collections',
    'game_collections',
    'game_franchises',
)
CONTRIBUTOR_IMAGE_SECTIONS = (
    {
        'title': 'All',
        'categories': CONTRIBUTOR_CATEGORIES,
        'output': TOP_CONTRIBUTORS_FILENAME,
    },
    {
        'title': 'Movies',
        'categories': ('movies',),
        'output': os.path.join('movies', TOP_CONTRIBUTORS_FILENAME),
    },
    {
        'title': 'TV Shows',
        'categories': ('tv_shows',),
        'output': os.path.join('tv_shows', TOP_CONTRIBUTORS_FILENAME),
    },
    {
        'title': 'Games',
        'categories': ('games',),
        'output': os.path.join('games', TOP_CONTRIBUTORS_FILENAME),
    },
    {
        'title': 'Movie Collections',
        'categories': ('movie_collections',),
        'output': os.path.join('movie_collections', TOP_CONTRIBUTORS_FILENAME),
    },
    {
        'title': 'Game Collections',
        'categories': ('game_collections',),
        'output': os.path.join('game_collections', TOP_CONTRIBUTORS_FILENAME),
    },
    {
        'title': 'Game Franchises',
        'categories': ('game_franchises',),
        'output': os.path.join('game_franchises', TOP_CONTRIBUTORS_FILENAME),
    },
)
DEPRECATED_CONTRIBUTOR_IMAGE_OUTPUTS = tuple(
    os.path.join(category, TOP_CONTRIBUTORS_FILENAME)
    for category in CONTRIBUTOR_CATEGORIES
)
DATABASE_URL_PATTERNS = {
    'game': r'https://www\.igdb\.com/games/(.+)/*.*',
    'game_collection': r'https://www\.igdb\.com/collections/(.+)/*.*',
    'game_franchise': r'https://www\.igdb\.com/franchises/(.+)/*.*',
    'movie': r'https://www\.themoviedb\.org/movie/(\d+)-*.*',
    'movie_collection': r'https://www\.themoviedb\.org/collection/(\d+)-*.*',
    'tv_show': r'https://www\.themoviedb\.org/tv/(\d+)-*.*',
}

# setup queue
queue = Queue()


@dataclass
class ContributorProfile:
    user_id: str
    login: str
    name: str
    avatar_url: str


@dataclass
class TopContributor:
    user_id: str
    count: int
    profile: ContributorProfile
    avatar_data_uri: Optional[str] = None


class RateLimiter:
    """Rate limiter to control API request frequency."""

    def __init__(self, max_requests_per_second: float):
        """
        Initialize rate limiter.

        Parameters
        ----------
        max_requests_per_second : float
            Maximum number of requests allowed per second.
        """
        self.max_requests_per_second = max_requests_per_second
        self.min_interval = 1.0 / max_requests_per_second
        self.last_request_time = 0
        self.lock = Lock()

    def wait(self):
        """Wait if necessary to maintain rate limit."""
        with self.lock:
            now = time.time()
            time_since_last = now - self.last_request_time
            if time_since_last < self.min_interval:
                time.sleep(self.min_interval - time_since_last)
            self.last_request_time = time.time()


# Rate limiters for different APIs
tmdb_limiter = RateLimiter(max_requests_per_second=40)  # TMDB allows 40 requests/second
igdb_limiter = RateLimiter(max_requests_per_second=4)   # IGDB allows 4 requests/second


def print_github_warning(message: str) -> None:
    """
    Print a warning message.

    Emits a GitHub Actions warning annotation when running in CI, otherwise prints a plain warning.

    Parameters
    ----------
    message : str
        The warning message to print.
    """
    if os.environ.get('GITHUB_ACTIONS'):
        print(f'::warning::{message}')
    else:
        print(f'WARNING: {message}')


def print_github_error(message: str) -> None:
    """
    Print an error message.

    Emits a GitHub Actions error annotation when running in CI, otherwise prints a plain error.

    Parameters
    ----------
    message : str
        The error message to print.
    """
    if os.environ.get('GITHUB_ACTIONS'):
        print(f'::error::{message}')
    else:
        print(f'ERROR: {message}')


def create_github_session() -> requests.Session:
    """
    Create a GitHub API session.

    Returns
    -------
    requests.Session
        Session configured with GitHub headers and an optional token.
    """
    session = requests.Session()
    session.headers.update({
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'ThemerrDB contributor image generator',
    })

    token = os.environ.get('GITHUB_TOKEN')
    if token:
        session.headers.update({'Authorization': f'Bearer {token}'})

    return session


def get_contributor_total(contributor: dict) -> int:
    """
    Return the total number of added and edited items for a contributor.

    Parameters
    ----------
    contributor : dict
        Contributor metadata from a ``contributors.json`` file.

    Returns
    -------
    int
        Total added and edited item count.
    """
    if not isinstance(contributor, dict):
        return 0

    try:
        return max(
            int(contributor.get('items_added', 0)) +
            int(contributor.get('items_edited', 0)),
            0
        )
    except (TypeError, ValueError):
        return 0


def load_contributor_totals(database_root: str, categories: tuple) -> dict:
    """
    Load and aggregate contributor totals for one or more categories.

    Parameters
    ----------
    database_root : str
        Root directory containing category database folders.
    categories : tuple
        Category directory names to aggregate.

    Returns
    -------
    dict
        Mapping of GitHub user ID to total contribution count.
    """
    totals = defaultdict(int)

    for category in categories:
        contributors_file = os.path.join(database_root, category, 'contributors.json')
        if not os.path.exists(contributors_file):
            continue

        try:
            with open(contributors_file, 'r', encoding='utf-8') as contributor_f:
                contributor_data = json.load(contributor_f)
        except (OSError, json.JSONDecodeError) as exc:
            print_github_warning(f'Unable to read contributor data from {contributors_file}: {exc}')
            continue

        if not isinstance(contributor_data, dict):
            continue

        for user_id, contributor in contributor_data.items():
            count = get_contributor_total(contributor=contributor)
            if count:
                totals[str(user_id)] += count

    return dict(totals)


def resolve_contributor_profile(user_id: str, session: requests.Session) -> ContributorProfile:
    """
    Resolve a GitHub user ID to profile details.

    Parameters
    ----------
    user_id : str
        Numeric GitHub user ID stored in contributor metadata.
    session : requests.Session
        GitHub API session.

    Returns
    -------
    ContributorProfile
        Resolved profile data, or a fallback profile when lookup fails.
    """
    fallback = ContributorProfile(
        user_id=user_id,
        login=f'user-{user_id}',
        name=f'User {user_id}',
        avatar_url=f'https://avatars.githubusercontent.com/u/{user_id}?size={AVATAR_SIZE}',
    )

    if os.environ.get('CI_TEST'):
        return ContributorProfile(
            user_id=user_id,
            login=f'user-{user_id}',
            name=f'User {user_id}',
            avatar_url='',
        )

    try:
        response = session.get(f'https://api.github.com/user/{user_id}', timeout=15)
        response.raise_for_status()
        profile_data = response.json()
    except (requests.RequestException, ValueError) as exc:
        print_github_warning(f'Unable to resolve GitHub user {user_id}: {exc}')
        return fallback

    login = profile_data.get('login')
    if not login:
        return fallback

    return ContributorProfile(
        user_id=user_id,
        login=login,
        name=profile_data.get('name') or login,
        avatar_url=f'https://github.com/{login}.png?size={AVATAR_SIZE}',
    )


def fetch_avatar_data_uri(profile: ContributorProfile, session: requests.Session) -> Optional[str]:
    """
    Fetch a contributor avatar and return it as a data URI.

    Parameters
    ----------
    profile : ContributorProfile
        Contributor profile with an avatar URL.
    session : requests.Session
        HTTP session.

    Returns
    -------
    Optional[str]
        Data URI for the avatar image, or ``None`` when the avatar cannot be fetched.
    """
    if not profile.avatar_url:
        return None

    try:
        response = session.get(profile.avatar_url, headers={'Accept': PNG_CONTENT_TYPE}, timeout=15)
        response.raise_for_status()
    except requests.RequestException:
        return None

    content_type = response.headers.get('Content-Type', PNG_CONTENT_TYPE).split(';', 1)[0]
    if not content_type.startswith('image/'):
        content_type = PNG_CONTENT_TYPE

    avatar = base64.b64encode(response.content).decode('ascii')
    return f'data:{content_type};base64,{avatar}'


def truncate_text(value: str, max_length: int) -> str:
    """
    Truncate text for fixed-width SVG labels.

    Parameters
    ----------
    value : str
        Text value to truncate.
    max_length : int
        Maximum text length.

    Returns
    -------
    str
        Truncated text.
    """
    if len(value) <= max_length:
        return value

    return f'{value[:max_length - 3]}...'


def append_contributor_avatar(
        parts: list,
        contributor: TopContributor,
        clip_id: str,
        avatar_x: int,
        avatar_y: int,
) -> None:
    """
    Append a compact contributor avatar to SVG parts.

    Parameters
    ----------
    parts : list
        SVG markup parts to append to.
    contributor : TopContributor
        Contributor to render.
    clip_id : str
        Unique clip path ID.
    avatar_x : int
        Avatar x position.
    avatar_y : int
        Avatar y position.
    """
    avatar_size = 24
    avatar_radius = avatar_size / 2
    center_x = avatar_x + avatar_radius
    center_y = avatar_y + avatar_radius

    if contributor.avatar_data_uri:
        avatar_uri = contributor.avatar_data_uri
        parts.extend([
            f'<clipPath id="{clip_id}"><circle cx="{center_x}" cy="{center_y}" r="{avatar_radius}"/></clipPath>',
            f'<image href="{avatar_uri}" x="{avatar_x}" y="{avatar_y}" '
            f'width="{avatar_size}" height="{avatar_size}" clip-path="url(#{clip_id})" '
            'preserveAspectRatio="xMidYMid slice"/>',
        ])
    else:
        initial = escape((contributor.profile.name or contributor.profile.login or '?')[:1].upper())
        parts.extend([
            f'<circle cx="{center_x}" cy="{center_y}" r="{avatar_radius}" fill="#404040" fill-opacity="0.5"/>',
            f'<text class="placeholder" x="{center_x}" y="{center_y + 4}" text-anchor="middle">{initial}</text>',
        ])


def append_contributor_card(
        parts: list,
        section: dict,
        x: int,
        y: int,
        width: int,
        height: int,
        display_limit: int,
        card_index: int,
) -> None:
    """
    Append one compact contributor card to SVG parts.

    Parameters
    ----------
    parts : list
        SVG markup parts to append to.
    section : dict
        Contributor section metadata and resolved contributors.
    x : int
        Card x position.
    y : int
        Card y position.
    width : int
        Card width.
    height : int
        Card height.
    display_limit : int
        Maximum contributors to show in the card.
    card_index : int
        Unique card index.
    """
    visible_contributors = section['contributors'][:display_limit]
    title = escape(section['title'])
    name_max_length = 48 if width > 600 else 25
    login_max_length = 54 if width > 600 else 29
    count_x = x + width - 18

    parts.extend([
        f'<rect class="card" x="{x}" y="{y}" width="{width}" height="{height}" rx="8"/>',
        f'<text class="section-title" x="{x + 16}" y="{y + 26}">{title}</text>',
    ])

    if not visible_contributors:
        parts.append(
            f'<text class="section-meta" x="{x + (width / 2)}" y="{y + 92}" '
            'text-anchor="middle">No contributors yet</text>'
        )
        return

    for index, contributor in enumerate(visible_contributors, start=1):
        row_y = y + CONTRIBUTOR_SECTION_HEADER_HEIGHT + ((index - 1) * CONTRIBUTOR_ROW_HEIGHT)
        rank_x = x + 16
        avatar_x = x + 42
        avatar_y = row_y + 4
        text_x = avatar_x + 34
        clip_id = f'avatar-{card_index}-{index}'
        display_name = escape(truncate_text(contributor.profile.name, name_max_length))
        login = escape(truncate_text(f'@{contributor.profile.login}', login_max_length))

        parts.extend([
            f'<line class="row-line" x1="{x + 16}" x2="{x + width - 16}" y1="{row_y}" y2="{row_y}"/>',
            f'<text class="rank" x="{rank_x}" y="{row_y + 20}">{index}</text>',
        ])
        append_contributor_avatar(
            parts=parts,
            contributor=contributor,
            clip_id=clip_id,
            avatar_x=avatar_x,
            avatar_y=avatar_y,
        )
        parts.extend([
            f'<text class="name" x="{text_x}" y="{row_y + 13}">{display_name}</text>',
            f'<text class="login" x="{text_x}" y="{row_y + 27}">{login}</text>',
            f'<text class="count" x="{count_x}" y="{row_y + 21}" text-anchor="end">{contributor.count:,}</text>',
        ])


def render_top_contributor_svg(sections: list) -> str:
    """
    Render a combined top contributors SVG.

    Parameters
    ----------
    sections : list
        Contributor sections and resolved contributors.

    Returns
    -------
    str
        SVG markup.
    """
    all_card_height = CONTRIBUTOR_SECTION_HEADER_HEIGHT + (TOP_CONTRIBUTORS_LIMIT * CONTRIBUTOR_ROW_HEIGHT) + 20
    category_card_height = CONTRIBUTOR_SECTION_HEADER_HEIGHT + (
        TOP_CONTRIBUTORS_CATEGORY_LIMIT * CONTRIBUTOR_ROW_HEIGHT
    ) + 20
    content_width = CONTRIBUTOR_IMAGE_WIDTH - (CONTRIBUTOR_IMAGE_MARGIN * 2)
    category_width = int((content_width - CONTRIBUTOR_CARD_GAP) / 2)
    category_sections = sections[1:]
    category_rows = int((len(category_sections) + 1) / 2)
    category_grid_height = (
        (category_rows * category_card_height) +
        (max(category_rows - 1, 0) * CONTRIBUTOR_CARD_GAP)
    )
    height = (
        74 + all_card_height +
        (CONTRIBUTOR_CARD_GAP if category_rows else 0) +
        category_grid_height +
        CONTRIBUTOR_IMAGE_MARGIN
    )

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{CONTRIBUTOR_IMAGE_WIDTH}" height="{height}" '
        f'viewBox="0 0 {CONTRIBUTOR_IMAGE_WIDTH} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Contribution Leaderboard</title>',
        '<desc id="desc">Top ThemerrDB contributors across all database categories.</desc>',
        '<style>',
        'text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}',
        '.title{fill:#777;font-size:26px;font-weight:700}',
        '.subtitle{fill:#777;font-size:14px}',
        '.card{fill:#000;fill-opacity:0.035;stroke:#404040;stroke-opacity:0.35}',
        '.section-title{fill:#777;font-size:18px;font-weight:700}',
        '.section-meta{fill:#777;font-size:12px}',
        '.row-line{stroke:#404040;stroke-opacity:0.16}',
        '.rank{fill:#777;font-size:12px;font-weight:700}',
        '.name{fill:#777;font-size:13px;font-weight:700}',
        '.login{fill:#777;font-size:10px}',
        '.count{fill:#777;font-size:14px;font-weight:700}',
        '.placeholder{fill:#777;font-size:12px;font-weight:700}',
        '</style>',
        '<text class="title" x="24" y="34">Contribution Leaderboard</text>',
        '<text class="subtitle" x="24" y="58">Added and edited themes</text>',
    ]

    append_contributor_card(
        parts=parts,
        section=sections[0],
        x=CONTRIBUTOR_IMAGE_MARGIN,
        y=74,
        width=content_width,
        height=all_card_height,
        display_limit=TOP_CONTRIBUTORS_LIMIT,
        card_index=0,
    )

    category_start_y = 74 + all_card_height + CONTRIBUTOR_CARD_GAP
    for index, section in enumerate(category_sections, start=1):
        row = int((index - 1) / 2)
        column = (index - 1) % 2
        card_x = CONTRIBUTOR_IMAGE_MARGIN + (column * (category_width + CONTRIBUTOR_CARD_GAP))
        card_y = category_start_y + (row * (category_card_height + CONTRIBUTOR_CARD_GAP))
        append_contributor_card(
            parts=parts,
            section=section,
            x=card_x,
            y=card_y,
            width=category_width,
            height=category_card_height,
            display_limit=TOP_CONTRIBUTORS_CATEGORY_LIMIT,
            card_index=index,
        )

    parts.append('</svg>')
    return '\n'.join(parts) + '\n'


def render_top_contributor_json(title: str, categories: tuple, contributors: list) -> str:
    """
    Render top contributor data as JSON.

    Parameters
    ----------
    title : str
        Contributor section title.
    categories : tuple
        Category directory names included in the section.
    contributors : list
        Top contributors for the section.

    Returns
    -------
    str
        JSON markup.
    """
    contributor_data = {
        'title': title,
        'categories': list(categories),
        'contributors': [
            {
                'user_id': contributor.user_id,
                'login': contributor.profile.login,
                'name': contributor.profile.name,
                'avatar_url': contributor.profile.avatar_url,
                'contributions': contributor.count,
            }
            for contributor in contributors
        ],
    }

    return f'{json.dumps(obj=contributor_data, indent=2)}\n'


def remove_deprecated_top_contributor_images(database_root: str) -> None:
    """
    Remove category-specific contributor SVGs replaced by the combined leaderboard.

    Parameters
    ----------
    database_root : str
        Root directory containing category database folders.
    """
    for output in DEPRECATED_CONTRIBUTOR_IMAGE_OUTPUTS:
        output_file = os.path.join(database_root, output)
        if os.path.exists(output_file):
            os.remove(output_file)


def build_top_contributor_images(
        database_root: str = 'database',
        profile_resolver: Optional[Callable[[str], ContributorProfile]] = None,
        session: Optional[requests.Session] = None
) -> None:
    """
    Build the top contributor leaderboard SVG and section JSON files.

    Parameters
    ----------
    database_root : str
        Root directory containing category database folders.
    profile_resolver : Optional[Callable[[str], ContributorProfile]]
        Optional profile resolver for tests.
    session : Optional[requests.Session]
        Optional HTTP session for GitHub requests.
    """
    session = session or create_github_session()
    profile_cache = {}
    avatar_cache = {}

    if profile_resolver is None:
        def profile_resolver(user_id: str) -> ContributorProfile:
            return resolve_contributor_profile(user_id=user_id, session=session)

    sections = []
    for section in CONTRIBUTOR_IMAGE_SECTIONS:
        totals = load_contributor_totals(database_root=database_root, categories=section['categories'])
        top_contributors = sorted(
            totals.items(),
            key=lambda item: (-item[1], item[0])
        )[:TOP_CONTRIBUTORS_LIMIT]
        contributors = []

        for user_id, count in top_contributors:
            if user_id not in profile_cache:
                profile_cache[user_id] = profile_resolver(user_id)

            profile = profile_cache[user_id]
            if profile.avatar_url not in avatar_cache:
                avatar_cache[profile.avatar_url] = fetch_avatar_data_uri(profile=profile, session=session)

            contributors.append(TopContributor(
                user_id=user_id,
                count=count,
                profile=profile,
                avatar_data_uri=avatar_cache[profile.avatar_url],
            ))

        sections.append({
            'title': section['title'],
            'categories': section['categories'],
            'contributors': contributors,
        })

        output_file = os.path.join(database_root, section['output'])
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        contributor_json = render_top_contributor_json(
            title=section['title'],
            categories=section['categories'],
            contributors=contributors,
        )
        json_file = os.path.splitext(output_file)[0] + JSON_EXTENSION
        with open(json_file, 'w', encoding='utf-8') as contributor_f:
            contributor_f.write(contributor_json)

    output_file = os.path.join(database_root, TOP_CONTRIBUTORS_FILENAME)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    svg = render_top_contributor_svg(sections=sections)
    with open(output_file, 'w', encoding='utf-8') as contributor_f:
        contributor_f.write(svg)

    remove_deprecated_top_contributor_images(database_root=database_root)


def exception_writer(error: Exception, name: str, end_program: bool = False) -> None:
    print_github_error(f'Error processing {name}: {error}')

    files = ['comment.md', 'exceptions.md']
    for file in files:
        with open(file, "a") as f:
            f.write(f'# :bangbang: **Exception Occurred** :bangbang:\n\n```txt\n{error}\n```\n\n')

    if end_program:
        if not os.environ.get('CI_TEST'):
            # exit without error to allow the rest of GitHub workflow steps to run
            sys.exit(0)  # pragma: no cover
        else:
            raise error


def igdb_authorization(client_id: str, client_secret: str) -> dict:
    """
    Get the igdb authorization.

    Parameters
    ----------
    client_id : str
        Twitch developer client id.
    client_secret : str
        Twitch developer client secret.

    Returns
    -------
    dict
        Dictionary containing access token and expiration.
    """
    auth_headers = {
        'Accept': 'application/json',
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials'
    }

    token_url = 'https://id.twitch.tv/oauth2/token'

    authorization = requests.post(url=token_url, data=auth_headers).json()
    return authorization


wrapper = None


def get_igdb_wrapper() -> IGDBWrapper:
    global wrapper

    if wrapper is None:
        auth = igdb_authorization(
            client_id=os.getenv("TWITCH_CLIENT_ID"),
            client_secret=os.getenv("TWITCH_CLIENT_SECRET")
        )
        wrapper = IGDBWrapper(client_id=os.getenv("TWITCH_CLIENT_ID"), auth_token=auth.get('access_token'))

    return wrapper


def requests_loop(url: str,
                  headers: Optional[dict] = None,
                  method: Callable = requests.get,
                  max_tries: int = 3,
                  allow_statuses: list = [requests.codes.ok],
                  no_retry_statuses: list = []) -> requests.Response:
    count = 1
    response = None
    while count <= max_tries:
        print(f'Processing {url} ... (attempt {count} of {max_tries})')
        try:
            tmdb_limiter.wait()  # Apply TMDB rate limiting
            response = method(url=url, headers=headers)
        except (requests.exceptions.RequestException, Exception) as e:
            print_github_error(f'Error processing {url} - {e}')
        else:
            if response.status_code in allow_statuses:
                return response
            elif response.status_code in no_retry_statuses:
                print_github_error(f'Permanent error for {url} - {response.status_code}, not retrying')
                return response
            else:
                print_github_warning(f'Error processing {url} - {response.status_code}')

        time.sleep(2**count)
        count += 1

    return response


def process_queue() -> None:
    """
    Add items to the queue.
    This is an endless loop to add items to the queue.
    Examples
    --------
    >>> threads = threading.Thread(target=process_queue, daemon=True)
    ...
    """
    while True:
        item = queue.get()
        try:
            queue_handler(item=item)  # process the item from the queue
        except BaseException as e:  # NOSONAR(S5754)
            # intentional broad catch: SystemExit (from sys.exit in exception_writer) is a BaseException, not Exception;
            # catching broadly here ensures queue.task_done() is always called and the thread stays alive
            print_github_error(f'Error processing queue item {item}: {e}')
        finally:
            queue.task_done()  # always mark the item done, even on failure


def queue_handler(item: tuple) -> None:
    data = process_item_id(item_type=item[0], item_id=item[1])
    if not data:
        return
    if item[0] == 'movie':
        databases[item[0]]['all_items'].append({
            'id': data['id'],
            'imdb_id': data.get('imdb_id'),  # imdb_id may not always be present
            'title': data['title']
        })
    else:
        databases[item[0]]['all_items'].append({
            'id': data['id'],
            'title': data['name']  # name is used in all cases except tmdb movies
        })


def start_queue_workers(worker_count: int = 40) -> None:
    """Start worker threads for processing queued database items."""
    for _ in range(worker_count):
        try:
            worker_thread = threading.Thread(target=process_queue)
            worker_thread.daemon = True
            worker_thread.start()
        except RuntimeError as r_e:
            print_github_error(f'RuntimeError encountered: {r_e}')
            break


start_queue_workers()


def _get_igdb_query_filter(item_id: Union[int, str]) -> tuple[str, Union[int, str]]:
    """Return the IGDB field and value used to query an item."""
    try:
        int(item_id)
    except ValueError:
        return 'slug', f'"{item_id}"'

    return 'id', item_id


def _load_igdb_item_data(item_type: str, item_id: Union[int, str]) -> tuple[str, Union[int, str], dict]:
    """Load item metadata from IGDB."""
    database_path = databases[item_type]['path']
    where_type, where = _get_igdb_query_filter(item_id=item_id)

    print(f'Searching igdb for {where_type}: {where}')

    endpoint = databases[item_type]['api_endpoint']
    fields = databases[item_type]['api_fields']

    igdb_limiter.wait()  # Apply IGDB rate limiting
    byte_array = get_igdb_wrapper().api_request(
        endpoint=endpoint,
        query=f'fields {", ".join(fields)}; where {where_type} = ({where}); limit 1; offset 0;'
    )
    json_result = json.loads(byte_array)
    json_data = {}

    try:
        json_data = json_result[0]
        item_id = json_data['id']
    except (KeyError, IndexError) as e:
        exception_writer(
            error=Exception(f'Error getting game id: {e}'),
            name='igdb',
            end_program=True,
        )

    return database_path, item_id, json_data


def _remove_stale_tmdb_file(database_path: str, item_type: str, item_id: Union[int, str]) -> None:
    """Remove a local TMDB file when the upstream item no longer exists."""
    print_github_warning(f'{item_type} id {item_id} not found on TMDB, removing from database')
    stale_file = os.path.join(database_path, f'{item_id}.json')
    if os.path.isfile(stale_file):
        os.remove(stale_file)
        print_github_warning(f'Removed stale database file: {stale_file}')


def _create_tmdb_session() -> requests.Session:
    """Create a TMDB session with credentials kept out of request URLs.

    Returns
    -------
    requests.Session
        Session configured with the TMDB API key as a request parameter.
    """
    session = requests.Session()
    session.params.update({'api_key': os.environ["TMDB_API_KEY_V3"]})
    return session


def _load_tmdb_item_data(item_type: str, item_id: Union[int, str]) -> tuple[str, Union[int, str], dict]:
    """Load item metadata from TMDB."""
    database_path = databases[item_type]['path']
    endpoint = databases[item_type]['api_endpoint']
    url = f'https://api.themoviedb.org/3/{endpoint}/{item_id}'
    response = requests_loop(url=url, method=_create_tmdb_session().get, no_retry_statuses=[404])

    if response.status_code == 404:
        _remove_stale_tmdb_file(database_path=database_path, item_type=item_type, item_id=item_id)
        return database_path, item_id, {}

    if response.status_code != 200:
        exception_writer(
            error=Exception(f'tmdb api returned a non 200 status code of: {response.status_code}'),
            name='tmdb',
            end_program=True,
        )
        return database_path, item_id, {}

    return database_path, item_id, response.json()


def _load_item_data(item_type: str, item_id: Union[int, str]) -> tuple[str, Union[int, str], dict]:
    """Load provider metadata for a database item."""
    if item_type.startswith('game'):
        return _load_igdb_item_data(item_type=item_type, item_id=item_id)

    return _load_tmdb_item_data(item_type=item_type, item_id=item_id)


def _load_existing_item_data(item_file: str) -> dict:
    """Load the existing database item and write duplicate metadata when needed."""
    if not os.path.isfile(item_file):
        return {}

    if args.issue_update:
        with open("duplicate.md", "w") as duplicate_f:
            duplicate_f.write('This item already exists in the database.')

    with open(file=item_file, mode='r') as og_f:
        return json.load(fp=og_f)


def _build_contribution_badge(author: Optional[str] = None, repository: Optional[str] = None) -> str:
    """Build a contribution-count badge for the issue author.

    Parameters
    ----------
    author : str, optional
        GitHub username to search for. Defaults to the issue author login.
    repository : str, optional
        GitHub repository in owner/name format. Defaults to the current repository.

    Returns
    -------
    str
        Markdown badge link, or an empty string when no author is available.
    """
    author = author or os.environ.get('ISSUE_AUTHOR_LOGIN', '')
    if not author:
        return ''

    repository = repository or os.environ.get('GITHUB_REPOSITORY', DEFAULT_GITHUB_REPOSITORY)
    query = f'repo:{repository} is:closed label:{APPROVE_THEME_LABEL} author:{author}'
    encoded_query = quote(query, safe='')
    badge_url = (
        'https://img.shields.io/github/issues-search?'
        f'query={encoded_query}&style={CONTRIBUTION_BADGE_STYLE}&label={CONTRIBUTION_BADGE_LABEL}'
    )
    issues_url = f'https://github.com/{repository}/issues?q={encoded_query}'
    return f'[![{CONTRIBUTION_BADGE_LABEL}]({badge_url})]({issues_url})'


def _write_issue_comment_header() -> None:
    """Write the leading issue comment content.

    Returns
    -------
    None
        The comment file is initialized only when a contribution badge can be built.
    """
    badge = _build_contribution_badge()
    if not badge:
        return

    with open("comment.md", "w", encoding='utf-8') as comment_f:
        comment_f.write(f'{badge}\n\n')


def _html_line_breaks(value: str) -> str:
    """Normalize issue-body line breaks for Markdown table output."""
    return value.replace('\n', '<br>').replace('\r', '<br>')


def _issue_metadata(title: str,
                    issue_title: str,
                    year: Union[int, str] = '',
                    poster: str = '',
                    summary: str = '') -> dict:
    """Create the common issue metadata payload."""
    return {
        'issue_title': issue_title,
        'poster': poster,
        'summary': summary,
        'title': title,
        'year': year,
    }


def _build_game_issue_metadata(json_data: dict) -> dict:
    """Build issue metadata for an IGDB game."""
    title = json_data['name']
    year = json_data['release_dates'][0]['y']
    poster = f"![poster](https:{json_data['cover']['url'].replace('/t_thumb/', '/t_cover_big/')})"
    summary = _html_line_breaks(value=json_data['summary'])
    return _issue_metadata(
        title=title,
        year=year,
        issue_title=f"[GAME]: {title} ({year})",
        poster=poster,
        summary=summary,
    )


def _build_movie_issue_metadata(json_data: dict) -> dict:
    """Build issue metadata for a TMDB movie."""
    title = json_data['title']
    year = json_data['release_date'].split('-')[0]
    poster = f"![poster](https://image.tmdb.org/t/p/w185{json_data['poster_path']})"
    summary = _html_line_breaks(value=json_data['overview'])
    return _issue_metadata(
        title=title,
        year=year,
        issue_title=f"[MOVIE]: {title} ({year})",
        poster=poster,
        summary=summary,
    )


def _build_tmdb_group_issue_metadata(json_data: dict, issue_prefix: str) -> dict:
    """Build issue metadata for a TMDB grouped item."""
    title = json_data['name']
    poster = f"![poster](https://image.tmdb.org/t/p/w185{json_data['poster_path']})"
    summary = _html_line_breaks(value=json_data['overview'])
    return _issue_metadata(
        title=title,
        issue_title=f"[{issue_prefix}]: {title}",
        poster=poster,
        summary=summary,
    )


def _build_tv_show_issue_metadata(json_data: dict) -> dict:
    """Build issue metadata for a TMDB TV show."""
    title = json_data['name']
    year = json_data['first_air_date'].split('-')[0]
    poster = f"![poster](https://image.tmdb.org/t/p/w185{json_data['poster_path']})"
    summary = _html_line_breaks(value=json_data['overview'])
    return _issue_metadata(
        title=title,
        year=year,
        issue_title=f"[TV SHOW]: {title} ({year})",
        poster=poster,
        summary=summary,
    )


def _build_issue_metadata(item_type: str, json_data: dict) -> dict:
    """Build issue metadata for the submitted item type."""
    metadata_builders = {
        'game': _build_game_issue_metadata,
        'game_collection': lambda data: _issue_metadata(
            title=data['name'],
            issue_title=f"[GAME COLLECTION]: {data['name']}",
        ),
        'game_franchise': lambda data: _issue_metadata(
            title=data['name'],
            issue_title=f"[GAME FRANCHISE]: {data['name']}",
        ),
        'movie': _build_movie_issue_metadata,
        'movie_collection': lambda data: _build_tmdb_group_issue_metadata(
            json_data=data,
            issue_prefix='MOVIE COLLECTION',
        ),
        'tv_show': _build_tv_show_issue_metadata,
    }
    return metadata_builders[item_type](json_data)


def _write_issue_metadata_files(item_type: str, json_data: dict) -> None:
    """Write the issue comment and title files for an issue update."""
    metadata = _build_issue_metadata(item_type=item_type, json_data=json_data)
    issue_comment = f"""
| Property | Value |
| --- | --- |
| title | {metadata['title']} |
| year | {metadata['year']} |
| summary | {metadata['summary']} |
| id | {json_data['id']} |
| poster | {metadata['poster']} |
"""
    with open("comment.md", "a") as comment_f:
        comment_f.write(issue_comment)

    with open("title.md", "w") as title_f:
        title_f.write(metadata['issue_title'])


def _update_issue_audit_data(og_data: dict, item_type: str, youtube_url: Optional[str]) -> None:
    """Update contributor and timestamp fields for an issue update."""
    now = int(datetime.now(timezone.utc).timestamp())
    if 'youtube_theme_added' not in og_data:
        og_data['youtube_theme_added'] = now
    og_data['youtube_theme_edited'] = now

    original_submission = 'youtube_theme_added_by' not in og_data
    if original_submission:
        og_data['youtube_theme_added_by'] = os.environ['ISSUE_AUTHOR_USER_ID']
    og_data['youtube_theme_edited_by'] = os.environ['ISSUE_AUTHOR_USER_ID']

    update_contributor_info(original=original_submission, base_dir=databases[item_type]['path'])

    if youtube_url and og_data.get('youtube_theme_url') == youtube_url:
        with open("auto_close.md", "w") as auto_close_f:
            auto_close_f.write('The YouTube url provided is the same as the current one.')


def _write_item_files(database_path: str, item_type: str, og_data: dict) -> None:
    """Write the updated database item files."""
    destination_filenames = [os.path.join(database_path, f'{og_data["id"]}.json')]

    if item_type == 'movie':
        try:
            if og_data["imdb_id"]:
                destination_filenames.append(os.path.join(imdb_path, f'{og_data["imdb_id"]}.json'))
        except KeyError as e:
            print_github_error(f'Error getting imdb_id: {e}')

    for filename in destination_filenames:
        destination_dir = os.path.dirname(filename)
        os.makedirs(name=destination_dir, exist_ok=True)  # create directory if it doesn't exist

        with open(filename, "w") as dest_f:
            json.dump(obj=og_data, indent=4, fp=dest_f, sort_keys=True)


def process_item_id(item_type: str,
                    item_id: Union[int, str],
                    youtube_url: Optional[str] = None) -> dict:
    database_path, item_id, json_data = _load_item_data(item_type=item_type, item_id=item_id)
    if not json_data:
        return {}

    item_file = os.path.join(database_path, f"{item_id}.json")
    og_data = _load_existing_item_data(item_file=item_file)
    print(f'processing {item_type}: id {item_id}')

    try:
        json_data['id']
    except KeyError as e:
        exception_writer(
            error=Exception(f'Error processing game: {e}'),
            name='igdb',
            end_program=True,
        )
    else:
        try:
            args.issue_update
        except NameError:
            pass
        else:
            if args.issue_update:
                _write_issue_metadata_files(item_type=item_type, json_data=json_data)
                _update_issue_audit_data(og_data=og_data, item_type=item_type, youtube_url=youtube_url)

        # update the existing dictionary with new values from json_data
        og_data.update(json_data)
        if youtube_url:
            og_data['youtube_theme_url'] = youtube_url

        # clean old data
        clean_old_data(data=og_data, item_type=item_type)

        _write_item_files(database_path=database_path, item_type=item_type, og_data=og_data)

    return og_data


def clean_old_data(data: dict, item_type: str) -> None:
    # remove old data
    if item_type == 'game':
        try:
            del data['igdb_id']
        except KeyError:
            pass


def update_contributor_info(original: bool, base_dir: str) -> None:
    contributor_file_path = os.path.join(os.path.dirname(base_dir), 'contributors.json')

    os.makedirs(name=os.path.dirname(contributor_file_path), exist_ok=True)  # create directory if it doesn't exist

    if not os.path.exists(contributor_file_path):  # create file if it doesn't exist
        with open(contributor_file_path, 'w+') as contributor_f:
            json.dump(obj={}, indent=4, fp=contributor_f, sort_keys=True)

    with open(contributor_file_path, 'r') as contributor_f:
        contributor_data = json.load(contributor_f)
        try:
            contributor_data[os.environ['ISSUE_AUTHOR_USER_ID']]
        except KeyError:
            contributor_data[os.environ['ISSUE_AUTHOR_USER_ID']] = {
                'items_added': 1 if original else 0,
                'items_edited': 0 if original else 1
            }
        else:
            if original:
                contributor_data[os.environ['ISSUE_AUTHOR_USER_ID']]['items_added'] += 1
            else:
                contributor_data[os.environ['ISSUE_AUTHOR_USER_ID']]['items_edited'] += 1

    with open(contributor_file_path, 'w') as contributor_f:
        json.dump(obj=contributor_data, indent=4, fp=contributor_f, sort_keys=True)


def _load_issue_submission_values(database_url: Optional[str],
                                  youtube_url: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Load missing issue-update values from the submission file."""
    if database_url and youtube_url:
        return database_url, youtube_url

    submission = process_submission()
    if not database_url:
        database_url = submission['database_url'].strip()

    if not youtube_url:
        youtube_url = check_youtube(data=submission)

    return database_url, youtube_url


def _match_database_url(database_url: str) -> tuple[Optional[str], Optional[str], list]:
    """Match a database URL against supported database item types."""
    exceptions = []
    for item_type, regex in DATABASE_URL_PATTERNS.items():
        try:
            item_id = re.search(regex, database_url).group(1)
        except AttributeError as e:
            exceptions.append((item_type, e))
        else:
            return item_type, item_id, exceptions

    return None, None, exceptions


def process_issue_update(database_url: Optional[str] = None, youtube_url: Optional[str] = None) -> Union[str, bool]:
    _write_issue_comment_header()
    database_url, youtube_url = _load_issue_submission_values(database_url=database_url, youtube_url=youtube_url)

    if not youtube_url:
        exception_writer(
            error=Exception('Error processing YouTube url'),
            name='youtube',
        )
        # if invalid YouTube URL, do not proceed with DB processing
        return False

    item_type, item_id, exceptions = _match_database_url(database_url=database_url)
    if item_type:
        process_item_id(item_type=item_type, item_id=item_id, youtube_url=youtube_url)
        return item_type

    # if we get here, we didn't find a match
    for exception in exceptions:
        exception_writer(
            error=exception[1],
            name=exception[0],
        )
    return False


def parse_youtube_duration_seconds(duration: str) -> int:
    """Parse an ISO 8601 YouTube duration string (e.g., 'PT4M13S') into total seconds.

    Uses isodate library for proper ISO 8601 parsing. Returns 0 if format is invalid or empty.
    """
    if not duration or not isinstance(duration, str):
        return 0
    try:
        parsed = isodate.parse_duration(duration)
        return int(parsed.total_seconds())
    except (isodate.ISO8601Error, ValueError, AttributeError):
        return 0


def is_age_restricted(content_details: dict) -> bool:
    """Check if video has age restriction."""
    rating = (content_details or {}).get('contentRating', {})
    return rating.get('ytRating') == 'ytAgeRestricted'


def is_available_in_us(content_details: dict) -> bool:
    """Check if video is available in the USA."""
    rr = (content_details or {}).get('regionRestriction', {})
    if not rr:
        return True  # no restrictions means worldwide
    allowed = rr.get('allowed')
    blocked = rr.get('blocked')
    if allowed is not None:
        # Allowed acts as a whitelist
        return 'US' in allowed
    if blocked is not None:
        # Blocklist indicates exceptions
        return 'US' not in blocked
    # Unknown structure; default to available
    return True


def is_public(status: dict) -> bool:
    """Check if video is public (not private or unlisted)."""
    privacy = (status or {}).get('privacyStatus', '')
    return privacy == 'public'


def is_valid_duration(content_details: dict, min_seconds: int = 20, max_seconds: int = 300) -> tuple[bool, int]:
    """Check if video duration is within acceptable range.

    Returns:
        tuple: (is_valid, total_seconds)
    """
    duration_str = content_details.get('duration', '')
    total_seconds = parse_youtube_duration_seconds(duration_str)
    is_valid = min_seconds <= total_seconds <= max_seconds
    return is_valid, total_seconds


def validate_youtube_requirements(item: dict, min_seconds: int = 20, max_seconds: int = 300) -> list[str]:
    """Validate YouTube video against ThemerrDB requirements.

    Returns a list of error messages. Empty list means all validations passed.
    Requirements:
      1) no age restriction
      2) available in the USA
      3) length between 0:20 and 5:00 (inclusive)
      4) video is public (not private or unlisted)
    """
    errors = []
    content_details = (item or {}).get('contentDetails', {})
    status = (item or {}).get('status', {})

    # 1) Age restriction
    if is_age_restricted(content_details):
        errors.append('Video is age-restricted on YouTube.')

    # 2) Regional availability (USA)
    if not is_available_in_us(content_details):
        errors.append('Video is not available in the USA.')

    # 3) Duration check
    is_valid, total_seconds = is_valid_duration(content_details, min_seconds, max_seconds)
    if not is_valid:
        if total_seconds < min_seconds:
            errors.append(f'Video is too short: {total_seconds}s (minimum {min_seconds}s).')
        elif total_seconds > max_seconds:
            errors.append(f'Video is too long: {total_seconds}s (maximum {max_seconds}s).')

    # 4) Public status
    if not is_public(status):
        privacy = status.get('privacyStatus', 'unknown')
        errors.append(f'Video must be public (current status: {privacy}).')

    return errors


def check_youtube(data: dict) -> Optional[str]:
    url = data['youtube_theme_url'].strip()

    # Strip playlist parameters if present
    # https://www.youtube.com/watch?v=<video_id>&list=<list_id>&index=<1-based-index>
    for symbol in ['&', '?']:
        if f'{symbol}list=' in url:
            url = url.split(f'{symbol}list=')[0]
            break

    # Extract video ID using regex pattern that matches all common YouTube URL formats
    # Matches: youtube.com/watch?v=ID, youtu.be/ID, youtube.com/embed/ID, youtube.com/v/ID
    video_id_match = re.search(
        r'(?:youtube\.com/(?:watch\?v=|embed/|v/)|youtu\.be/)([a-zA-Z0-9_-]{11})',
        url
    )

    if not video_id_match:
        exception_writer(
            error=Exception(f"Error processing YouTube url: Could not extract video ID from URL: {url}"),
            name='youtube',
        )
        return None

    video_id = video_id_match.group(1)

    # Get YouTube API key from environment
    youtube_api_key = os.environ.get('YOUTUBE_API_KEY')
    if not youtube_api_key:
        exception_writer(
            error=Exception("YOUTUBE_API_KEY environment variable is not set"),
            name='youtube',
        )
        return None

    try:
        # Build the YouTube API service
        youtube = build('youtube', 'v3', developerKey=youtube_api_key)

        # Request video details
        request = youtube.videos().list(
            part='snippet,contentDetails,status',
            id=video_id
        )
        response = request.execute()

        if not response.get('items'):
            exception_writer(
                error=Exception(f"Error processing YouTube url: Video not found or unavailable: {video_id}"),
                name='youtube',
            )
            return None

        # Check if we got multiple items (shouldn't happen with a single video ID)
        if len(response['items']) > 1:
            exception_writer(
                error=Exception(
                    "Error processing YouTube url: multiple videos found, but URL doesn't indicate a playlist"),
                name='youtube',
            )
            return None

        # Enforce ThemerrDB validation requirements
        item = response['items'][0]
        validation_errors = validate_youtube_requirements(item=item)
        if validation_errors:
            # Write all validation errors
            for error_msg in validation_errors:
                exception_writer(
                    error=Exception(f"YouTube validation failed: {error_msg}"),
                    name='youtube',
                )

        # Construct the canonical YouTube URL
        webpage_url = f'https://www.youtube.com/watch?v={video_id}'

        return webpage_url

    except HttpError as e:
        exception_writer(
            error=Exception(f"YouTube API error: {e.reason}"),
            name='youtube'
        )
        return None
    except Exception as e:
        exception_writer(
            error=e,
            name='youtube',
        )
        return None


def process_submission() -> dict:
    with open(file='submission.json') as file:
        data = json.load(file)

    required_keys = ['database_url', 'youtube_theme_url']
    error = False
    for key in required_keys:
        if key not in data:
            error = True
            exception_writer(
                error=Exception(f'Key {key} not found in issue body, please undo changes made to the issue headings'),
                name='submission',
            )
        if not data.get(key):
            error = True
            exception_writer(
                error=Exception(f'Key {key} is empty in issue body, please ensure a valid value is provided'),
                name='submission',
            )

    if error:
        exception_writer(
            error=Exception('Error processing issue body, please edit and correct the issue body.'),
            name='submission',
            end_program=True,
        )

    return data


def parse_args(args_list: list) -> argparse.Namespace:
    # setup arguments using argparse
    parser = argparse.ArgumentParser(description="Add theme song to database.")
    parser.add_argument('--daily_update', action='store_true', help='Run in daily update mode.')
    parser.add_argument('--issue_update', action='store_true', help='Run in issue update mode.')
    parser.add_argument('--leaderboard_update', action='store_true', help='Build the contributor leaderboard only.')

    global args
    args = parser.parse_args(args_list)

    return args


def _queue_daily_update_items() -> None:
    """Queue all existing database items for daily refresh."""
    for database in databases.values():
        try:
            all_db_items = os.listdir(path=database['path'])
        except FileNotFoundError:
            continue

        for next_item_file in all_db_items:
            if os.path.isfile(os.path.join(database['path'], next_item_file)):
                next_item_id = next_item_file.rsplit('.', 1)[0]
                queue.put((database['type'], next_item_id))


def _write_chunk_files(db: str, chunks: list) -> None:
    """Write paginated all-item JSON files for a database."""
    for page_number, chunk in enumerate(chunks, start=1):
        chunk_file = os.path.join(os.path.dirname(databases[db]['path']), f'all_page_{page_number}.json')
        with open(file=chunk_file, mode='w') as chunk_f:
            json.dump(obj=chunk, fp=chunk_f)


def _write_pages_file(db: str, all_items: list, chunks: list) -> None:
    """Write the page-count metadata for a database."""
    pages = {
        'count': len(all_items),
        'pages': len(chunks)
    }

    # get imdb count... number of files in imdb_path that start with tt
    if db == 'movie':
        pages['imdb_count'] = len([name for name in os.listdir(imdb_path) if name.startswith('tt')])

    pages_file = os.path.join(os.path.dirname(databases[db]['path']), 'pages.json')
    with open(file=pages_file, mode='w') as pages_f:
        json.dump(obj=pages, fp=pages_f)


def _load_theme_timestamps(db: str, all_items: list) -> list:
    """Load theme-add timestamps for database plot generation."""
    timestamps = []
    for item_ in all_items:
        with open(file=os.path.join(databases[db]['path'], f'{item_["id"]}.json')) as item_f:
            item_data = json.load(item_f)
        timestamps.append(item_data['youtube_theme_added'])

    timestamps.sort()
    return timestamps


def _build_database_plot_values(timestamps: list) -> tuple[list, list]:
    """Build cumulative date and count values for the database size plot."""
    timestamps_human = [datetime.fromtimestamp(x).strftime('%Y-%m-%d') for x in timestamps]
    x_values = []
    y_values = []
    total_count = 0

    for timestamp_human in timestamps_human:
        if timestamp_human not in x_values:
            new_total = timestamps_human.count(timestamp_human) + total_count
            x_values.append(timestamp_human)
            y_values.append(new_total)
            total_count = new_total

    # get the current date in human-readable format
    current_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    if timestamps_human[-1] != current_date:
        x_values.append(current_date)  # add the current date
        y_values.append(y_values[-1])  # add the last value again to indicate no increase

    return x_values, y_values


def _write_database_size_plot(db: str, all_items: list) -> None:
    """Write the database size plot SVG."""
    timestamps = _load_theme_timestamps(db=db, all_items=all_items)
    x_values, y_values = _build_database_plot_values(timestamps=timestamps)
    x_dates = [datetime.strptime(d, '%Y-%m-%d') for d in x_values]

    fig, ax = plt.subplots(figsize=(10, 4))
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    ax.plot(x_dates, y_values, color='#1f77b4')
    ax.set_title(databases[db]['title'], color='#777')
    ax.set_ylabel('Themes', color='#777')
    ax.tick_params(colors='#777')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    fig.autofmt_xdate()
    ax.grid(True, color='#404040')
    for spine in ax.spines.values():
        spine.set_edgecolor('#404040')

    svg_file = os.path.join(
        os.path.dirname(databases[db]['path']),
        f'{databases[db]["title"].lower()}_plot.svg'.replace(' ', '_')
    )
    fig.savefig(svg_file, format='svg', bbox_inches='tight', transparent=True)
    plt.close(fig)


def _write_database_outputs(db: str) -> None:
    """Write daily update JSON and SVG outputs for one database."""
    items_per_page = 10
    all_items = sorted(databases[db]['all_items'], key=itemgetter('title'), reverse=False)
    if not all_items:
        return

    chunks = [all_items[x:x + items_per_page] for x in range(0, len(all_items), items_per_page)]
    _write_chunk_files(db=db, chunks=chunks)
    _write_pages_file(db=db, all_items=all_items, chunks=chunks)
    _write_database_size_plot(db=db, all_items=all_items)


def _run_daily_update() -> None:
    """Run the daily update workflow."""
    # migration tasks go here
    _queue_daily_update_items()

    # finish queue before writing `all` files
    queue.join()

    for db in databases:
        _write_database_outputs(db=db)

    build_top_contributor_images()


def main() -> None:
    if args.issue_update:
        process_issue_update()

    elif args.leaderboard_update:
        build_top_contributor_images()

    elif args.daily_update:
        _run_daily_update()


if __name__ == '__main__':
    args = parse_args(args_list=sys.argv[1:])
    main()
