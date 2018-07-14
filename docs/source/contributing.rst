############
Contributing
############

Creating a branch
-----------------
This project uses the GitFlow_ branching model. The ``master`` branch reflects the current
production-ready state. The ``develop`` branch is a perpetual development branch.

.. _GitFlow: http://nvie.com/posts/a-successful-git-branching-model/

New development is done in feature branches which are merged back
into the ``develop`` branch once development is completed. Prior to a release,
a release branch is created off of ``develop``. When the
release is ready, the release branch is merged into ``master`` and ``develop``.

Development branches are named with a prefix according to their purpose:

- ``feature/``: An added feature or improved functionality.
- ``bug/``: Bug fix.
- ``doc/``: Addition or cleaning of documentation.
- ``clean/``: Code clean-up.

When starting a new branch, be sure to branch from develop::

  $ git checkout -b my_feature develop

Keep any changes in this branch specific to one bug or feature. If the develop
branch has advanced since your branch was first created, then you can update
your branch by retrieving those changes from the develop branch::

  $ git fetch origin
  $ git rebase origin/develop

This will replay your commits on top of the latest version of the develop branch.
If there are merge conflicts, then you must resolve them.

Committing your code
--------------------
When committing to your changes, we recommend structuring the commit message
in the following way:

- subject line with less than < 80 chars
- one blank line
- optionally, a commit message body

Please reference the relevant GitHub issues in your commit message using
GH1234 or #1234.

For the subject line, this project uses the same convention for commit message
prefix and layout as the Pandas project. Here are some common prefixes and
guidelines for when to use them:

- ENH: Enhancement, new functionality
- BUG: Bug fix
- DOC: Additions/updates to documentation
- TST: Additions/updates to tests
- BLD: Updates to the build process/scripts
- PERF: Performance improvement
- CLN: Code cleanup

Combining commits
+++++++++++++++++
When you're ready to make a pull request and if you have made multiple commits,
then you may want to combine, or "squash", those commits. Squashing commits
helps to maintain a compact commit history, especially if a number of commits
were made to fix errors or bugs along the way. To squash your commits::

  git rebase -i HEAD-#

where # is the number of commits you want to combine.  If you want to squash
all commits on the branch::

  git rebase -i --root

Then you will need to push the branch forcefully to replace the current commits
with the new ones::

  git push origin new-feature -f

Incorporating a finished feature on develop
+++++++++++++++++++++++++++++++++++++++++++
Finished features should be added to the develop branch to be included in the
next release::

  $ git checkout develop
  Switched to branch 'develop'
  $ git merge --no-ff myfeature
  Updating ea1b82a..05e9557
  (summary of changes)
  $ git branch -d myfeature
  Deleted branch myfeature (was 05e9557).
  $ git push origin develop

The ``--no-ff`` flag causes the merge to always create a commit, even if it can
be done with a fast-forward. This way we record the existence of the feature
branch even after it has been deleted, and it groups all of the relevant
commits for this feature.

Note that pull-requests into develop require passing Continuous Integration
(CI) builds on Travis.ci and AppVeyor, and at least one approved review.

Code standards
--------------
*DGP* uses the PEP8_ standard. In particular, that means:

- we restrict line-length to 79 characters to promote readability
- passing arguments should have spaces after commas, *e.g.*,
  ``foo(arg1, arg2, kw1='bar')``

Continuous integration will run the flake8 tool to check for conformance with
PEP8.  Therefore, it is beneficial to run the check yourself before submitting
a pull request::

  git diff master --name-only -- '*.py' | flake8 --diff

.. _PEP8: http://www.python.org/dev/peps/pep-0008/

Test-driven development
-----------------------
All new features and added functionality will require new tests or amendments
to existing tests, so we highly recommend that all contributors embrace
`test-driven development (TDD)`_.

.. _`test-driven development (TDD)`: http://en.wikipedia.org/wiki/Test-driven_development

All tests should go to the ``tests`` subdirectory. We suggest looking to any of
the examples in that directory to get ideas on how to write tests for the
code that you are adding or modifying.

*DGP* uses the pytest_ framework for unit testing and coverage.py_ to gauge the
effectiveness of tests by showing which parts of the code are being executed
by tests, and which are not. The pytest-cov_ extension is used in conjunction
with Py.Test and coverage.py to generate coverage reports after executing the
test suite.

Continuous integration will also run the test-suite with coverage, and report
the coverage statistics to `Coveralls <https://coveralls.io>`__

.. _pytest: https://docs.pytest.org/
.. _pytest-cov: https://pytest-cov.readthedocs.io/
.. _unittest: https://docs.python.org/3/library/unittest.html
.. _coverage.py: https://coverage.readthedocs.io/en/coverage-4.4.1/

Running the test suite
++++++++++++++++++++++
The test suite can be run from the repository root::

  pytest --cov=dgp tests
  # or
  coverage run --source=dgp -m unittest discover

Add the following parameter to display lines missing coverage when using the
pytest-cov extension::

  --cov-report term-missing


Use ``coverage report`` to report the results on test coverage::

  $ coverage report -m
  Name                             Stmts   Miss  Cover   Missing
  --------------------------------------------------------------
  dgp/__init__.py                      0      0   100%
  dgp/lib/__init__.py                  0      0   100%
  dgp/lib/etc.py                       6      0   100%
  dgp/lib/gravity_ingestor.py         94      0   100%
  dgp/lib/time_utils.py               52      3    94%   131-136
  dgp/lib/trajectory_ingestor.py      50      8    84%   62-65, 93-94, 100-101, 106
  --------------------------------------------------------------
  TOTAL                              202     11    95%

Documentation
-------------
The documentation is written in reStructuredText and built using Sphinx. Some
other things to know about the docs:

- It consists of two parts: the docstrings in the code and the docs in this folder.

  Docstrings provide a clear explanation of the usage of the individual functions,
  while the documentation in this folder consists of tutorials, planning, and
  technical documents related data formats, sensors, and processing techniques.

- The docstrings in this project follow the  `NumPydoc docstring standard`_.
  This standard specifies the format of the different sections of the docstring.
  See `this document`_ for a detailed explanation and examples.

- See `Quick reStructuredText <http://docutils.sourceforge.net/docs/user/rst/quickref.html>`__
  for a quick-reference on reStructuredText syntax and markup.

- Documentation can also contain cross-references to other
  classes/objects/modules using the `Sphinx Domain Reference Syntax <http://www
  .sphinx-doc.org/en/master/usage/restructuredtext/domains.html>`__

- Documentation is automatically built on push for designated branches
  (typically master and develop) and hosted on `Read the Docs <https://readthedocs.org>`__

.. _`NumPydoc docstring standard`: https://numpydoc.readthedocs.io/en/latest/
.. _`this document`: http://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_numpy.html

Building the documentation
++++++++++++++++++++++++++
Navigate to the ``dgp/docs`` directory in the console. On Linux and MacOS X run::

  make html

or on Windows run::

  make.bat

If the build completes without errors, then you will find the HTML output in
``dgp/docs/build/html``.

Alternately, documentation can be built by calling the sphinx python module
e.g.::

   python -m sphinx -M html source build

