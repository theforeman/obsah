# obsah - easily build CLI applications using ansible playbooks

[![Documentation Status](https://readthedocs.org/projects/obsah/badge/?version=latest)](https://obsah.readthedocs.io/en/latest/)

`obsah` is an Ansible wrapper that will help you to build CLI applications by writing Ansible playbooks.

## necessary tools

- `python` 3
- `ansible`


## Release

First, install dependencies, either from Fedora:

```
$ sudo dnf install bumpversion
```

Or PyPI:

```
$ pip install bump2version
```

Now bump the version based on the type of update (e.g. major, minor, patch):

```
bump2version <type>
```

Finally, open a pull request with release.
