import obsah
import pytest


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


def make_playbook(playbooks_path, application_config, name):
    path = (playbooks_path / name / '{}.yaml'.format(name)).strpath
    return obsah.Playbook(path, application_config)


class TestResolveIncludes:
    def test_single_include(self, playbooks_path, application_config):
        playbook = make_playbook(playbooks_path, application_config, 'include_parent')
        variables = {v.name for v in playbook.metadata['variables']}
        assert 'parent_var' in variables
        assert 'child_var' in variables
        assert 'required_if' in playbook.metadata['constraints']

    def test_recursive_include(self, playbooks_path, application_config):
        playbook = make_playbook(playbooks_path, application_config, 'include_parent')
        variables = {v.name for v in playbook.metadata['variables']}
        assert 'grandchild_var' in variables
        assert 'mutually_exclusive' in playbook.metadata['constraints']

    def test_overlapping_constraints_are_merged(self, playbooks_path, application_config):
        playbook = make_playbook(playbooks_path, application_config, 'include_parent')
        required_if = playbook.metadata['constraints']['required_if']
        assert ['parent_var', 'y', ['child_var']] in required_if
        assert ['child_var', 'x', ['automatic']] in required_if
        assert len(required_if) == 2

    def test_cyclic_includes(self, playbooks_path, application_config):
        playbook = make_playbook(playbooks_path, application_config, 'include_cycle_a')
        variables = {v.name for v in playbook.metadata['variables']}
        assert 'cycle_a_var' in variables
        assert 'cycle_b_var' in variables
