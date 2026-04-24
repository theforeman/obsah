Developing Obsah
===============

Obsah is written with support for Python 3.9 or higher. To provide the command line we rely on the Python built in `argparse`_ and `Ansible`_. For testing we use `Pytest`_ but this is wrapped up with `Tox`_ to test multiple environments.

.. _argparse: https://docs.python.org/3/library/argparse.html
.. _Ansible: https://www.ansible.com/
.. _Pytest: https://pytest.org/
.. _Tox: https://tox.readthedocs.org/

Writing actions
---------------

All Ansible is contained in `obsah/data`. There we have `playbooks`, `roles` and `modules`.

A `playbook` with `metadata` is considered an action and exposed to the user as such.

Writing playbooks
~~~~~~~~~~~~~~~~~

We have a slightly non-standard playbooks layout. Every playbook is contained in its own directory and named after the directory, like `release/release.yaml` for the `release` action. It can also contain a `metadata.obsah.yaml`. While playbooks are pure Ansible, the metadata is the data Obsah needs to extract to build a CLI.

Obsah uses the inventory to operate on. The inventory is typically composed of packages, but there are some special hosts:

* localhost
* packages

As with regular Ansible, `localhost` is used to operate on the local machine. This is typically used to setup or work on environments.

Packages is the entire set of all packages. These are exposed on the command line to users so they can operate on a limited set of packages.

Within Ansible playbooks you can choose on which inventory items to operate through `hosts`. We set the additional limitation that hosts must always be a list. Our setup playbook is an example of a local connection:

.. literalinclude:: ../../obsah/data/playbooks/setup/setup.yaml
  :language: yaml
  :caption: setup.yaml
  :emphasize-lines: 2,3

When dealing with packages we typically include the `package_variables` role to set various variables:

.. literalinclude:: ../../obsah/data/playbooks/changelog/changelog.yaml
  :language: yaml
  :caption: changelog.yaml
  :emphasize-lines: 6,7

Exposing playbooks using metadata
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default Obsah exposes a playbook based on its name. It can also automatically detect whether it accepts a packages parameter. To provide a better experience we introduce metadata via `metadata.obsah.yaml` in the same directory.

An example:

.. literalinclude:: ../../tests/fixtures/playbooks/dummy/metadata.obsah.yaml
  :language: yaml
  :caption: playbooks/dummy/metadata.obsah.yaml

The help text is a top level key. The first line is used in ``obsah --help``:

.. code-block:: none

   usage: obsah [-h] action ...

   positional arguments:
     action          which action to execute
       dummy         Short description

   optional arguments:
     -h, --help      show this help message and exit


When we execute ``obsah dummy --help`` we see more show up:

.. code-block:: none

   usage: obsah dummy [-h] [-v] [-e EXTRA_VARS] [--automatic AUTOMATIC]
                      [--explicit MAPPED] [--my-list MAPPED_LIST] [--store-false]
                      [--store-list STORE_LIST] [--store-true]
                      target [target ...]

   Short description

   Full text on multiple lines
   with an explicit newline

   positional arguments:
     target                the target to execute the action against

   options:
     -h, --help            show this help message and exit
     -v, --verbose         verbose output
     --automatic AUTOMATIC
                           Automatically determined parameter
     --explicit MAPPED     Explicitly specified parameter
     --my-list MAPPED_LIST
                           Repeatable action
     --store-false         Action that stores false if passed
     --store-list STORE_LIST
                           Repeatable action
     --store-true          Action that stores true if passed

   advanced arguments:
     -e, --extra-vars EXTRA_VARS
                           set additional variables as key=value or YAML/JSON, if
                           filename prepend with @


Help
^^^^

Help is a string at the top level in the metadata with some additional newline handling.

Multiple lines are joined but a single empty line indicates a newline. A double empty line indicates a new paragraph.

The first line is taken as a short description while the full text is included in the commands ``--help`` as can be seen above.

Variables
^^^^^^^^^

Variables is a mapping at the top level in the metadata.

For every variable the key is the variable in Ansible. It also needs a ``help`` (`argparse help`_). The most minimal variant for a ``changelog`` playbook:

.. _argparse help: https://docs.python.org/3/library/argparse.html#help

.. code-block:: yaml

    variables:
      changelog:
        help: The changelog message

This results into the following ``obsah changelog --help`` output:

.. code-block:: none
  :emphasize-lines: 13,14

   usage: obsah changelog [-h] [-v] [-e EXTRA_VARS]
                         [--changelog CHANGELOG]
                         package [package ...]

   The changelog command writes a RPM changelog entry for the current version and release.

   positional arguments:
     package               the package to build

   optional arguments:
     -h, --help            show this help message and exit
     -v, --verbose         verbose output
     --changelog CHANGELOG
                           The text for the changelog entry

Now you might notice that this results in a ``obsah changelog --changelog "my message"`` which feels a bit redundant. That's why there's mapping built in.


.. code-block:: yaml
  :emphasize-lines: 4

    variables:
      changelog:
        help: The changelog message
        parameter: --message

