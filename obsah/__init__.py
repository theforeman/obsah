#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

"""
Obsah is a wrapper around Ansible playbooks. They are exposed as a command line application.
"""

from __future__ import print_function

import argparse
import glob
import json
import os
from collections import namedtuple
from functools import total_ordering
from importlib import resources

import yaml

from . import data_types
from .constraints import validate_constraints

try:
    import argcomplete
except ImportError:
    argcomplete = None


# Need for PlaybookCLI to set the verbosity
display = None  # pylint: disable=C0103


Variable = namedtuple('Variable', ['name', 'parameter', 'help_text', 'action', 'type', 'choices'])


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
    def metadata(self):
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
            }

        return self._metadata

    @property
    def takes_target_parameter(self):
        """
        Whether this playbook takes a target argument.

        This is determined by a hosts: targets inside the playbook
        """
        with open(self.path) as playbook_file:
            plays = yaml.safe_load(playbook_file.read())

        target_names = set(self.application_config.target_names())

        return any(len(target_names.intersection(play.get('hosts', []))) > 0 for play in plays)

    @property
    def playbook_variables(self):
        """
        The playbook variables that should be exposed to the user

        This is extracted from the metadata.
        """
        return self.metadata['variables']

    @property
    def help_text(self):
        """
        The help text if available. This is the first line from the help in the metadata.
        """
        return self.metadata['help'].split('\n', 1)[0] if self.metadata['help'] else None

    @property
    def description(self):
        """
        The full help text if available. This is extracted from the metadata.
        """
        return self.metadata['help']

    def _parse_parameters(self, variables):
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

            yield Variable(name, parameter, options.get('help'), options.get('action'), options.get('type'), options.get('choices'))

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
    def name():
        """
        Return the name as shown to the user in the ArgumentParser
        """
        return 'obsah'

    @staticmethod
    def target_name():
        """
        Return the name of the target in the playbook if the playbook takes a parameter.
        """
        return 'packages'

    @classmethod
    def target_names(cls):
        """
        Return the names of the targets in the playbook if the playbook takes parameters.
        """
        return [cls.target_name()]

    @staticmethod
    def metadata_name():
        """
        Return the name of the metadata file.
        """
        return 'metadata.obsah.yaml'

    @staticmethod
    def data_path():
        """
        Return the data path. Houses playbooks and configs.
        """
        path = os.environ.get('OBSAH_DATA')
        if path is None:
            with resources.path(__name__, 'data') as fspath:
                path = fspath.as_posix()

        return path

    @staticmethod
    def inventory_path():
        """
        Return the inventory path
        """
        return os.environ.get('OBSAH_INVENTORY', os.path.join(os.getcwd(), 'package_manifest.yaml'))

    @classmethod
    def playbooks_path(cls):
        """
        Return the default playbooks path
        """
        return os.environ.get('OBSAH_PLAYBOOKS', os.path.join(cls.data_path(), 'playbooks'))

    @classmethod
    def ansible_config_path(cls):
        """
        Return the ansible.cfg path
        """
        return os.environ.get('OBSAH_ANSIBLE_CFG', os.path.join(cls.data_path(), 'ansible.cfg'))

    @classmethod
    def playbooks(cls):
        """
        Return all playbooks in the playbook path.
        """
        paths = glob.glob(os.path.join(cls.playbooks_path(), '*', '*.yaml'))
        return sorted(Playbook(playbook_path, cls) for playbook_path in paths if
                      os.path.basename(playbook_path) != cls.metadata_name())

    @staticmethod
    def allow_extra_vars():
        """
        Whether to allow --extra-vars parameter to be automatically added
        """
        return True


class ObsahArgumentParser(argparse.ArgumentParser):
    def exit(self, status=0, message=None):
        if message is not None and not message.endswith("\n"):
            message += "\n"
        super().exit(status, message)

    def format_usage(self):
        return super().format_help()


def find_targets(inventory_path):
    """
    Find all targets in the given inventory
    """
    targets = None
    if os.path.exists(inventory_path):
        from ansible.inventory.manager import InventoryManager # pylint: disable=all
        from ansible.parsing.dataloader import DataLoader # pylint: disable=all
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

    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("-v", "--verbose",
                               action="count",
                               dest="verbose",
                               help="verbose output")

    if application_config.allow_extra_vars():
        advanced = parent_parser.add_argument_group('advanced arguments')
        advanced.add_argument('-e', '--extra-vars',
                              dest="extra_vars",
                              action="append",
                              default=[],
                              help="""set additional variables as key=value or
                              YAML/JSON, if filename prepend with @""")

    subparsers = parser.add_subparsers(dest='action', metavar='action',
                                       required=True,
                                       help="""which action to execute""")

    for playbook in playbooks:
        subparser = subparsers.add_parser(playbook.name, parents=[parent_parser],
                                          help=playbook.help_text,
                                          description=playbook.description,
                                          formatter_class=argparse.RawDescriptionHelpFormatter)
        data_types.register_types(subparser)
        subparser.set_defaults(playbook=playbook)

        if playbook.takes_target_parameter:
            subparser.add_argument('target',
                                   metavar='target',
                                   choices=targets,
                                   nargs='+',
                                   help="the target to execute the action against")

        for variable in playbook.playbook_variables:
            argument_args = {'help': variable.help_text, 'action': variable.action,
                             'default': argparse.SUPPRESS}
            if variable.type is not None:
                argument_args['type'] = variable.type
            if variable.choices is not None:
                argument_args['choices'] = variable.choices
            if variable.parameter.startswith('--'):
                argument_args['dest'] = variable.name
            subparser.add_argument(variable.parameter, **argument_args)
            parser.obsah_arguments.append(variable.name)

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
    for extra_var in getattr(args, 'extra_vars', []):
        ansible_args.extend(["-e", extra_var])

    variables = {arg: getattr(args, arg) for arg in obsah_arguments if hasattr(args, arg)}
    if variables:
        ansible_args.extend(["-e", json.dumps(variables, sort_keys=True)])

    return ansible_args


def main(cliargs=None, application_config=ApplicationConfig):  # pylint: disable=R0914
    """
    Main command
    """
    cfg_path = application_config.ansible_config_path()

    if os.path.exists(cfg_path):
        os.environ["ANSIBLE_CONFIG"] = cfg_path

    # this needs to be global, as otherwise PlaybookCLI fails
    # to set the verbosity correctly
    from ansible.utils.display import Display # pylint: disable=all
    global display  # pylint: disable=C0103,W0603
    display = Display()

    inventory_path = application_config.inventory_path()

    targets = find_targets(inventory_path)

    parser = obsah_argument_parser(application_config, targets=targets)

    args = parser.parse_args(cliargs)

    if errors := validate_constraints(args.playbook.metadata, args):
        parser.exit(1, "\n".join(errors))

    if args.playbook.takes_target_parameter and not os.path.exists(inventory_path):
        parser.exit(1, "Could not find your inventory at {}".format(inventory_path))

    from ansible.cli.playbook import PlaybookCLI # pylint: disable=all

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
