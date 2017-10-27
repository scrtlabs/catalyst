Install
=======

Installing with ``pip``
-----------------------

Installing Catalyst via ``pip`` is slightly more involved than the average
Python package.

There are two reasons for the additional complexity:

1. Catalyst ships several C extensions that require access to the CPython C API.
   In order to build the C extensions, ``pip`` needs access to the CPython
   header files for your Python installation.

2. Catalyst depends on `numpy <http://www.numpy.org/>`_, the core library for
   numerical array computing in Python.  Numpy depends on having the `LAPACK
   <http://www.netlib.org/lapack>`_ linear algebra routines available.

Because LAPACK and the CPython headers are non-Python dependencies, the correct
way to install them varies from platform to platform.  If you'd rather use a
single tool to install Python and non-Python dependencies, or if you're already
using `Anaconda <http://continuum.io/downloads>`_ as your Python distribution,
you can skip to the :ref:`Installing with Conda <conda>` section.

Once you've installed the necessary additional dependencies (see below for
your particular platform), you should be able to simply run

.. code-block:: bash

   $ pip install enigma-catalyst

If you use Python for anything other than Catalyst, we **strongly** recommend
that you install in a `virtualenv
<https://virtualenv.readthedocs.org/en/latest>`_.  The `Hitchhiker's Guide to
Python`_ provides an `excellent tutorial on virtualenv
<http://docs.python-guide.org/en/latest/dev/virtualenvs/>`_. Here's a summarized
version:

.. code-block:: bash

   $ pip install virtualenv
   $ virtualenv catalyst-venv
   $ source ./catalyst-venv/bin/activate
   $ pip install enigma-catalyst

Though not required by Catalyst directly, our example algorithms use matplotlib 
to visually display the results of the trading algorithms. If you wish to run 
any examples or use matplotlib during development, it can be installed using:

.. code-block:: bash

    $ pip install matplotlib

GNU/Linux
~~~~~~~~~

On `Debian-derived`_ Linux distributions, you can acquire all the necessary
binary dependencies from ``apt`` by running:

.. code-block:: bash

   $ sudo apt-get install libatlas-base-dev python-dev gfortran pkg-config libfreetype6-dev

On recent `RHEL-derived`_ derived Linux distributions (e.g. Fedora), the
following should be sufficient to acquire the necessary additional
dependencies:

.. code-block:: bash

   $ sudo dnf install atlas-devel gcc-c++ gcc-gfortran libgfortran python-devel redhat-rep-config

On `Arch Linux`_, you can acquire the additional dependencies via ``pacman``:

.. code-block:: bash

   $ pacman -S lapack gcc gcc-fortran pkg-config

.. Commenting it out until Catalyst fully supports Python 3.X
..
.. There are also AUR packages available for installing `Python 3.4
.. <https://aur.archlinux.org/packages/python34/>`_ (Arch's default python is now
.. 3.5, but Catalyst only currently supports 3.4), and `ta-lib
.. <https://aur.archlinux.org/packages/ta-lib/>`_, an optional Catalyst dependency.
.. Python 2 is also installable via:

.. 

..   $ pacman -S python2

OSX
~~~

The version of Python shipped with OSX by default is generally out of date, and
has a number of quirks because it's used directly by the operating system.  For
these reasons, many developers choose to install and use a separate Python
installation. The `Hitchhiker's Guide to Python`_ provides an excellent guide
to `Installing Python on OSX <http://docs.python-guide.org/en/latest/>`_, which
explains how to install Python with the `Homebrew`_ manager.

Assuming you've installed Python with Homebrew, you'll also likely need the
following brew packages:

.. code-block:: bash

   $ brew install freetype pkg-config gcc openssl

OSX + virtualenv + matplotlib
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A note about using matplotlib in virtual enviroments on OSX: it may be necessary to run

.. code-block:: bash

   echo "backend: TkAgg" > ~/.matplotlib/matplotlibrc

in order to override the default ``macosx`` backend for your system, which may not 
be accessible from inside the virtual environment. This will allow Catalyst to open 
matplotlib charts from within a virtual environment, which is useful for displaying 
the performance of your backtests.  To learn more about matplotlib backends, please refer to the
`matplotlib backend documentation <https://matplotlib.org/faq/usage_faq.html#what-is-a-backend>`_.


Windows
~~~~~~~

In Windows, you will need the `Microsoft Visual C++ Compiler for Python 2.7 
<https://www.microsoft.com/en-us/download/details.aspx?id=44266>`_. This package 
contains the compiler and the set of system headers necessary for producing 
binary wheels for Python 2.7 packages. If it's not already in your system, download
it and install it before proceeding to the next step.

For windows, the easiest and best supported way to install Catalyst is to use
:ref:`Conda <conda>`.

Troubleshooting Visual C++ Compiler Install
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We run into two different errors when trying to install the the `Microsoft Visual C++ 
Compiler for Python 2.7` mentioned above:

-  


Amazon Linux AMI
~~~~~~~~~~~~~~~~

The packages ``pip`` and ``setuptools`` that come shipped by default are very outdated. 
Thus, you first need to run:

.. code-block:: bash

   pip install --upgrade pip setuptools

The default installation is also missing the C and C++ compilers, which you install by:

.. code-block:: bash

   sudo yum install gcc gcc-c++

Then you should follow the regular installation instructions outlined at the beginning 
of this page.


Troubleshooting ``pip`` Install
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Issue**: 
   Package enigma-catalyst cannot be found 
 
**Solution**: 
   Make sure you have the most up-to-date version of pip installed, by running: 

   .. code-block:: bash

      pip install --upgrade pip

   On Windows, the recommended command is:

   .. code-block:: bash

      python -m pip install --upgrade pip

