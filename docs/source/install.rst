Install
=======

To get started with Catalyst, you will need to install it in your computer. 
Like any other piece of software, Catalyst has a number of dependencies 
(other software on which it depends to run) that you will need to install, as 
well. We recommend using a software named ``Conda`` that will manage all 
these dependencies for you, and set up the environment needed to get you up 
and running as easily as possible. This is the recommended installation method
for Windows, MacOS and Linux. See :ref:`Installing with Conda <conda>`.

What conda does is create a pre-configured environment, and inside that 
environment install Catalyst using ``pip``, Python's package manager. Thus, 
as an alternative installation method for MacOS and Linux, you can install 
Catalyst directly with ``pip`` (we recommend in combination with a virtual 
environment). See :ref:`Installing with pip <pip>`.

Alternatively you can install Catalyst using ``pipenv`` which is a mix of pip
and virtualenv. See :ref:`Installing with pipenv <pipenv>`.

Regardless of the method, each operating system (OS), has its own 
prerequisites, make sure to review the corresponding sections for your system:
:ref:`Linux <linux>`, :ref:`MacOS <macos>` and :ref:`Windows <windows>`.

.. _conda:

Installing with ``conda``
-------------------------

The preferred method to install Catalyst is via the ``conda`` package manager, 
which comes as part of Continuum Analytics' `Anaconda
<http://continuum.io/downloads>`_ distribution.

The primary advantage of using Conda over ``pip`` is that conda natively
understands the complex binary dependencies of packages like ``numpy`` and
``scipy``.  This means that ``conda`` can install Catalyst and its 
dependencies without requiring the use of a second tool to acquire Catalyst's 
non-Python dependencies.

  For Windows, you will first need to install the *Microsoft Visual C++ 
  Compiler for Python*. Follow the instructions on the :ref:`Windows
  <windows>` section and come back here.

For instructions on how to install ``conda``, see the `Conda Installation
Documentation <http://conda.pydata.org/docs/download.html>`_. Alternatively, 
you can install MiniConda, which is a smaller footprint (fewer packages and 
smaller size) than its big brother Anaconda, but it still contains all the 
main packages needed. To install MiniConda, you can follow these steps:

1. Download `MiniConda <https://conda.io/miniconda.html>`_. Select either 
   Python 3.6 (recommended) or Python 2.7 for your Operating System. The 
   `Enigma Data Marketplace <https://enigmampc.github.io/marketplace/>`_ will 
   require Python3, that's why we are recommending to opt for the newer version.
2. Install MiniConda. See the `Installation Instructions 
   <https://conda.io/docs/user-guide/install/index.html>`_ if you need help.
3. Ensure the correct installation by running ``conda list`` in a Terminal 
   window, which should print the list of packages installed with Conda.

  For Windows, if you accepted the default installation options, you didn't 
  check an option to add Conda to the PATH, so trying to run ``conda`` from
  a regular ``Command Prompt`` will result in the following error: ``'conda' 
  is no recognized as an internal or external command, operatble program or 
  batch file``. That's to be expected. You will nee to launch an ``Anaconda 
  Prompt`` that was added at installation time to your list of programs 
  available from the Start menu. 

Once either Conda or MiniConda has been set up you can install Catalyst:

1. Download the proper .yml file matching your Conda installation from
   step #1 above.
   To download, simply click on the 'Raw' button and save the file locally
   to a folder you can remember. Make sure that the file gets saved with the
   ``.yml`` extension, and nothing like a ``.txt`` file or anything else.

   **Linux or MacOS:**
   Download the file `python3.6-environment.yml
   <https://github.com/enigmampc/catalyst/blob/master/etc/python3.6-environment.yml>`_
   (recommended) or `python2.7-environment.yml
   <https://github.com/enigmampc/catalyst/blob/master/etc/python2.7-environment.yml>`_

   **Windows:**
   Download the file `python3.6-environment-windows.yml
   <https://github.com/enigmampc/catalyst/blob/master/etc/python3.6-environment-windows.yml>`_
   (recommended) or `python2.7-environment.yml
   <https://github.com/enigmampc/catalyst/blob/master/etc/python2.7-environment.yml>`_

2. Open a Terminal window and enter [``cd/dir``] into the directory where you 
   saved the above ``.yml`` file.


3. Install using this file. This step can take about 5-10 minutes to install.

   **Linux or MacOS Python 3.6:**

   .. code-block:: bash

      conda env create -f python3.6-environment.yml

   **Linux or MacOS Python 2.7:**

   .. code-block:: bash

      conda env create -f python2.7-environment.yml


   **Windows Python 3.6:**

   .. code-block:: bash

      conda env create -f python3.6-environment-windows.yml

   **Windows Python 2.7:**

   .. code-block:: bash

      conda env create -f python2.7-environment.yml

