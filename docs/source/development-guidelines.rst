Development Guidelines
======================
This page is intended for developers of Catalyst, people who want to contribute
to the Catalyst codebase or documentation, or people who want to install from
source and make local changes to their copy of Catalyst.

All contributions, bug reports, bug fixes, documentation improvements,
enhancements and ideas are welcome.
We `track issues <https://github.com/enigmampc/catalyst/issues>`_ on
`GitHub <https://github.com/enigmampc/catalyst>`_ and also have a
`discord group <https://discord.gg/SJK32GY>`_ and a
`forum <https://forum.catalystcrypto.io>`_ where you can share ideas and ask
questions.

Creating a Development Environment
----------------------------------

First, you'll need to clone Catalyst by running:

.. code-block:: bash

   $ git clone git@github.com:enigmampc/catalyst.git

Then check out to a new branch where you can make your changes:

.. code-block:: bash
		
   $ git checkout -b some-short-descriptive-name

If you don't already have them, you'll need some C library dependencies. You can follow the `install guide <install.html>`_ to get the appropriate dependencies.

The following section assumes you already have virtualenvwrapper and pip installed on your system. Suggested installation of Python library dependencies used for development:

.. code-block:: bash

   $ mkvirtualenv catalyst
   $ ./etc/ordered_pip.sh ./etc/requirements.txt
   $ pip install -r ./etc/requirements_dev.txt
   $ pip install -r ./etc/requirements_blaze.txt 

Finally, you can build the C extensions by running:

.. code-block:: bash

   $ python setup.py build_ext --inplace

Development with Docker
-----------------------

If you want to work with zipline using a `Docker`__ container, you'll need to 
build the ``Dockerfile`` in the Zipline root directory, and then build 
``Dockerfile-dev``. Instructions for building both containers can be found in 
``Dockerfile`` and ``Dockerfile-dev``, respectively.

__ https://docs.docker.com/get-started/
   
Git Branching Structure
-----------------------

If you want to contribute to the codebase of Catalyst, familiarize yourself with our branching structure, a fairly standardized one for that matter, that follows what is documented in the following article: `A successful Git branching model <http://nvie.com/posts/a-successful-git-branching-model/>`_. To contribute, create your local branch and submit a Pull Request (PR) to the **develop** branch.

.. image:: https://camo.githubusercontent.com/9bde6fb64a9542a572e0e2017cbb58d9d2c440ac/687474703a2f2f6e7669652e636f6d2f696d672f6769742d6d6f64656c4032782e706e67

Style Guide & Running Tests
---------------------------

We use `flake8`__ for checking style requirements and `nosetests`__ to run Catalyst tests. Our `continuous integration`__ tool will run these commands.

__ http://flake8.pycqa.org/en/latest/
__ http://nose.readthedocs.io/en/latest/
__ https://en.wikipedia.org/wiki/Continuous_integration

Before submitting patches or pull requests, please ensure that your changes pass when running:

.. code-block:: bash

   $ flake8 catalyst tests

In order to run tests locally, you'll need to install several libraries
(one of them is TA-lib, so make sure you have it installed following `these instructions`__ before continuing).

__ https://mrjbq7.github.io/ta-lib/install.html

.. code-block:: bash

   $ pip install -r ./etc/requirements.txt
   $ pip install -r ./etc/requirements_dev.txt
   $ pip install -r ./etc/requirements_blaze.txt
   $ pip install -r ./etc/requirements_talib.txt
   $ pip install -e .

You should now be free to run tests:

.. code-block:: bash

   $ cd tests && nosetests


Continuous Integration
----------------------

We use `Travis CI`__ for Linux-64 bit builds.

.. note::

   We do not currently have CI for OSX-64 bit builds or Windows-64 bit builds.

__ https://travis-ci.com/enigmampc/catalyst


Contributing to the Docs
------------------------

If you'd like to contribute to the documentation on enigmampc.github.io, you can navigate to ``docs/source/`` where each `reStructuredText <https://en.wikipedia.org/wiki/ReStructuredText>`_ file is a separate section there. To add a section, create a new file called ``some-descriptive-name.rst`` and add ``some-descriptive-name`` to ``index.rst``. To edit a section, simply open up one of the existing files, make your changes, and save them.

We use `Sphinx <http://www.sphinx-doc.org/en/stable/>`_ to generate documentation for Catalyst, which you will need to install by running:

.. code-block:: bash

   $ pip install -r ./etc/requirements_docs.txt

To build and view the docs locally, run:

.. code-block:: bash

   # assuming you're in the Catalyst root directory
   $ cd docs
   $ make html
   $ {BROWSER} build/html/index.html


There is a `documented issue <https://github.com/sphinx-doc/sphinx/issues/3212>`_ 
with ``sphinx`` and ``docutils`` that causes the error below when trying to build 
the docs.

.. code-block:: text

   Exception occurred:
     File "(...)/env-c/lib/python2.7/site-packages/docutils/writers/_html_base.py", line 671, in depart_document
       assert not self.context, 'len(context) = %s' % len(self.context)
   AssertionError: len(context) = 3

If you get this error, you need to downgrade your version of ``docutils`` as 
follows, and build the docs again:

.. code-block:: bash

   $ pip install docutils==0.12


Commit messages
---------------

Standard prefixes to start a commit message:

.. code-block:: text

   BLD: change related to building Catalyst
   BUG: bug fix
   DEP: deprecate something, or remove a deprecated object
   DEV: development tool or utility
   DOC: documentation
   ENH: enhancement
   MAINT: maintenance commit (refactoring, typos, etc)
   REV: revert an earlier commit
   STY: style fix (whitespace, PEP8, flake8, etc)
   TST: addition or modification of tests
   REL: related to releasing Catalyst
   PERF: performance enhancements


Some commit style guidelines:

Commit lines should be no longer than `72 characters <https://git-scm.com/book/en/v2/Distributed-Git-Contributing-to-a-Project>`_. The first line of the commit should include one of the above prefixes. There should be an empty line between the commit subject and the body of the commit. In general, the message should be in the imperative tense. Best practice is to include not only what the change is, but why the change was made.

**Example:**

.. code-block:: text

   MAINT: Remove unused calculations of max_leverage, et al.

   In the performance period the max_leverage, max_capital_used,
   cumulative_capital_used were calculated but not used.

   At least one of those calculations, max_leverage, was causing a
   divide by zero error.
   
   Instead of papering over that error, the entire calculation was
   a bit suspect so removing, with possibility of adding it back in
   later with handling the case (or raising appropriate errors) when
   the algorithm has little cash on hand.


Formatting Docstrings
---------------------

When adding or editing docstrings for classes, functions, etc, we use `numpy <https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt>`_ as the canonical reference.