This results into the following help:

.. code-block:: none
  :emphasize-lines: 13

    usage: obsah changelog [-h] [-v] [-e EXTRA_VARS]
                          [--message CHANGELOG]
                          package [package ...]

    The changelog command writes a RPM changelog entry for the current version and release.

    positional arguments:
      package               the package to build

    optional arguments:
      -h, --help            show this help message and exit
      -v, --verbose         verbose output
      --message CHANGELOG   The text for the changelog entry

There is also support for automatic removal of namespaces.

.. code-block:: yaml
  :emphasize-lines: 2

    variables:
      changelog_author:
        help: The author of the changelog entry

When we run this within the changelog playbook, this is translated into:

.. code-block:: none

  --author CHANGELOG_AUTHOR
                        The author of the changelog entry

Sometimes you just want to store a boolean. For this we expose the `argparse action`_:

.. _argparse action: https://docs.python.org/3/library/argparse.html#action

.. code-block:: yaml
  :emphasize-lines: 3

    variables:
      scratch:
        action: store_true
        help: To indicate this is a scratch build

Which translates into:

.. code-block:: none

  --scratch             To indicate this is a scratch build

Calling ``obsah release --scratch`` will result in ``ansible-playbook release -e '{"scratch": true}'``.

The ``store_false`` behaves in the same way as ``store_true`` but with a different value.

Storing lists can be done with the ``append`` action. It's exposed as a repeatable argument:

.. code-block:: yaml
  :emphasize-lines: 4

    variables:
      releasers:
        parameter: --releaser
        action: append
        help: Specifiy the releasers

Calling ``obsah release --releaser first --releaser second`` will translate to ``ansible-playbook release -e '{"releasers": ["first", "second"]}'``.

In addition to the standard argparse actions, Obsah provides two custom actions:

* ``append_unique`` - Similar to ``append``, but ensures no duplicate values are added to the list
* ``remove`` - Removes a value from a list (useful when combined with ``dest`` to have add/remove parameter pairs)

Type Validation
"""""""""""""""

Variables can have a ``type`` field (`argparse type`_) to validate user input. Obsah extends argparse with custom types:

.. _argparse type: https://docs.python.org/3/library/argparse.html#type

* ``File`` - Accepts only existing files
* ``AbsolutePath`` - Accepts only absolute paths
* ``Boolean`` - Accepts true/false or 1/0
* ``FQDN`` - Validates fully qualified domain names
* ``HTTPUrl`` - Validates HTTP/HTTPS URLs
* ``Port`` - Validates TCP/UDP ports (0-65535)

Example:

.. code-block:: yaml

    variables:
      config_file:
        type: File
        help: Path to the configuration file
      hostname:
        type: FQDN
        help: The server hostname
      use_ssl:
        type: Boolean
        help: Enable SSL connections

Choices
"""""""

You can restrict a variable to a specific set of values using ``choices`` (`argparse choices`_):

.. _argparse choices: https://docs.python.org/3/library/argparse.html#choices

.. code-block:: yaml

    variables:
      logging:
        choices:
          - journal
          - file
        help: Logging destination

This will restrict the ``--logging`` parameter to only accept ``journal`` or ``file`` as values.

Destination Override
""""""""""""""""""""

The ``dest`` field (`argparse dest`_) allows multiple parameters to modify the same variable. This is particularly useful when combined with the ``append_unique`` and ``remove`` actions:

.. _argparse dest: https://docs.python.org/3/library/argparse.html#dest

.. code-block:: yaml

    variables:
      options:
        parameter: --add-option
        action: append_unique
        dest: options
        help: Add an option
      remove_options:
        parameter: --remove-option
        action: remove
        dest: options
        help: Remove an option

This allows both ``--add-option`` and ``--remove-option`` to modify the same ``options`` variable.

Parameter Persistence
"""""""""""""""""""""

When ``OBSAH_PERSIST_PARAMS`` is enabled, parameter values are saved between runs. You can control this per-variable with the ``persist`` field (defaults to ``true``):

.. code-block:: yaml

    variables:
      build_type:
        help: Type of build
        persist: true  # Value persists across runs
      one_time_flag:
        help: One-time flag
        persist: false  # Value does not persist

Persisted parameters are marked with ``(persisted)`` in the help output and can be reset using ``--reset-<parameter-name>``.

Constraints
^^^^^^^^^^^

Constraints validate relationships between CLI arguments. They are defined at the top level in the metadata:

.. code-block:: yaml

    constraints:
      required_together:
        - [input_file, output_file]
      required_one_of:
        - [hostname, url]
      mutually_exclusive:
        - [hostname, url]
      required_if:
        - ['database_mode', 'external', ['database_host']]
      forbidden_if:
        - ['database_mode', 'internal', ['database_host']]

Available constraint types:

* ``required_together`` - All specified arguments must be provided together
* ``required_one_of`` - At least one of the specified arguments is required
* ``mutually_exclusive`` - The specified arguments cannot be used together
* ``required_if`` - If an argument has a specific value, require other arguments
* ``forbidden_if`` - If an argument has a specific value, forbid other arguments or argument-value pairs

