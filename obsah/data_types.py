"""
obsah data types to be used to validate user input
"""

import argparse
import os
import pathlib
import re

REGISTRY: list[type['BaseType']] = []


class BaseType:
    """
    Base type class
    """

    def __init_subclass__(cls, **kwargs):
        if not cls.__name__.endswith('Type'):
            REGISTRY.append(cls)

    @property
    def name(self):
        """
        the name of the type
        this is either the class name of, if set, the `type_name` property
        """
        if hasattr(self, 'type_name'):
            return self.type_name
        return self.__class__.__name__

    def validate(self, string):
        """
        validate user input
        """
        return string


class Boolean(BaseType):
    """
    Boolean type, accepting true/false and 1/0 only
    """
    def validate(self, string):
        if string.lower() in ['true', '1']:
            return True
        if string.lower() in ['false', '0']:
            return False
        raise ValueError


class AbsolutePath(BaseType):
    """
    Path type, accepting anything that looks like an absolute path
    """
    def validate(self, string):
        path = pathlib.PurePath(string)
        if path.is_absolute():
            return path.as_posix()
        raise ValueError


class File(BaseType):
    """
    File type, accepting any existing file
    """
    def validate(self, string):
        if os.path.isfile(string):
            return string
        raise ValueError


class Port(BaseType):
    """
    TCP/UDP Port type, accepting an integer between 0 and 65535
    """
    def validate(self, string):
        if 0 < int(string) < 65535:
            return int(string)
        raise ValueError


class RegexType(BaseType):
    """
    Validates a string against a regular expression
    """
    REGEX = r'.*'

    def validate(self, string):
        if re.match(self.REGEX, string):
            return string
        raise ValueError


class FQDN(RegexType):
    """
    A FQDN
    """
    REGEX = r'\A(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])\Z'


class HTTPUrl(RegexType):
    """
    A HTTP or HTTPS URL
    """
    REGEX = r'(?i:\Ahttps?:\/\/.*\Z)'


def register_types(parser: argparse.ArgumentParser):
    """
    register all known data types as types usable by argparse
    """
    for t in REGISTRY:
        tobj = t()
        parser.register('type', tobj.name, tobj.validate)
