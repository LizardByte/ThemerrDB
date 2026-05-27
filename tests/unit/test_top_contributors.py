# standard imports
import json

# lib imports
import requests

# local imports
from src import updater


def write_contributors(database_root, category, contributor_data):
    category_dir = database_root / category
    category_dir.mkdir(parents=True, exist_ok=True)
    (category_dir / 'contributors.json').write_text(json.dumps(contributor_data), encoding='utf-8')


def test_load_contributor_totals_aggregates_categories(tmp_path):
    write_contributors(tmp_path, 'movies', {
        '100': {
            'items_added': 2,
            'items_edited': 3,
        },
        '200': {
            'items_added': 4,
            'items_edited': 0,
        },
    })
    write_contributors(tmp_path, 'tv_shows', {
        '100': {
            'items_added': 1,
            'items_edited': 0,
        },
        '300': {
            'items_added': 'bad',
            'items_edited': 1,
        },
    })

    totals = updater.load_contributor_totals(
        database_root=str(tmp_path),
        categories=('movies', 'tv_shows', 'games'),
    )

    assert totals == {
        '100': 6,
        '200': 4,
    }


def test_contributor_totals_ignore_invalid_inputs(tmp_path, capsys):
    invalid_dir = tmp_path / 'invalid'
    invalid_dir.mkdir()
    (invalid_dir / 'contributors.json').write_text('{', encoding='utf-8')

    list_dir = tmp_path / 'list'
    list_dir.mkdir()
    (list_dir / 'contributors.json').write_text('[]', encoding='utf-8')

    totals = updater.load_contributor_totals(
        database_root=str(tmp_path),
        categories=('invalid', 'list'),
    )

    captured = capsys.readouterr()
    assert totals == {}
    assert 'Unable to read contributor data' in captured.out
    assert updater.get_contributor_total([]) == 0
    assert updater.get_contributor_total({'items_added': -4, 'items_edited': 1}) == 0


def test_build_top_contributor_images_writes_all_readme_assets(tmp_path):
    database_root = tmp_path / 'database'
    write_contributors(database_root, 'movies', {
        '100': {
            'items_added': 2,
            'items_edited': 1,
        },
        '200': {
            'items_added': 5,
            'items_edited': 0,
        },
        '400': {
            'items_added': 3,
            'items_edited': 0,
        },
        '500': {
            'items_added': 2,
            'items_edited': 0,
        },
        '600': {
            'items_added': 1,
            'items_edited': 0,
        },
        '700': {
            'items_added': 1,
            'items_edited': 0,
        },
    })
    write_contributors(database_root, 'tv_shows', {
        '100': {
            'items_added': 1,
            'items_edited': 0,
        },
    })
    write_contributors(database_root, 'game_collections', {
        '300': {
            'items_added': 4,
            'items_edited': 0,
        },
    })
    write_contributors(database_root, 'game_franchises', {
        '300': {
            'items_added': 0,
            'items_edited': 2,
        },
    })

    def profile_resolver(user_id):
        return updater.ContributorProfile(
            user_id=user_id,
            login=f'user-{user_id}',
            name=f'User {user_id}',
            avatar_url='',
        )

    updater.build_top_contributor_images(
        database_root=str(database_root),
        profile_resolver=profile_resolver,
    )

    all_svg = (database_root / 'top_contributors.svg').read_text(encoding='utf-8')
    assert 'Top Contributors - All' in all_svg
    assert 'User 300' in all_svg
    assert '6' in all_svg
    assert 'User 200' in all_svg
    assert '5' in all_svg
    assert 'User 100' in all_svg
    assert '4' in all_svg
    assert 'User 500' in all_svg
    assert 'User 700' not in all_svg

    all_json = json.loads((database_root / 'top_contributors.json').read_text(encoding='utf-8'))
    assert all_json == {
        'title': 'All',
        'categories': [
            'movies',
            'tv_shows',
            'games',
            'movie_collections',
            'game_collections',
            'game_franchises',
        ],
        'contributors': [
            {
                'user_id': '300',
                'login': 'user-300',
                'name': 'User 300',
                'avatar_url': '',
                'contributions': 6,
            },
            {
                'user_id': '200',
                'login': 'user-200',
                'name': 'User 200',
                'avatar_url': '',
                'contributions': 5,
            },
            {
                'user_id': '100',
                'login': 'user-100',
                'name': 'User 100',
                'avatar_url': '',
                'contributions': 4,
            },
            {
                'user_id': '400',
                'login': 'user-400',
                'name': 'User 400',
                'avatar_url': '',
                'contributions': 3,
            },
            {
                'user_id': '500',
                'login': 'user-500',
                'name': 'User 500',
                'avatar_url': '',
                'contributions': 2,
            },
        ],
    }

    assert (database_root / 'movies' / 'top_contributors.svg').is_file()
    assert (database_root / 'tv_shows' / 'top_contributors.svg').is_file()
    assert (database_root / 'movie_collections' / 'top_contributors.svg').is_file()
    assert (database_root / 'games' / 'top_contributors.svg').is_file()
    assert (database_root / 'game_collections' / 'top_contributors.svg').is_file()
    assert (database_root / 'game_franchises' / 'top_contributors.svg').is_file()
    assert (database_root / 'movies' / 'top_contributors.json').is_file()
    assert (database_root / 'tv_shows' / 'top_contributors.json').is_file()
    assert (database_root / 'movie_collections' / 'top_contributors.json').is_file()
    assert (database_root / 'games' / 'top_contributors.json').is_file()
    assert (database_root / 'game_collections' / 'top_contributors.json').is_file()
    assert (database_root / 'game_franchises' / 'top_contributors.json').is_file()

    games_svg = (database_root / 'games' / 'top_contributors.svg').read_text(encoding='utf-8')
    assert 'No contributors yet' in games_svg
    games_json = json.loads((database_root / 'games' / 'top_contributors.json').read_text(encoding='utf-8'))
    assert games_json['contributors'] == []

    game_collections_svg = (database_root / 'game_collections' / 'top_contributors.svg').read_text(encoding='utf-8')
    assert 'Top Contributors - Game Collections' in game_collections_svg
    assert 'User 300' in game_collections_svg
    assert '4' in game_collections_svg

    game_franchises_svg = (database_root / 'game_franchises' / 'top_contributors.svg').read_text(encoding='utf-8')
    assert 'Top Contributors - Game Franchises' in game_franchises_svg
    assert 'User 300' in game_franchises_svg
    assert '2' in game_franchises_svg