The ``forbidden_if`` constraint supports both argument names and argument-value pairs:

.. code-block:: yaml

    constraints:
      forbidden_if:
        # Forbid database_host argument when database_mode is internal
        - ['database_mode', 'internal', ['database_host']]
        # Forbid ssl_mode=disable when database_mode is external
        - ['database_mode', 'external', [['ssl_mode', 'disable']]]

Including Other Metadata
^^^^^^^^^^^^^^^^^^^^^^^^

You can reuse variables and constraints from other playbooks using the ``include`` field:

.. code-block:: yaml

    include:
      - common
      - database

This will merge the ``variables`` and ``constraints`` from the ``common`` and ``database`` playbook metadata into the current playbook.

Resetting Persisted Parameters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When using parameter persistence, you can automatically reset certain parameters when a trigger parameter changes:

.. code-block:: yaml

    reset:
      - ['database_mode', ['database_host', 'database_port']]

This example will reset the persisted values of ``database_host`` and ``database_port`` whenever ``database_mode`` changes to a different value.

Metadata Reference
^^^^^^^^^^^^^^^^^^

This section provides a complete reference of all available metadata fields.

Top-Level Fields
""""""""""""""""

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Field
     - Required
     - Description
   * - ``help``
     - Optional
     - Help text for the playbook. First line appears in main help, full text in subcommand help.
   * - ``variables``
     - Optional
     - Mapping of variables to expose as CLI parameters.
   * - ``constraints``
     - Optional
     - Validation rules for argument relationships.
   * - ``include``
     - Optional
     - List of playbook names to include variables and constraints from.
   * - ``reset``
     - Optional
     - List of parameter reset rules for persisted parameters.

Variable Fields
"""""""""""""""

Each variable in the ``variables`` mapping can have these fields:

.. list-table::
   :header-rows: 1
   :widths: 20 15 20 45

   * - Field
     - Required
     - Source
     - Description
   * - ``help``
     - Yes
     - argparse
     - Help text for the parameter
   * - ``parameter``
     - No
     - Obsah
     - Custom CLI parameter name (default: auto-generated from variable name)
   * - ``action``
     - No
     - argparse + Obsah
     - Argparse action: ``store_true``, ``store_false``, ``append``, ``append_unique`` (Obsah), ``remove`` (Obsah)
   * - ``type``
     - No
     - argparse + Obsah
     - Type validator. Obsah types: ``File``, ``AbsolutePath``, ``Boolean``, ``FQDN``, ``HTTPUrl``, ``Port``
   * - ``choices``
     - No
     - argparse
     - List of allowed values
   * - ``dest``
     - No
     - argparse
     - Destination variable name (allows multiple parameters to modify same variable)
   * - ``persist``
     - No
     - Obsah
     - Whether to persist parameter value (default: ``true``)

Constraint Types
""""""""""""""""

All constraint types are defined under the ``constraints`` field:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Constraint Type
     - Description
   * - ``required_together``
     - List of argument groups that must all be provided together
   * - ``required_one_of``
     - List of argument groups where at least one must be provided
   * - ``mutually_exclusive``
     - List of argument groups that cannot be used together
   * - ``required_if``
     - List of ``[arg, value, [required_args]]`` - require args when condition is met
   * - ``forbidden_if``
     - List of ``[arg, value, [forbidden_items]]`` - forbid args or arg=value pairs when condition is met

Fixing the tests
^^^^^^^^^^^^^^^^

First of all, the tests for various playbooks are stored in ``tests/test_playbooks.py``.

* ``test_takes_package_argument`` verifies whether there's an action parameter. Most playbooks do, but if yours doesn't then it must be added.
* ``test_is_documented`` verifies you're written a help text for your playbook.
* ``test_help`` captures the help texts in ``tests/fixtures/help`` to ensure there are no unintended changes. Rendered output is easier to review. Because manually copying output is stupid, we automatically store the output if the file is missing. To update the content, remove it and run the tests (``pytest tests/test_playbooks.py::test_help -v``). Note it marks that test as skipped. Running it again should mark it as passed.

Releasing obsah
--------------

Before creating a new release, it's best to check if there are `issues`_ or `pull requests`_ that should be merged.

To create a new release, we use `bump2version`_ for version bumping. It can be installed via pip but using the Fedora package is easier. Note it's named after the predecessor that halted development, but we actually need the fork for signed tags:

    $ sudo dnf install bumpversion

Ensure you are on the latest commit:

    $ git checkout master
    $ git pull

To decide on the next version, the git log is a good indicator. We can either do a *major*, *minor* or *patch* release:

    $ bumpversion patch

This will modify all the files containing the version number, create a git commit and a GPG signed git tag. Once this is pushed, GitHub Actions will release it to PyPI:

    $ git push

.. _issues: https://github.com/theforeman/obsah/issues
.. _pull requests: https://github.com/theforeman/obsah/pulls
.. _bump2version: https://github.com/c4urself/bump2version
