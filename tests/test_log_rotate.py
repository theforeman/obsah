import os
from unittest import mock
import obsah

def test_log_path_from_env():
    test_log_path = '/custom/path.log'
    with mock.patch.dict(os.environ, {'ANSIBLE_LOG_PATH': test_log_path}):
        assert obsah.ApplicationConfig.log_path() == test_log_path

def test_rotate_log(tmp_path):
    dir = tmp_path / 'logs'
    log_file = dir / 'test.log'

    dir.mkdir()
    log_file.touch()

    assert log_file.exists()

    obsah.rotate_log(str(log_file))
    assert len(os.listdir(dir)) == 1 # only the backup file should exist
    assert not log_file.exists()