def test_build_top_contributor_images_uses_default_profile_resolver(tmp_path, monkeypatch):
    database_root = tmp_path / 'database'
    write_contributors(database_root, 'movies', {
        '100': {
            'items_added': 1,
            'items_edited': 0,
        },
    })

    def resolve_profile(user_id, session):
        assert user_id == '100'
        assert session == 'session'
        return updater.ContributorProfile(
            user_id=user_id,
            login='resolved-user',
            name='Resolved User',
            avatar_url='',
        )

    monkeypatch.setattr(updater, 'create_github_session', lambda: 'session')
    monkeypatch.setattr(updater, 'resolve_contributor_profile', resolve_profile)

    updater.build_top_contributor_images(database_root=str(database_root))

    movies_svg = (database_root / 'movies' / updater.TOP_CONTRIBUTORS_FILENAME).read_text(encoding='utf-8')
    assert 'Resolved User' in movies_svg


def test_main_daily_update_builds_top_contributor_images(tmp_path, monkeypatch):
    built = []
    args = type('Args', (), {
        'issue_update': False,
        'daily_update': True,
    })()

    monkeypatch.setattr(updater, 'args', args)
    monkeypatch.setattr(updater, 'databases', {
        'movie': {
            'all_items': [],
            'path': str(tmp_path / 'missing'),
            'type': 'movie',
        },
    })
    monkeypatch.setattr(updater, 'build_top_contributor_images', lambda: built.append(True))

    updater.main()

    assert built == [True]


def test_create_github_session_only_uses_github_token(monkeypatch):
    monkeypatch.setenv('GITHUB_TOKEN', 'github-token')
    monkeypatch.setenv('GH_TOKEN', 'gh-token')
    monkeypatch.setenv('GH_BOT_TOKEN', 'bot-token')

    session = updater.create_github_session()

    assert session.headers['Authorization'] == 'Bearer github-token'
    assert 'X-GitHub-Api-Version' not in session.headers

    monkeypatch.delenv('GITHUB_TOKEN')
    session = updater.create_github_session()

    assert 'Authorization' not in session.headers
    assert 'X-GitHub-Api-Version' not in session.headers


def test_resolve_contributor_profile_uses_ci_test_fallback(monkeypatch):
    monkeypatch.setenv('CI_TEST', 'True')

    profile = updater.resolve_contributor_profile(user_id='1', session=None)

    assert profile.login == 'user-1'
    assert profile.name == 'User 1'
    assert profile.avatar_url == ''


