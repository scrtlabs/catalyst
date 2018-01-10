pragma solidity ^0.4.17;

import "truffle/Assert.sol";
import "truffle/DeployedAddresses.sol";
import "../contracts/Marketplace.sol";

contract TestMarketplace {
    Marketplace marketplace = Marketplace(DeployedAddresses.Marketplace());

    // Testing the adopt() function
    function testUserCanSubscribe() public {
        uint returnedId = marketplace.subscribe(2);

        uint expected = 2;

        Assert.equal(returnedId, expected, "Adoption of pet ID 8 should be recorded.");
    }

    // Testing retrieval of a single pet's owner
    function testGetSubscriberAddressByDataSourceId() public {
        // Expected owner is this contract
        address expected = this;

        address adopter = marketplace.subscribers(2);

        Assert.equal(adopter, expected, "Owner of data source ID 0 should be recorded.");
    }

    // Testing retrieval of all pet owners
    function testGetSubscriberAddressByDataSourceIdInArray() public {
        // Expected owner is this contract
        address expected = this;

        // Store adopters in memory rather than contract's storage
        address[16] memory subscribers = marketplace.getSubscribers();

        Assert.equal(subscribers[2], expected, "Owner of pet ID 2 should be recorded.");
    }
}