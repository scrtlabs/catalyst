.. image:: https://s3.amazonaws.com/enigmaco-docs/catalyst-crypto.png
    :target: https://enigmampc.github.io/catalyst
    :align: center
    :alt: Enigma | Catalyst

|version tag|
|version status|
|forum|
|discord|
|twitter|

|

Catalyst is an algorithmic trading library for crypto-assets written in Python.
It allows trading strategies to be easily expressed and backtested against 
historical data (with daily and minute resolution), providing analytics and 
insights regarding a particular strategy's performance. Catalyst also supports
live-trading of crypto-assets starting with three exchanges (Bitfinex, Bittrex, 
and Poloniex) with more being added over time. Catalyst empowers users to share 
and curate data and build profitable, data-driven investment strategies. Please 
visit `catalystcrypto.io <https://www.catalystcrypto.io>`_ to learn more about Catalyst.

Catalyst builds on top of the well-established 
`Zipline <https://github.com/quantopian/zipline>`_ project. We did our best to 
minimize structural changes to the general API to maximize compatibility with 
existing trading algorithms, developer knowledge, and tutorials. Join us on the 
`Catalyst Forum <https://forum.catalystcrypto.io/>`_ for questions around Catalyst,
algorithmic trading and technical support. We also have a 
`Discord <https://discord.gg/SJK32GY>`_ group with the *#catalyst_dev* and 
*#catalyst_setup* dedicated channels.

Overview
========

-  Ease of use: Catalyst tries to get out of your way so that you can 
   focus on algorithm development. See 
   `examples of trading strategies <https://github.com/enigmampc/catalyst/tree/master/catalyst/examples>`_ 
   provided.
-  Support for several of the top crypto-exchanges by trading volume:
   `Bitfinex <https://www.bitfinex.com>`_, `Bittrex <http://www.bittrex.com>`_,
   and `Poloniex <https://www.poloniex.com>`_. 
-  Secure: You and only you have access to each exchange API keys for your accounts.
-  Input of historical pricing data of all crypto-assets by exchange, 
   with daily and minute resolution. See 
   `Catalyst Market Coverage Overview <https://www.enigma.co/catalyst/status>`_.
-  Backtesting and live-trading functionality, with a seamless transition
   between the two modes.
-  Output of performance statistics are based on Pandas DataFrames to 
   integrate nicely into the existing PyData eco-system.
-  Statistic and machine learning libraries like matplotlib, scipy, 
   statsmodels, and sklearn support development, analysis, and 
   visualization of state-of-the-art trading systems.
-  Addition of Bitcoin price (btc_usdt) as a benchmark for comparing 
   performance across trading algorithms.

Go to our `Documentation Website <https://enigmampc.github.io/catalyst/>`_.




.. |version tag| image:: https://img.shields.io/pypi/v/enigma-catalyst.svg
   :target: https://pypi.python.org/pypi/enigma-catalyst

.. |version status| image:: https://img.shields.io/pypi/pyversions/enigma-catalyst.svg
   :target: https://pypi.python.org/pypi/enigma-catalyst
   
.. |forum| image:: https://img.shields.io/badge/forum-join-green.svg
   :target: https://forum.catalystcrypto.io/

.. |discord| image:: https://img.shields.io/badge/discord-join%20chat-green.svg
   :target: https://discordapp.com/invite/SJK32GY

.. |twitter| image:: https://img.shields.io/twitter/follow/enigmampc.svg?style=social&label=Follow&style=flat-square
   :target: https://twitter.com/catalystcrypto


