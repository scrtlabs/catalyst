pragma solidity ^0.4.17;

import "truffle/Assert.sol";
import "truffle/DeployedAddresses.sol";
import "../contracts/Marketplace.sol";

contract TestMarketplace {
    Marketplace marketplace = Marketplace(DeployedAddresses.Marketplace());

    // Testing the subscribe() function
    function testUserCanSubscribe() public {
        uint returnedId = marketplace.subscribe(2);

        uint expected = 2;

        Assert.equal(returnedId, expected, "Data source 2 should be recorded.");
    }

    // Testing retrieval of a single subscriber
    function testGetSubscriberAddressByDataSourceId() public {
        // Expected owner is this contract
        address expected = this;

        address subscriber = marketplace.subscribers(2);

        Assert.equal(subscriber, expected, "Subscriber of data source ID 2 should be recorded.");
    }

    // Testing retrieval of all subscribers
    function testGetSubscriberAddressByDataSourceIdInArray() public {
        // Expected subscriber is this contract
        address expected = this;

        // Store subscribers in memory rather than contract's storage
        address[16] memory subscribers = marketplace.getSubscribers();

        Assert.equal(subscribers[2], expected, "Subscriber of data source 2 should be recorded.");
    }
}