4. Activate the environment (which you need to do every time you start a new 
   session to run Catalyst):

   **Linux or MacOS:**

   .. code-block:: bash

      source activate catalyst

   **Windows:**

   .. code-block:: bash

      activate catalyst

5. Verify that Catalyst is install correctly:

   .. code-block:: bash

     catalyst --version

   which should display the current version.

Congratulations! You now have Catalyst installed.

Troubleshooting ``conda`` Install
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the command  ``conda env create -f python2.7-environment.yml`` in step 3 
above failed for any reason, you can try setting up the environment manually 
with the following steps:

1. If the above installation failed, and you have a partially set up catalyst
   environment, remove it first. If you are starting from scratch, proceed to 
   step #2:

   .. code-block:: bash

      conda env remove --name catalyst

2. Create the environment:

   for python 2.7:

   .. code-block:: bash

      conda create --name catalyst python=2.7 scipy zlib

  or for python 3.6:

   .. code-block:: bash

      conda create --name catalyst python=3.6 scipy zlib

3. Activate the environment:

   **Linux or MacOS:**

   .. code-block:: bash

      source activate catalyst

   **Windows:**

   .. code-block:: bash

      activate catalyst

4. Install the Catalyst inside the environment:

   .. code-block:: bash

      pip install enigma-catalyst matplotlib

5. Verify that Catalyst is installed correctly:

   .. code-block:: bash

     catalyst --version

   which should display the current version.

Congratulations! You now have Catalyst properly installed.

.. _pip:

Installing with ``pip``
-----------------------

Installing Catalyst via ``pip`` is slightly more involved than the average
Python package.

There are two reasons for the additional complexity:

1. Catalyst ships several C extensions that require access to the CPython C 
   API. In order to build the C extensions, ``pip`` needs access to the 
   CPython header files for your Python installation.

2. Catalyst depends on `numpy <http://www.numpy.org/>`_, the core library for
   numerical array computing in Python.  Numpy depends on having the `LAPACK
   <http://www.netlib.org/lapack>`_ linear algebra routines available.

Because LAPACK and the CPython headers are non-Python dependencies, the 
correctway to install them varies from platform to platform.  If you'd rather 
use a single tool to install Python and non-Python dependencies, or if you're 
already using `Anaconda <http://continuum.io/downloads>`_ as your Python 
distribution, refer to the :ref:`Installing with Conda <conda>` section.

If you use Python for anything other than Catalyst, we **strongly** recommend
that you install in a `virtualenv
<https://virtualenv.readthedocs.org/en/latest>`_.  The `Hitchhiker's Guide to
Python`_ provides an `excellent tutorial on virtualenv
<http://docs.python-guide.org/en/latest/dev/virtualenvs/>`_. Here's a 
summarized version:

.. code-block:: bash

   $ pip install virtualenv
   $ virtualenv catalyst-venv
   $ source ./catalyst-venv/bin/activate

Once you've installed the necessary additional dependencies for your system 
(:ref:`Linux`, :ref:`MacOS` or :ref:`Windows`) **and have activated your virtualenv**, you should be able to simply run

.. code-block:: bash

   $ pip install enigma-catalyst matplotlib

Note that in the command above we install two different packages. The second 
one, ``matplotlib`` is a visualization library. While it's not strictly 
required to run catalyst simulations or live trading, it comes in very handy
to visualize the performance of your algorithms, and for this reason we 
recommend you install it, as well.


Troubleshooting ``pip`` Install
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Issue**: 
   Package enigma-catalyst cannot be found 
 
**Solution**: 
   Make sure you have the most up-to-date version of pip installed, by running: 

   .. code-block:: bash

      $ pip install --upgrade pip

   On Windows, the recommended command is:

   .. code-block:: bash

      $ python -m pip install --upgrade pip

----

**Issue**: 
   Package enigma-catalyst cannot still be found, even after upgrading pip 
   (see above), with an error similar to:

   .. code-block:: bash

      Downloading/unpacking enigma-catalyst
      Could not find a version that satisfies the requirement enigma-catalyst 
      (from versions: 0.1.dev9, 0.2.dev2, 0.1.dev4, 0.1.dev5, 0.1.dev3, 
      0.2.dev1, 0.1.dev8, 0.1.dev6)
      Cleaning up...
      No distributions matching the version for enigma-catalyst

**Solution**:
   In some systems (this error has been reported in Ubuntu), pip is configured 
   to only find stable versions by default. Since Catalyst is in alpha 
   version, pip cannot find a matching version that satisfies the installation 
   requirements. The solution is to include the `--pre` flag to include 
   pre-release and development versions:

   .. code-block:: bash

      $ pip install --pre enigma-catalyst

----

**Issue**: 
   Package enigma-catalyst fails to install because of outdated setuptools

