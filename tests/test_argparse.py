"""
Tests for custom argparse actions
"""
import argparse

from obsah import AppendUniqueAction, ObsahArgumentParser, RemoveAction


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


class TestRemoveAction:
    """Test the RemoveAction custom argparse action"""

    def test_remove_single_item(self):
        """Test that RemoveAction removes a single item from the default list"""
        parser = argparse.ArgumentParser()
        parser.add_argument('--exclude', action=RemoveAction, default=['foo', 'bar', 'baz'])

        args = parser.parse_args(['--exclude', 'bar'])

        assert args.exclude == ['foo', 'baz']

    def test_remove_nonexistent_item(self):
        """Test that RemoveAction silently ignores items not in the list"""
        parser = argparse.ArgumentParser()
        parser.add_argument('--exclude', action=RemoveAction, default=['foo', 'bar'])

        args = parser.parse_args(['--exclude', 'nonexistent'])

        assert args.exclude == ['foo', 'bar']


class TestActionStringNames:
    """Test that custom actions can be used via string names"""

    def test_append_unique_string_name(self):
        """Test that 'append_unique' string action works"""
        parser = ObsahArgumentParser()
        parser.add_argument('--plugin', action='append_unique', default=[])

        args = parser.parse_args(['--plugin', 'foo', '--plugin', 'foo', '--plugin', 'bar'])

        assert args.plugin == ['foo', 'bar']

    def test_remove_string_name(self):
        """Test that 'remove' string action works"""
        parser = ObsahArgumentParser()
        parser.add_argument('--exclude', action='remove', default=['foo', 'bar', 'baz'])

        args = parser.parse_args(['--exclude', 'bar'])

        assert args.exclude == ['foo', 'baz']
