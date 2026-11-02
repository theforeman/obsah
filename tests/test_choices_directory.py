import pytest

import obsah


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


class TestChoicesOverride:
    def test_choices_d_overrides_metadata_choices(self, playbooks_path, application_config):
        playbook = make_playbook(playbooks_path, application_config, 'choices_file')
        variables = {v.name: v for v in playbook.metadata['variables']}
        assert 'flavor' in variables
        assert variables['flavor'].choices == ['alpha', 'beta']

    def test_no_override_uses_metadata_choices(self, playbooks_path, application_config):
        playbook = make_playbook(playbooks_path, application_config, 'types')
        choice_var = next(v for v in playbook.metadata['variables'] if v.choices is not None)
        assert choice_var.choices is not None
