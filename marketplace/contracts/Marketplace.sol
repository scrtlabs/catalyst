pragma solidity ^0.4.17;

contract Marketplace {
    address[16] public subscribers;

    // Adopting a pet
    function subscribe(uint dataSourceId) public returns (uint) {
        require(dataSourceId >= 0 && dataSourceId <= 5);

        subscribers[dataSourceId] = msg.sender;

        return dataSourceId;
    }

    // Retrieving the subscribers
    function getSubscribers() public view returns (address[16]) {
        return subscribers;
    }
}