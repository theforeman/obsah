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

    log_dir_contents = list(dir.iterdir())

    assert len(log_dir_contents) == 1 # only the rotated file should exist
    assert log_dir_contents[0].suffix == '.log'
    assert 'test.log' not in log_dir_contents[0].name
    assert 'test.' in log_dir_contents[0].name
    assert not log_file.exists()
