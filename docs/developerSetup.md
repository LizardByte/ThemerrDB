# Developer Setup

This page is for code contributors working on ThemerrDB development, tests, or workflow automation.

Python dependencies are managed with [uv](https://docs.astral.sh/uv/). The dependency declarations live in
`pyproject.toml`, and `uv.lock` is committed so local development and CI use the same resolved package set.

Install uv outside this repository's `.venv` if it is not already available:

```shell
pipx install uv
# or
python -m pip install --user uv
```

If Python 3.14 is not already installed, install it with uv:

```shell
uv python install 3.14
```

Create or update the project `.venv` environment, including test dependencies:

```shell
uv sync --extra dev
```

Run Python commands through uv so they use the synced `.venv` environment:

```shell
uv run python -m pytest tests
```

Node dependencies still use npm:

```shell
npm ci --ignore-scripts
npm test
```

When `pyproject.toml` dependencies change, update the lock file and include it in the same pull request:

```shell
uv lock
```

CI runs `uv sync --locked`, so dependency changes fail until `uv.lock` is current. To check that locally, run:

```shell
uv sync --locked --extra dev
```
