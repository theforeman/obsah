import argparse
import os
import pytest
import yaml
import obsah


@pytest.fixture
def persist_file(tmp_path):
    return tmp_path / 'parameters.yaml'


@pytest.fixture
def persist_application_config(playbooks_path, persist_file):
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
        def persist_path():
            return str(persist_file)

        @staticmethod
        def state_path():
            return str(persist_file.parent)

        @staticmethod
        def inventory_path():
            return os.path.join(os.path.dirname(__file__), 'fixtures', 'inventory.yaml')

        @staticmethod
        def ansible_config_path():
            return '/nonexistent/ansible.cfg'

        @staticmethod
        def allow_extra_vars():
            return False

    return PersistApplicationConfig


@pytest.fixture
def write_persist(persist_file):
    def _write(params):
        with open(persist_file, 'w') as f:
            yaml.safe_dump(params, f)
    return _write


class TestResetParam:
    def test_reset_removes_only_specified_param(self, write_persist, persist_application_config):
        persisted = {'automatic': 'foo', 'mapped': 'bar'}
        write_persist(persisted)

        parser = obsah.obsah_argument_parser(persist_application_config, targets=['testpackage'])
        args = parser.parse_args(['dummy', 'testpackage', '--reset-automatic'])
        args = obsah.reset_args(persist_application_config, args.playbook.metadata, args)

        assert not hasattr(args, 'automatic')
        assert getattr(args, 'mapped') == 'bar'

    def test_reset_multiple(self, write_persist, persist_application_config):
        persisted = {'automatic': 'a', 'mapped': 'b', 'store_true': True}
        write_persist(persisted)

        parser = obsah.obsah_argument_parser(persist_application_config, targets=['testpackage'])
        args = parser.parse_args(['dummy', 'testpackage', '--reset-automatic', '--reset-explicit'])
        args = obsah.reset_args(persist_application_config, args.playbook.metadata, args)

        assert not hasattr(args, 'automatic')
        assert not hasattr(args, 'mapped')
        assert getattr(args, 'store_true') is True

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
            def persist_path():
                return str(nested)

        args = argparse.Namespace(automatic='foo')
        obsah.persist_args(NestedConfig, args, set())

        assert nested.exists()

