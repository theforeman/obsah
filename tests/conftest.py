import py.path
import pytest


@pytest.fixture
def fixture_dir():
    return py.path.local(__file__).realpath() / '..' / 'fixtures'


@pytest.fixture
def playbooks_path(fixture_dir):
    return fixture_dir / 'playbooks'