**Solution**: 
   Upgrade to the most up-to-date setuptools package by running: 

   .. code-block:: bash

      $ pip install --upgrade pip setuptools

----

**Issue**:
   Missing required packages  

**Solution**:
   Download `requirements.txt 
   <https://github.com/enigmampc/catalyst/blob/master/etc/requirements.txt>`_ 
   (click on the *Raw* button and Right click -> Save As...) and use it to
   install all the required dependencies by running:

   .. code-block:: bash

      $ pip install -r requirements.txt

----

**Issue**: 
   Installation fails with error: 
   ``fatal error: Python.h: No such file or directory``

**Solution**: 
   Some systems (this issue has been reported in Ubuntu) require `python-dev` 
   for the proper build and installation of package dependencies. The solution 
   is to install python-dev, which is independent of the virtual environment. 
   In Ubuntu, you would need to run:

   .. code-block:: bash

      $ sudo apt-get install python-dev

----

**Issue**:
   Missing TA_Lib

**Solution**:
   Follow `these instructions
   <https://mrjbq7.github.io/ta-lib/install.html>`_ to install the TA_Lib Python wrapper
   (and if needed, its underlying C library as well).

.. _pipenv:

Installing with ``pipenv``
--------------------------

Installing Catalyst via ``pipenv`` is perhaps easier that installing it via
``pip`` itself but you need to install ``pipenv`` first via ``pip``.

.. code-block:: bash

   $ pip install pipenv

Once ``pipenv`` is installed you can proceed by creating a project folder and
installing Catalyst on that project automagically as follows:

.. code-block:: bash

   $ mkdir project
   $ cd project
   $ pipenv --two
   $ pipenv install enigma-catalyst matplotlib

Until now the workflow compared to ``pip`` is almost identical, the difference
is that you don't need to load manually any virtualenv however you need to use
the `pipenv run` prefix to run the `catalyst` command as follows:

.. code-block:: bash

   $ pipenv run catalyst --version

If you want to know more about ``pipenv`` go to the `pipenv github repo`_

.. _`pipenv github repo`: https://github.com/pypa/pipenv

.. _linux:

GNU/Linux Requirements
----------------------

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

Amazon Linux AMI Notes
~~~~~~~~~~~~~~~~~~~~~~

The packages ``pip`` and ``setuptools`` that come shipped by default are very 
outdated. Thus, you first need to run:

.. code-block:: bash

   $ pip install --upgrade pip setuptools

The default installation is also missing the C and C++ compilers, which you 
install by:

.. code-block:: bash

   $ sudo yum install gcc gcc-c++

Then you should follow the regular installation instructions outlined at the 
beginning of this page.


.. _MacOS:

MacOS Requirements
------------------

The version of Python shipped with MacOS by default is generally out of date, 
and has a number of quirks because it's used directly by the operating system.
For these reasons, many developers choose to install and use a separate Python
installation. The `Hitchhiker's Guide to Python`_ provides an excellent guide
to `Installing Python on MacOS <http://docs.python-guide.org/en/latest/>`_, 
which explains how to install Python with the `Homebrew`_ manager.

Assuming you've installed Python with Homebrew, you'll also likely need the
following brew packages:

.. code-block:: bash

   $ brew install freetype pkg-config gcc openssl

MacOS + virtualenv/conda + matplotlib
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The first time that you try to run an algorithm that loads the ``matplotlib`` 
library, you may get the following error:

.. code-block:: text

  RuntimeError: Python is not installed as a framework. The Mac OS X backend 
  will not be able to function correctly if Python is not installed as a 
  framework. See the Python documentation for more information on installing 
  Python as a framework on Mac OS X. Please either reinstall Python as a 
  framework, or try one of the other backends. If you are using (Ana)Conda 
  please install python.app and replace the use of 'python' with 'pythonw'. 
  See 'Working with Matplotlib on OSX' in the Matplotlib FAQ for more 
  information.

This is a ``matplotlib``-specific error, that will go away once you run the 
following command:

.. code-block:: bash

   $ echo "backend: TkAgg" > ~/.matplotlib/matplotlibrc

in order to override the default ``MacOS`` backend for your system, which 
may not be accessible from inside the virtual or conda environment. This will 
allow Catalyst to open matplotlib charts from within a virtual environment, 
which is useful for displaying the performance of your backtests.  To learn more 
about matplotlib backends, please refer to the
`matplotlib backend documentation <https://matplotlib.org/faq/usage_faq.html#what-is-a-backend>`_.

.. _windows:

Windows Requirements
--------------------

In Windows, you will first need to install the Microsoft Visual C++ Compiler, 
which is different depending on the version of Python that you plan to use:

