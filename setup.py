"""
Setup file for obsah
"""

# To use a consistent encoding
import codecs
import os

# Always prefer setuptools over distutils
from setuptools import setup, find_packages


def get_long_description():
    """
    Get the long description from the README file
    """
    here = os.path.abspath(os.path.dirname(__file__))

    with codecs.open(os.path.join(here, 'README.md'), encoding='utf-8') as readme:
        return readme.read()


def find_package_data(package, data_dir):
    """
    Find all the package data
    """
    package_data = []
    oldcwd = os.getcwd()
    os.chdir(package)
    for dirpath, _, filenames in os.walk(data_dir):
        files = [os.path.join(dirpath, filename) for filename in filenames]
        package_data.extend(files)
    os.chdir(oldcwd)
    return package_data


setup(
    name='obsah',
    version='1.1.0',
    license='GPL-2.0-only',
    description='packaging wrapper using ansible',
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    url='https://github.com/theforeman/obsah',
    author='The Foreman Project',
    author_email='foreman-dev@googlegroups.com',
    zip_safe=False,
    python_requires=">=3.9, <4",

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
    ],

    keywords='ansible foreman packaging koji brew mock',

    packages=find_packages(exclude=['contrib', 'docs']),

    install_requires=[
        'ansible-core',
    ],

    extras_require={
        'argcomplete': ['argcomplete'],
    },

    package_data={
        'obsah': find_package_data('obsah', 'data'),
    },

    entry_points={
        'console_scripts': [
            'obsah=obsah:main',
        ],
    },

    project_urls={
        "Documentation": "https://obsah.readthedocs.io/en/latest/",
        "Source": "https://github.com/theforeman/obsah",
    },
)
