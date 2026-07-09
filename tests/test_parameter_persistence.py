import argparse
import os
import pytest
import yaml
import obsah

from unittest.mock import patch


@pytest.fixture
def state_path(tmp_path):
    return tmp_path


@pytest.fixture
def persist_file(state_path):
    return state_path / 'parameters.yaml'


@pytest.fixture
def persist_application_config(playbooks_path, state_path):
    class PersistApplicationConfig(obsah.ApplicationConfig):
        @staticmethod
        def playbooks_path():
            return playbooks_path.strpath

        @staticmethod
        def target_name():
            return 'packages'

        @staticmethod
        def persist_params():
            return True

        @staticmethod
        def state_path():
            return str(state_path)

        @staticmethod
        def inventory_path():
            return os.path.join(os.path.dirname(__file__), 'fixtures', 'inventory.yaml')

        @staticmethod
        def ansible_config_path():
            return '/nonexistent/ansible.cfg'

        @staticmethod
        def allow_extra_vars():
            return False

        @staticmethod
        def log_path():
            return None

    return PersistApplicationConfig


@pytest.fixture
def write_persist(persist_file):
    def _write(params):
        with open(persist_file, 'w') as f:
            yaml.safe_dump(params, f)
    return _write


class TestResetParam:
    def test_reset_removes_only_specified_param(self, write_persist, persist_file, persist_application_config):
        persisted = {'automatic': 'foo', 'mapped': 'bar'}
        write_persist(persisted)

        parser = obsah.obsah_argument_parser(persist_application_config, targets=['testpackage'])
        args = parser.parse_args(['dummy', 'testpackage', '--reset-automatic'])
        args = obsah.reset_args(persist_application_config, args.playbook.metadata, args)

        assert not hasattr(args, 'automatic')
        assert getattr(args, 'mapped') == 'bar'

        obsah.persist_args(persist_application_config, args, parser.obsah_dont_persist)
        params = yaml.safe_load(persist_file.read_text())
        assert 'automatic' not in params
        assert params['mapped'] == 'bar'

    def test_reset_multiple(self, write_persist, persist_file, persist_application_config):
        persisted = {'automatic': 'a', 'mapped': 'b', 'store_true': True}
        write_persist(persisted)

        parser = obsah.obsah_argument_parser(persist_application_config, targets=['testpackage'])
        args = parser.parse_args(['dummy', 'testpackage', '--reset-automatic', '--reset-explicit'])
        args = obsah.reset_args(persist_application_config, args.playbook.metadata, args)

        assert not hasattr(args, 'automatic')
        assert not hasattr(args, 'mapped')
        assert getattr(args, 'store_true') is True

        obsah.persist_args(persist_application_config, args, parser.obsah_dont_persist)
        params = yaml.safe_load(persist_file.read_text())
        assert 'automatic' not in params
        assert 'mapped' not in params
        assert params['store_true'] is True

    def test_no_persist_file(self, persist_file, persist_application_config):
        assert not os.path.exists(persist_file)

        parser = obsah.obsah_argument_parser(persist_application_config, targets=['testpackage'])
        args = parser.parse_args(['dummy', 'testpackage', '--reset-automatic'])
        args = obsah.reset_args(persist_application_config, args.playbook.metadata, args)

        assert not hasattr(args, 'automatic')


class TestPersistArgs:
    def test_params_persisted(self, persist_file, persist_application_config):
        args = argparse.Namespace(automatic='foo', mapped='bar')
        obsah.persist_args(persist_application_config, args, set())

        assert persist_file.exists()
        params = yaml.safe_load(persist_file.read_text())
        assert params['automatic'] == 'foo'
        assert params['mapped'] == 'bar'

    def test_dont_persist_filtered(self, persist_file, persist_application_config):
        args = argparse.Namespace(automatic='foo', mapped='bar')
        obsah.persist_args(persist_application_config, args, {'mapped'})

        params = yaml.safe_load(persist_file.read_text())
        assert params == {'automatic': 'foo'}

    def test_creates_directory(self, tmp_path, persist_application_config):
        nested = tmp_path / 'subdir' / 'parameters.yaml'

        class NestedConfig(persist_application_config):
            @staticmethod
            def state_path():
                return str(tmp_path / 'subdir')

        args = argparse.Namespace(automatic='foo')
        obsah.persist_args(NestedConfig, args, set())

        assert nested.exists()

    def test_persistence_on_success(self, persist_file, persist_application_config):
        with patch('ansible.utils.display.Display'), \
             patch('ansible.cli.playbook.PlaybookCLI') as mock_cli_class:
            mock_cli_class.return_value.run.return_value = 0

            with pytest.raises(SystemExit) as exc:
                obsah.main(['dummy', '--my-list', 'is-nice', 'testpackage'], persist_application_config)

        assert exc.value.code == 0
        assert persist_file.exists()
        assert yaml.safe_load(persist_file.read_text()) == {'mapped_list': ['is-nice']}

    def test_persistence_on_success_with_side_effect(self, write_persist, persist_file, persist_application_config):
        def migration_sideeffect():
            persisted = {'automatic': 'foo', 'mapped': 'bar'}
            write_persist(persisted)
            return 0

        with patch('ansible.utils.display.Display'), \
             patch('ansible.cli.playbook.PlaybookCLI') as mock_cli_class:
            mock_cli_class.return_value.run.side_effect = migration_sideeffect

            with pytest.raises(SystemExit) as exc:
                obsah.main(['dummy', '--my-list', 'is-nice', 'testpackage'], persist_application_config)

        assert exc.value.code == 0
        assert persist_file.exists()
        assert yaml.safe_load(persist_file.read_text()) == {'mapped_list': ['is-nice'], 'automatic': 'foo', 'mapped': 'bar'}

    def test_no_persistence_on_failure(self, persist_file, persist_application_config):
        with patch('ansible.utils.display.Display'), \
             patch('ansible.cli.playbook.PlaybookCLI') as mock_cli_class:
            mock_cli_class.return_value.run.return_value = 1

            with pytest.raises(SystemExit) as exc:
                obsah.main(['dummy', 'testpackage'], persist_application_config)

        assert exc.value.code == 1
        assert not persist_file.exists()