def test_resolve_contributor_profile_uses_login_for_avatar_url(monkeypatch):
    monkeypatch.delenv('CI_TEST', raising=False)

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                'login': 'octocat',
                'name': 'The Octocat',
            }

    class Session:
        def get(self, url, timeout):
            assert url == 'https://api.github.com/user/1'
            assert timeout == 15
            return Response()

    profile = updater.resolve_contributor_profile(user_id='1', session=Session())

    assert profile.login == 'octocat'
    assert profile.name == 'The Octocat'
    assert profile.avatar_url == f'https://github.com/octocat.png?size={updater.AVATAR_SIZE}'


def test_resolve_contributor_profile_uses_fallback_for_errors(monkeypatch, capsys):
    monkeypatch.delenv('CI_TEST', raising=False)

    class Session:
        def get(self, url, timeout):
            raise requests.RequestException('lookup failed')

    profile = updater.resolve_contributor_profile(user_id='1', session=Session())

    captured = capsys.readouterr()
    assert 'Unable to resolve GitHub user 1' in captured.out
    assert profile.login == 'user-1'
    assert profile.name == 'User 1'
    assert profile.avatar_url == f'https://avatars.githubusercontent.com/u/1?size={updater.AVATAR_SIZE}'


def test_resolve_contributor_profile_uses_fallback_without_login(monkeypatch):
    monkeypatch.delenv('CI_TEST', raising=False)

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {}

    class Session:
        def get(self, url, timeout):
            return Response()

    profile = updater.resolve_contributor_profile(user_id='1', session=Session())

    assert profile.login == 'user-1'
    assert profile.name == 'User 1'
    assert profile.avatar_url == f'https://avatars.githubusercontent.com/u/1?size={updater.AVATAR_SIZE}'


def test_fetch_avatar_data_uri_handles_empty_url_and_request_errors():
    profile = updater.ContributorProfile(
        user_id='1',
        login='octocat',
        name='The Octocat',
        avatar_url='',
    )
    assert updater.fetch_avatar_data_uri(profile=profile, session=None) is None

    class Session:
        def get(self, url, headers, timeout):
            raise requests.RequestException('avatar failed')

    profile.avatar_url = 'https://github.com/octocat.png?size=96'
    assert updater.fetch_avatar_data_uri(profile=profile, session=Session()) is None


def test_fetch_avatar_data_uri_embeds_avatar_with_content_type_fallback():
    class Response:
        content = b'avatar'
        headers = {
            'Content-Type': 'text/plain; charset=utf-8',
        }

        def raise_for_status(self):
            return None

    class Session:
        def get(self, url, headers, timeout):
            assert url == 'https://github.com/octocat.png?size=96'
            assert headers == {'Accept': updater.PNG_CONTENT_TYPE}
            assert timeout == 15
            return Response()

    profile = updater.ContributorProfile(
        user_id='1',
        login='octocat',
        name='The Octocat',
        avatar_url='https://github.com/octocat.png?size=96',
    )

    avatar_data_uri = updater.fetch_avatar_data_uri(profile=profile, session=Session())

    assert avatar_data_uri == 'data:image/png;base64,YXZhdGFy'


def test_render_top_contributor_svg_embeds_avatar_and_truncates_text():
    contributor = updater.TopContributor(
        user_id='1',
        count=1,
        profile=updater.ContributorProfile(
            user_id='1',
            login='octocat',
            name='The Octocat With A Name That Is Definitely Too Long For The SVG',
            avatar_url='https://github.com/octocat.png?size=96',
        ),
        avatar_data_uri='data:image/png;base64,YXZhdGFy',
    )

    svg = updater.render_top_contributor_svg(title='Movies & TV', contributors=[contributor])

    assert 'Top Contributors - Movies &amp; TV' in svg
    assert 'The Octocat With A Name That Is Definit...' in svg
    assert '<image href="data:image/png;base64,YXZhdGFy"' in svg
    assert '1</text>' in svg
    assert 'contribution</text>' in svg

    contributor_json = json.loads(updater.render_top_contributor_json(
        title='Movies & TV',
        categories=('movies', 'tv_shows'),
        contributors=[contributor],
    ))

    assert contributor_json == {
        'title': 'Movies & TV',
        'categories': ['movies', 'tv_shows'],
        'contributors': [
            {
                'user_id': '1',
                'login': 'octocat',
                'name': 'The Octocat With A Name That Is Definitely Too Long For The SVG',
                'avatar_url': 'https://github.com/octocat.png?size=96',
                'contributions': 1,
            },
        ],
    }
