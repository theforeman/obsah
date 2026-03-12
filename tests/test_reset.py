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

    return PersistApplicationConfig



def write_persist_file(persist_file, params):
    with open(persist_file, 'w') as f:
        yaml.safe_dump(params, f)


class TestResetParam:
    def test_reset_removes_only_specified_param(self, persist_file, persist_application_config):
        persisted = {'automatic': 'foo', 'mapped': 'bar'}
        write_persist_file(persist_file, persisted)

        parser = obsah.obsah_argument_parser(persist_application_config, targets=['testpackage'])
        args = parser.parse_args(['dummy', 'testpackage', '--reset-automatic'])
        args = obsah.reset_args(persist_application_config, args.playbook.metadata, args)

        assert not hasattr(args, 'automatic')
        assert getattr(args, 'mapped') == 'bar'

    def test_reset_multiple(self, persist_file, persist_application_config):
        persisted = {'automatic': 'a', 'mapped': 'b', 'store_true': True}
        write_persist_file(persist_file, persisted)

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