* Python 3.5, 3.6: `Visual C++ 2015 Build Tools 
  <https://www.microsoft.com/en-us/download/details.aspx?id=48159>`_,
  which installs Visual C++ version 14.0. **This is the recommended version**

* Python 2.7: `Microsoft Visual C++ Compiler for Python 2.7 
  <https://www.microsoft.com/en-us/download/details.aspx?id=44266>`_, which 
  installs version Visual C++ version 9.0

This package contains the compiler and the set of system headers necessary for 
producing binary wheels for Python packages. If it's not already in your 
system, download it and install it before proceeding to the next step. If you 
need additional help, or are looking for other versions of Visual C++ for 
Windows (only advanced users), follow `this link <https://wiki.python.org/moin/WindowsCompilers>`_.

Once you have the above compiler installed, the easiest and best supported way 
to install Catalyst in Windows is to use :ref:`Conda <conda>`. If you didn't 
any problems installing the compiler, jump to the :ref:`Conda <conda>` section, 
otherwise keep on reading to troubleshoot the C++ compiler installtion.

Some problems we have encountered installing the **Visual C++ Compiler** 
mentioned above are as follows:

- **The system administrator has set policies to prevent this installation**.
  
  In some systems, there is a default *Windows Software Restriction* policy 
  that prevents the installation of some software packages like this one. 
  You'll have to change the Registry to circumvent this:

  - Click ``Start``, and search for ``regedit`` and launch the 
    ``Registry Editor``
  - Navigate to the following folder:
    ``HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows\Installer``
  - If the last folder does not exist, create it by right-clicking on the 
    parent folder and choosing -> ``New`` -> ``Key`` and typing ``Installer``
  - If there is an entry for ``DisableMSI``, set the Value data to 0.
  - If there is no such entry, click on the ``Edit`` menu -> ``New`` -> 
    ``DWORD (32-bit) Value`` and enter ``DisableMSI`` as the Name (and by 
    default you get 0 as the Value Data)

|

- **The installer has encountered an unexpected error installing this package. 
  This may indicate a problem with this package. The error code is 2503.**

  We have observed this when trying to install a package without enough 
  administrator permissions. Even when you are logged in as an Administrator, 
  you have to explictily install this package with administrator privileges:

  - Click ``Start`` and find ``CMD`` or ``Command Prompt``
  - Right click on it and choose ``Run as administrator``
  - ``cd`` into the folder where you downloaded ``VCForPython27.msi``
  - Run ``msiexec /i VCForPython27.msi``

Updating Catalyst
-----------------

Catalyst is currently in alpha and in under very active development. We release
new minor versions every few days in response to the thorough battle testing 
that our user community puts Catalyst in. As a result, you should expect to 
update Catalyst frequently. Once installed, Catalyst can easily be updated as a 
``pip`` package regardless of the environment used for installation. Make sure 
you activate your environment first as you did in your first install, and then 
execute:

.. code-block:: bash

   $ pip uninstall enigma-catalyst
   $ pip install enigma-catalyst

Alternatively, you could update Catalyst issuing the following command:

.. code-block:: bash

   $ pip install -U enigma-catalyst

but this command will also upgrade all the Catalyst dependencies to the latest 
versions available, and may have unexpected side effects if a newer version of a 
dependency inadvertently breaks some functionality that Catalyst relies on. 
Thus, the first method is the recommended one.

Getting Help
------------

If after following the instructions above, and going through the 
*Troubleshooting* sections, you still experience problems installing Catalyst,
you can seek additional help through the following channels:

- Join our `Catalyst Forum <https://forum.catalystcrypto.io/>`_, and browse a variety
  of topics and conversations around common issues that others face when using
  Catalyst, and how to resolve them. And join the conversation!

- Join our `Discord community <https://discord.gg/SJK32GY>`_, and head over 
  the #catalyst_dev channel where many other users (as well as the project 
  developers) hang out, and can assist you with your particular issue. The 
  more descriptive and the more information you can provide, the easiest will 
  be for others to help you out.

- Report the problem you are experiencing on our 
  `GitHub repository <https://github.com/enigmampc/catalyst/issues>`_ 
  following the guidelines provided therein. Before you do so, take a moment 
  to browse through all `previous reported issues
  <https://github.com/enigmampc/catalyst/issues?utf8=%E2%9C%93&q=is%3Aissue>`_ 
  in the likely case that someone else experienced that same issue before, 
  and you get a hint on how to solve it.


.. _`Debian-derived`: https://www.debian.org/misc/children-distros
.. _`RHEL-derived`: https://en.wikipedia.org/wiki/Red_Hat_Enterprise_Linux_derivatives
.. _`Arch Linux` : https://www.archlinux.org/
.. _`Hitchhiker's Guide to Python` : http://docs.python-guide.org/en/latest/
.. _`Homebrew` : http://brew.sh
