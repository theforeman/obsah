#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

"""
Obsah is a wrapper around Ansible playbooks. They are exposed as a command line application.
"""

from __future__ import print_function

import argparse
import contextlib
import glob
import json
import os
from collections import namedtuple
from collections.abc import Iterable, Mapping
from functools import total_ordering
from importlib import resources
from typing import Any, Optional

import yaml

from . import data_types
from .constraints import validate_constraints

try:
    import argcomplete
except ImportError:
    argcomplete = None


# Need for PlaybookCLI to set the verbosity
display = None  # pylint: disable=C0103


Variable = namedtuple('Variable', ['name', 'parameter', 'help_text', 'action', 'type', 'choices', 'dest'])


class AppendUniqueAction(argparse.Action):
    """
    Custom argparse action that appends values but ensures uniqueness.
    Similar to action='append', but duplicate values are ignored.
    """
    def __init__(self, option_strings, dest, default=None, **kwargs):
        if default is None:
            default = []
        super().__init__(option_strings, dest, default=default, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        items = getattr(namespace, self.dest, None)
        if items is None:
            items = []
        # Create a new list to avoid modifying the default
        items = list(items)
        # Only append if the value is not already in the list
        if values not in items:
            items.append(values)
        setattr(namespace, self.dest, items)


class RemoveAction(argparse.Action):
    """
    Custom argparse action that removes values from a list.
    Useful when you have a default list and want to selectively remove items.
    """
    def __init__(self, option_strings, dest, default=None, **kwargs):
        if default is None:
            default = []
        super().__init__(option_strings, dest, default=default, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        items = getattr(namespace, self.dest, None)
        if items is None:
            items = []
        else:
            # Create a new list to avoid modifying the default
            items = list(items)
            # Remove the value if it exists in the list
            if values in items:
                items.remove(values)
        setattr(namespace, self.dest, items)


@total_ordering
class Playbook(object):
    """
    An abstraction over an Ansible playbook
    """
    def __init__(self, path, application_config):
        self.path = path
        self.application_config = application_config
        directory = os.path.dirname(self.path)
        self.name = os.path.basename(directory)
        self._metadata_path = os.path.join(directory, self.application_config.metadata_name())
        self._metadata = None

    def _load_metadata_file(self, path):
        """
        Read JSON from a file
        """
        try:
            with open(path) as obsah_metadata:
                data = yaml.safe_load(obsah_metadata)
        except FileNotFoundError:
            data = {}
        return data

    @property
    def metadata(self) -> Mapping[str, Any]:
        """
        Read metadata about the playbook

        The metadata can contain a global help text as well as variables that should be exposed as
        command line parameters.

        This data is lazily loaded and cached.
        """
        if not self._metadata:
            data = self._load_metadata_file(self._metadata_path)
            for include in data.get('include', []):
                include_path = os.path.join(self.application_config.playbooks_path(), include, self.application_config.metadata_name())
                include_data = self._load_metadata_file(include_path)
                data['variables'] = data.get('variables', {}) | include_data.get('variables', {})
                data['constraints'] = data.get('constraints', {}) | include_data.get('constraints', {})

            self._metadata = {
                'help': data.get('help'),
                'variables': sorted(self._parse_parameters(data.get('variables', {}))),
                'constraints': data.get('constraints', {}),
                'reset': data.get('reset', [])
            }

        return self._metadata

    @property
    def takes_target_parameter(self) -> bool:
        """
        Whether this playbook takes a target argument.

        This is determined by a hosts: targets inside the playbook
        """
        with open(self.path) as playbook_file:
            plays = yaml.safe_load(playbook_file.read())

        target_names = set(self.application_config.target_names())

        return any(len(target_names.intersection(play.get('hosts', []))) > 0 for play in plays)

    @property
    def playbook_variables(self) -> Optional[Iterable[Variable]]:
        """
        The playbook variables that should be exposed to the user

        This is extracted from the metadata.
        """
        return self.metadata['variables']

    @property
    def help_text(self) -> Optional[str]:
        """
        The help text if available. This is the first line from the help in the metadata.
        """
        return self.metadata['help'].split('\n', 1)[0] if self.metadata['help'] else None

    @property
    def description(self) -> Optional[str]:
        """
        The full help text if available. This is extracted from the metadata.
        """
        return self.metadata['help']

    def _parse_parameters(self, variables: Mapping[str, Mapping[str, str]]) -> Iterable[Variable]:
        """
        Parse parameters from the metadata.

        Automatically determines the parameter if not specified. This is done by looking at the
        variable and de-namespacing if it's namespaced. Also replaces underscores with dashes. This
        means that for the playbook changelog we expose changelog_message as --message but
        other_option as --other-option.
        """
        namespace = '{}_'.format(self.name)

        for name, options in variables.items():
            try:
                parameter = options['parameter']
            except KeyError:
                parameter = '--{}'.format(name.removeprefix(namespace).replace('_', '-'))

            yield Variable(name, parameter, options.get('help'), options.get('action'), options.get('type'), options.get('choices'), options.get('dest'))

    @property
    def __doc__(self):
        return self.description

    def __str__(self):
        return self.name

    def __repr__(self):
        return "{}('{}')".format(self.__class__.__name__, self.path)

    def __eq__(self, other):
        if hasattr(other, 'path'):
            return self.path == other.path
        return NotImplemented

    def __lt__(self, other):
        if hasattr(other, 'name'):
            return self.name.__lt__(other.name)
        return NotImplemented


class ApplicationConfig(object):
    """
    A class describing the where to find various files
    """

    @staticmethod
    def name() -> str:
        """
        Return the name as shown to the user in the ArgumentParser
        """
        return os.environ.get('OBSAH_NAME', 'obsah')

    @staticmethod
    def target_name() -> str:
        """
        Return the name of the target in the playbook if the playbook takes a parameter.
        """
        return 'packages'

    @classmethod
    def target_names(cls) -> Iterable[str]:
        """
        Return the names of the targets in the playbook if the playbook takes parameters.
        """
        return [cls.target_name()]

    @staticmethod
    def metadata_name() -> str:
        """
        Return the name of the metadata file.
        """
        return 'metadata.obsah.yaml'

    @staticmethod
    def data_path() -> str:
        """
        Return the data path. Houses playbooks and configs.
        """
        path = os.environ.get('OBSAH_DATA')
        if path is None:
            with resources.path(__name__, 'data') as fspath:
                path = fspath.as_posix()

        return path

    @staticmethod
    def inventory_path() -> str:
        """
        Return the inventory path
        """
        return os.environ.get('OBSAH_INVENTORY', os.path.join(os.getcwd(), 'package_manifest.yaml'))

    @classmethod
    def playbooks_path(cls) -> str:
        """
        Return the default playbooks path
        """
        return os.environ.get('OBSAH_PLAYBOOKS', os.path.join(cls.data_path(), 'playbooks'))

    @classmethod
    def ansible_config_path(cls) -> str:
        """
        Return the ansible.cfg path
        """
        return os.environ.get('OBSAH_ANSIBLE_CFG', os.path.join(cls.data_path(), 'ansible.cfg'))

    @classmethod
    def playbooks(cls) -> Iterable[Playbook]:
        """
        Return all playbooks in the playbook path.
        """
        paths = glob.glob(os.path.join(cls.playbooks_path(), '*', '*.yaml'))
        return sorted(Playbook(playbook_path, cls) for playbook_path in paths if
                      os.path.basename(playbook_path) != cls.metadata_name())

    @staticmethod
    def allow_extra_vars() -> bool:
        """
        Whether to allow --extra-vars parameter to be automatically added
        """
        if (value := os.environ.get('OBSAH_ALLOW_EXTRA_VARS')) is not None:
            return value.lower() in ['true', '1']
        return True

    @staticmethod
    def allow_inventory_auth() -> bool:
        """
        Whether to allow host authentication parameters such as password or private key
        """
        if (value := os.environ.get('OBSAH_ALLOW_INVENTORY_AUTH')) is not None:
            return value.lower() in ['true', '1']
        return False

    @staticmethod
    def state_path():
        """
        Where to store the state
        """
        return os.environ.get('OBSAH_STATE', '/var/lib/obsah')

    @staticmethod
    def persist_params():
        """
        Whether or not to persist parameters
        """
        if (value := os.environ.get('OBSAH_PERSIST_PARAMS')) is not None:
            return value.lower() in ['true', '1']
        return False

    @classmethod
    def persist_path(cls):
        """
        Where to persist parameters to
        """
        return os.path.join(cls.state_path(), 'parameters.yaml')


class ObsahArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Register custom actions so they can be used with string names
        self.register('action', 'append_unique', AppendUniqueAction)
        self.register('action', 'remove', RemoveAction)

    def exit(self, status=0, message=None):
        if message is not None and not message.endswith("\n"):
            message += "\n"
        super().exit(status, message)

    def format_usage(self):
        return super().format_help()


def find_targets(inventory_path) -> Optional[Iterable]:
    """
    Find all targets in the given inventory
    """
    targets = None
    if os.path.exists(inventory_path):
        from ansible.inventory.manager import InventoryManager  # pylint: disable=all
        from ansible.parsing.dataloader import DataLoader  # pylint: disable=all
        ansible_loader = DataLoader()
        ansible_inventory = InventoryManager(loader=ansible_loader,
                                             sources=inventory_path)
        targets = list(ansible_inventory.hosts.keys())
        targets.extend(ansible_inventory.groups.keys())
    return targets


def obsah_argument_parser(application_config=ApplicationConfig, playbooks=None, targets=None):
    """
    Construct an argument parser with the given actions and target choices.
    """
    if playbooks is None:
        playbooks = application_config.playbooks()

    if targets is None:
        targets = []

    parser = ObsahArgumentParser(application_config.name())

    parser.obsah_arguments = []
    parser.obsah_dont_persist = {'playbook'}

    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("-v", "--verbose",
                               action="count",
                               dest="verbose",
                               help="verbose output")
    parser.obsah_dont_persist.add('verbose')

    if application_config.allow_inventory_auth():
        parent_parser.add_argument("-k", "--ask-pass",
                                   action="store_true",
                                   dest="ask_pass",
                                   help="ask for connection password")
        parser.obsah_dont_persist.add('ask_pass')

        parent_parser.add_argument("--private-key",
                                   dest="private_key_file",
                                   help="use this file to authenticate the connection")
        parser.obsah_dont_persist.add('private_key_file')

    if application_config.allow_extra_vars():
        advanced = parent_parser.add_argument_group('advanced arguments')
        advanced.add_argument('-e', '--extra-vars',
                              dest="extra_vars",
                              action="append",
                              default=[],
                              help="""set additional variables as key=value or
                              YAML/JSON, if filename prepend with @""")
        parser.obsah_dont_persist.add('extra_vars')

    subparsers = parser.add_subparsers(dest='action', metavar='action',
                                       required=True,
                                       help="""which action to execute""")
    parser.obsah_dont_persist.add('action')

    for playbook in playbooks:
        subparser = subparsers.add_parser(playbook.name, parents=[parent_parser],
                                          help=playbook.help_text,
                                          description=playbook.description,
                                          formatter_class=argparse.RawDescriptionHelpFormatter)
        data_types.register_types(subparser)
        subparser.set_defaults(playbook=playbook)
        if application_config.persist_params():
            with contextlib.suppress(FileNotFoundError):
                with open(application_config.persist_path()) as persist_file:
                    persist_params = yaml.safe_load(persist_file)
                if persist_params:
                    subparser.set_defaults(**persist_params)

        if playbook.takes_target_parameter:
            subparser.add_argument('target',
                                   metavar='target',
                                   choices=targets,
                                   nargs='+',
                                   help="the target to execute the action against")
            parser.obsah_dont_persist.add('target')

        for variable in playbook.playbook_variables:
            argument_args = {'help': variable.help_text, 'action': variable.action,
                             'default': argparse.SUPPRESS}
            if variable.type is not None:
                argument_args['type'] = variable.type
            if variable.choices is not None:
                argument_args['choices'] = variable.choices
            if variable.parameter.startswith('--'):
                argument_args['dest'] = variable.dest or variable.name
            subparser.add_argument(variable.parameter, **argument_args)
            parser.obsah_arguments.append(variable.name)

            if application_config.persist_params() and variable.parameter.startswith('--'):
                reset_param = variable.parameter.replace('--', '--reset-')
                subparser.add_argument(reset_param, help=f'Reset {variable.name}', action='append_const', dest='obsah_reset', const=variable.name)
            elif application_config.persist_params():
                # Don't persist positional arguments
                parser.obsah_dont_persist.add(variable.name)

        parser.obsah_dont_persist.add('obsah_reset')

    if argcomplete:
        argcomplete.autocomplete(parser)

    return parser


def generate_ansible_args(inventory_path, args, obsah_arguments):
    """
    Generate the arguments to run ansible based on the parsed command line arguments
    """
    ansible_args = [args.playbook.path, '--inventory', inventory_path]
    if hasattr(args, 'target'):
        limit = ':'.join(args.target)
        ansible_args.extend(['--limit', limit])
    if args.verbose:
        ansible_args.append("-%s" % str("v" * args.verbose))

    if getattr(args, 'ask_pass', False):
        ansible_args.append('-k')

    if getattr(args, 'private_key_file', None):
        ansible_args.extend(['--private-key', args.private_key_file])

    for extra_var in getattr(args, 'extra_vars', []):
        ansible_args.extend(["-e", extra_var])

    variables = {arg: getattr(args, arg) for arg in obsah_arguments if hasattr(args, arg)}

    # Expose the obsah_state_path variable to roles and playbooks
    variables['obsah_state_path'] = args.playbook.application_config.state_path()

    if variables:
        ansible_args.extend(["-e", json.dumps(variables, sort_keys=True)])

    return ansible_args


def reset_args(application_config: ApplicationConfig, metadata: dict, args: argparse.Namespace):
    with contextlib.suppress(FileNotFoundError):
        with open(application_config.persist_path()) as persist_file:
            persist_params = yaml.safe_load(persist_file)
        if persist_params:
            for (reset_key, reset_values) in metadata['reset']:
                if reset_key in persist_params and persist_params.get(reset_key) != getattr(args, reset_key):
                    for arg in reset_values:
                        if arg in persist_params and persist_params[arg] == getattr(args, arg):
                            delattr(args, arg)
            for reset_arg in (getattr(args, 'obsah_reset', None) or []):
                with contextlib.suppress(AttributeError):
                    delattr(args, reset_arg)
    return args


def main(cliargs=None, application_config=ApplicationConfig):  # pylint: disable=R0914
    """
    Main command
    """
    cfg_path = application_config.ansible_config_path()

    if os.path.exists(cfg_path):
        os.environ["ANSIBLE_CONFIG"] = cfg_path

    # this needs to be global, as otherwise PlaybookCLI fails
    # to set the verbosity correctly
    from ansible.utils.display import Display  # pylint: disable=all
    global display  # pylint: disable=C0103,W0603
    display = Display()

    inventory_path = application_config.inventory_path()

    targets = find_targets(inventory_path)

    parser = obsah_argument_parser(application_config, targets=targets)

    args = parser.parse_args(cliargs)

    if application_config.persist_params():
        args = reset_args(application_config, args.playbook.metadata, args)

    if errors := validate_constraints(args.playbook.metadata, args):
        parser.exit(1, "\n".join(errors))

    if args.playbook.takes_target_parameter and not os.path.exists(inventory_path):
        parser.exit(1, "Could not find your inventory at {}".format(inventory_path))

    if application_config.persist_params():
        persist_dir = os.path.dirname(application_config.persist_path())
        if not os.path.exists(persist_dir):
            os.makedirs(persist_dir, mode=0o770, exist_ok=True)
        with open(application_config.persist_path(), 'w') as persist_file:
            persist_params = dict(vars(args))
            for item in parser.obsah_dont_persist:
                persist_params.pop(item, None)
            yaml.safe_dump(persist_params, persist_file)

    from ansible.cli.playbook import PlaybookCLI  # pylint: disable=all

    ansible_args = generate_ansible_args(inventory_path, args, parser.obsah_arguments)
    ansible_playbook = (["ansible-playbook"] + ansible_args)

    if args.verbose:
        print("ANSIBLE_CONFIG={}".format(os.environ["ANSIBLE_CONFIG"]), ' '.join(ansible_playbook))

    cli = PlaybookCLI(ansible_playbook)
    cli.parse()
    exit_code = cli.run()
    parser.exit(exit_code)


if __name__ == '__main__':
    main()
