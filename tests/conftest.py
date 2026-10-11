from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from helpers import FakeConsole, make_config, make_context

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PROJECT = PROJECT_ROOT / "sample_project"
FIXTURE_REPO = Path(__file__).resolve().parent / "fixtures" / "repo"


@pytest.fixture
def config(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    return make_config(root)


@pytest.fixture
def console():
    return FakeConsole()


@pytest.fixture
def context(config, console):
    return make_context(config, console=console)


@pytest.fixture
def sample_repo(tmp_path: Path):
    destination = tmp_path / "sample_project"
    shutil.copytree(SAMPLE_PROJECT, destination)
    return destination


@pytest.fixture
def fixture_repo(tmp_path: Path):
    destination = tmp_path / "fixture_repo"
    shutil.copytree(FIXTURE_REPO, destination)
    return destination
