This module contains smart contracts for the data marketplace.
It was generated with Truffle. Truffle can be used to compile and test
the smart contracts. It's being tested on a test blockhain using Ganache.

Steps to test:
* Download and run Ganache
* Ensure that your Ganache endpoint matches `truffle.js`
* In this `marketplace` folder, run the following commands:
    * `truffle compile`
    * `truffle test`
    * `truffle migrate --reset`
    * `truffle console`
    * From the console: `Marketplace.deployed()`
* The deployed method displays info about the deployed smart contract
including its address. Copy/paste the address into 
`catalyst/marketplace/marketplace.py`.
* Run the catalyst marketplace unit tests: 
`tests/marketplace/test_marketplace.py`
