import sys

import pytest
import obsah


@pytest.fixture
def playbooks_path(fixture_dir):
    return fixture_dir / 'playbooks'


@pytest.fixture
def application_config(playbooks_path):
    class MockApplicationConfig(obsah.ApplicationConfig):
        @staticmethod
        def playbooks_path():
            return playbooks_path.strpath

        @staticmethod
        def target_name():
            return 'packages'

    return MockApplicationConfig


@pytest.fixture
def application_config_multi_target(playbooks_path):
    class MockApplicationConfig(obsah.ApplicationConfig):
        @staticmethod
        def playbooks_path():
            return playbooks_path.strpath

        @staticmethod
        def target_names():
            return ['packages', 'repos']

    return MockApplicationConfig


@pytest.fixture
def parser(application_config, targets=['testpackage']):
    return obsah.obsah_argument_parser(application_config, targets=targets)


def test_find_no_targets(fixture_dir):
    targets = obsah.find_targets((fixture_dir / 'nope.yaml').strpath)
    assert targets is None


def test_find_targets(fixture_dir):
    targets = obsah.find_targets((fixture_dir / 'inventory.yaml').strpath)
    assert targets
    assert 'testpackage' in targets
    assert 'all' in targets
    assert 'repos' in targets


def test_playbook_constructor(application_config, playbooks_path):
    path = (playbooks_path / 'setup' / 'setup.yaml').strpath
    playbook = obsah.Playbook(path, application_config)
    assert playbook.path == path
    assert playbook.name == 'setup'


@pytest.mark.parametrize('playbook,expected', [
    ('setup', False),
    ('positional', False),
    ('dummy', True),
    ('multiple_plays', True),
    ('repoclosure', True),
])
def test_playbook_takes_target_parameter(application_config, playbooks_path, playbook, expected):
    path = (playbooks_path / playbook / '{}.yaml'.format(playbook)).strpath
    assert obsah.Playbook(path, application_config).takes_target_parameter == expected

@pytest.mark.parametrize('playbook,expected', [
    ('setup', False),
    ('positional', False),
    ('dummy', True),
    ('multiple_plays', True),
    ('repoclosure', True),
])
def test_playbook_takes_multi_target_parameter(application_config_multi_target, playbooks_path, playbook, expected):
    path = (playbooks_path / playbook / '{}.yaml'.format(playbook)).strpath
    assert obsah.Playbook(path, application_config_multi_target).takes_target_parameter == expected


def test_parser_no_arguments(parser):
    with pytest.raises(SystemExit):
        parser.parse_args([])


@pytest.mark.parametrize('cliargs,expected', [
    (['setup'],
     []),
    (['positional', 'tag1'],
     ['-e', '{"tag": "tag1"}']),
    (['dummy', 'testpackage'],
     ['--limit', 'testpackage']),
    (['dummy', 'testpackage', '--verbose'],
     ['--limit', 'testpackage', '-v']),
    (['dummy', 'testpackage', '-vvvv'],
     ['--limit', 'testpackage', '-vvvv']),
    (['dummy', 'testpackage', '-e', 'v1=1', '-e', 'v2=2'],
     ['--limit', 'testpackage', '-e', 'v1=1', '-e', 'v2=2']),
    (['dummy', 'testpackage', '--automatic', 'foo'],
     ['--limit', 'testpackage', '-e', '{"automatic": "foo"}']),
    (['dummy', 'testpackage', '--explicit', 'foo'],
     ['--limit', 'testpackage', '-e', '{"mapped": "foo"}']),
    (['dummy', 'testpackage', '--store-true'],
     ['--limit', 'testpackage', '-e', '{"store_true": true}']),
    (['dummy', 'testpackage', '--store-false'],
     ['--limit', 'testpackage', '-e', '{"store_false": false}']),
    (['dummy', 'testpackage', '--automatic', 'foo', '--explicit', 'bar'],
     ['--limit', 'testpackage', '-e', '{"automatic": "foo", "mapped": "bar"}']),
    (['dummy', 'testpackage', '--my-list', 'foo', '--my-list', 'bar'],
     ['--limit', 'testpackage', '-e', '{"mapped_list": ["foo", "bar"]}']),
])
def test_generate_ansible_args(playbooks_path, parser, cliargs, expected):
    action = cliargs[0]
    base_expected = [(playbooks_path / action / '{}.yaml'.format(action)).strpath,
                     '--inventory', 'inventory.yml']

    args = parser.parse_args(cliargs)
    ansible_args = obsah.generate_ansible_args('inventory.yml', args, parser.obsah_arguments)
    assert ansible_args == base_expected + expected


def test_obsah_argument_parser_help(fixture_dir, parser):
    # https://github.com/python/cpython/commit/7cc773ba3d07d4a2e6cd39063fd1954abd6ae8f1
    if sys.version_info >= (3, 12, 7):
        path = fixture_dir / 'help-3.12.txt'
    else:
        path = fixture_dir / 'help.txt'
    expected = path.read()
    if sys.version_info >= (3, 10, 0):
        expected = expected.replace('optional arguments:', 'options:')
    assert expected == parser.format_help()
