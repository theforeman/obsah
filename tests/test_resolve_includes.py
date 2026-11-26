import obsah
import pytest
import yaml


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
    def test_external_metadata_uses_its_own_root_and_merges_resets(self, tmp_path):
        local = tmp_path / 'development/playbooks'
        external = tmp_path / 'production/playbooks'
        documents = {
            local / 'wrapper/metadata.obsah.yaml': {
                'include': ['common', {'path': '../../../production/playbooks/deploy/metadata.obsah.yaml',
                                       'root': '../../../production/playbooks'}],
            },
            local / 'common/metadata.obsah.yaml': {'variables': {'local_option': {'help': 'Local'}}},
            external / 'deploy/metadata.obsah.yaml': {'include': ['common']},
            external / 'common/metadata.obsah.yaml': {
                'variables': {'external_option': {'help': 'External'}},
                'constraints': {'required_one_of': [['external_option']]},
                'reset': [['external_option', ['dependent_option']]],
            },
        }
        for path, document in documents.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(yaml.safe_dump(document))

        class Config(obsah.ApplicationConfig):
            @staticmethod
            def playbooks_path():
                return str(local)

        playbook = obsah.Playbook(str(local / 'wrapper/wrapper.yaml'), Config)
        assert {variable.name for variable in playbook.metadata['variables']} == {'local_option', 'external_option'}
        assert playbook.metadata['constraints']['required_one_of'] == [['external_option']]
        assert playbook.metadata['reset'] == [['external_option', ['dependent_option']]]

    def test_explicit_missing_metadata_fails(self, tmp_path, application_config):
        path = tmp_path / 'wrapper'
        path.mkdir()
        (path / 'metadata.obsah.yaml').write_text('include:\n  - path: missing.yaml\n    root: .\n')
        playbook = obsah.Playbook(str(path / 'wrapper.yaml'), application_config)
        with pytest.raises(FileNotFoundError, match='Included metadata file does not exist'):
            _ = playbook.metadata

    def test_invalid_include_mapping_fails(self, tmp_path, application_config):
        (tmp_path / 'metadata.obsah.yaml').write_text('include:\n  - path: missing.yaml\n')
        playbook = obsah.Playbook(str(tmp_path / 'wrapper.yaml'), application_config)
        with pytest.raises(ValueError, match="containing 'path' and 'root'"):
            _ = playbook.metadata

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

    def test_overlapping_variables_are_merged(self, playbooks_path, application_config):
        playbook = make_playbook(playbooks_path, application_config, 'include_parent')
        shared_var = next(v for v in playbook.metadata['variables'] if v.name == 'shared_var')
        assert shared_var.help_text == 'Variable from child'
        assert shared_var.persist is False

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
