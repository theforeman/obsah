"""
Tests for custom argparse actions
"""
import argparse

from obsah import AppendUniqueAction


class TestAppendUniqueAction:
    """Test the AppendUniqueAction custom argparse action"""

    def test_append_unique_removes_duplicates(self):
        """Test that AppendUniqueAction removes duplicate values"""
        parser = argparse.ArgumentParser()
        parser.add_argument('--plugin', action=AppendUniqueAction, default=[])

        args = parser.parse_args(['--plugin', 'foo', '--plugin', 'foo', '--plugin', 'bar'])

        assert args.plugin == ['foo', 'bar']

    def test_append_unique_single_value(self):
        """Test that AppendUniqueAction works with a single value"""
        parser = argparse.ArgumentParser()
        parser.add_argument('--plugin', action=AppendUniqueAction, default=[])

        args = parser.parse_args(['--plugin', 'foo'])

        assert args.plugin == ['foo']

    def test_append_unique_different_values(self):
        """Test that AppendUniqueAction keeps all unique values"""
        parser = argparse.ArgumentParser()
        parser.add_argument('--plugin', action=AppendUniqueAction, default=[])

        args = parser.parse_args(['--plugin', 'foo', '--plugin', 'bar', '--plugin', 'baz'])

        assert args.plugin == ['foo', 'bar', 'baz']