----

**Issue**: 
   Package enigma-catalyst cannot still be found, even after upgrading pip (see above), with an error similar to:

   .. code-block:: bash

      Downloading/unpacking enigma-catalyst
      Could not find a version that satisfies the requirement enigma-catalyst (from versions: 0.1.dev9, 0.2.dev2, 0.1.dev4, 0.1.dev5, 0.1.dev3, 0.2.dev1, 0.1.dev8, 0.1.dev6)
      Cleaning up...
      No distributions matching the version for enigma-catalyst

**Solution**:
   In some systems (this error has been reported in Ubuntu), pip is configured to only find stable versions by default. Since Catalyst is in alpha version, pip cannot find a matching version that satisfies the installation requirements. The solution is to include the `--pre` flag to include pre-release and development versions:

   .. code-block:: bash

      pip install --pre enigma-catalyst

----

**Issue**: 
   Package enigma-catalyst fails to install because of outdated setuptools

**Solution**: 
   Upgrade to the most up-to-date setuptools package by running: 

   .. code-block:: bash

      pip install --upgrade pip setuptools

----

**Issue**:
   Missing required packages  

**Solution**:
   Download `requirements.txt 
   <https://github.com/enigmampc/catalyst/blob/master/etc/requirements.txt>`_ 
   (click on the *Raw* button and Right click -> Save As...) and use it to
   install all the required dependencies by running:

   .. code-block:: bash

      pip install -r requirements.txt

----

**Issue**: 
   Installation fails with error: ``fatal error: Python.h: No such file or directory``

**Solution**: 
   Some systems (this issue has been reported in Ubuntu) require `python-dev` for the proper build and installation of package dependencies. The solution is to install python-dev, which is independent of the virtual environment. In Ubuntu, you would need to run:

   .. code-block:: bash

      sudo apt-get install python-dev


.. _conda:

Installing with ``conda``
-------------------------

Another way to install Catalyst is via the ``conda`` package manager, which
comes as part of Continuum Analytics' `Anaconda
<http://continuum.io/downloads>`_ distribution.

The primary advantage of using Conda over ``pip`` is that conda natively
understands the complex binary dependencies of packages like ``numpy`` and
``scipy``.  This means that ``conda`` can install Catalyst and its dependencies
without requiring the use of a second tool to acquire Catalyst's non-Python
dependencies.

For instructions on how to install ``conda``, see the `Conda Installation
Documentation <http://conda.pydata.org/docs/download.html>`_. Alternatively, you 
can install MiniConda, which is a smaller footprint (fewer packages and smaller 
size) than its big brother Anaconda, but it still contains all the main packages 
needed. To install MiniConda, you can follow these steps:

1. Download `MiniConda <https://conda.io/miniconda.html>`_. Select Python 2.7 for 
   your Operating System.
2. Install MiniConda. See the `Installation Instructions <https://conda.io/docs/user-guide/install/index.html>`_
   if you need help.
3. Ensure the correct installation by running ``conda list`` in a Terminal window,
   which should print the list of packages installed with Conda.

Once either Conda or MiniConda has been set up you can install Catalyst:

1. Download the file `python2.7-environment.yml <https://github.com/enigmampc/catalyst/blob/master/etc/python2.7-environment.yml>`_.
2. Open a Terminal window and enter [``cd/dir``] into the directory where you saved
   the above ``python2.7-environment.yml`` file.
3. Install using this file. This step can take about 5-10 minutes to install.

   .. code-block:: bash

      conda env create -f python2.7-environment.yml

4. Activate the environment (which you need to do every time you start a new session
   to run Catalyst):

   **Linux or OSX:**

   .. code-block:: bash

      source activate catalyst

   **Windows:**

   .. code-block:: bash

      activate catalyst

Congratulations! You now have Catalyst installed.

Troubleshooting ``conda`` Install
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the command  ``conda env create -f python2.7-environment.yml`` in step 3 above failed 
for any reason, you can try setting up the environment manually with the following steps:

1. Create the environment:

   .. code-block:: bash

      conda create --name catalyst python=2.7 scipy

2. Activate the environment:

   **Linux or OSX:**

   .. code-block:: bash

      source activate catalyst

   **Windows:**

   .. code-block:: bash

      activate catalyst

3. Install the Catalyst inside the environment:

   .. code-block:: bash

      pip install enigma-catalyst matplotlib

Getting Help
------------

If after following the instructions above, and going through the *Troubleshooting* sections, 
you still experience problems installing Catalyst, you can seek additional help through the 
following channels:

- Join our `Discord community <https://discord.gg/SJK32GY>`_, and head over the #catalyst_dev 
  channel where many other users (as well as the project developers) hang out, and can assist 
  you with your particular issue. The more descriptive and the more information you can provide, 
  the easiest will be for others to help you out.

- Report the problem you are experiencing on our 
  `GitHub repository <https://github.com/enigmampc/catalyst/issues>`_ following the guidelines 
  provided therein. Before you do so, take a moment to browse through all `previous reported issues
  <https://github.com/enigmampc/catalyst/issues?utf8=%E2%9C%93&q=is%3Aissue>`_ in the likely case
  that someone else experienced that same issue before, and you get a hint on how to solve it.


.. _`Debian-derived`: https://www.debian.org/misc/children-distros
.. _`RHEL-derived`: https://en.wikipedia.org/wiki/Red_Hat_Enterprise_Linux_derivatives
.. _`Arch Linux` : https://www.archlinux.org/
.. _`Hitchhiker's Guide to Python` : http://docs.python-guide.org/en/latest/
.. _`Homebrew` : http://brew.sh
