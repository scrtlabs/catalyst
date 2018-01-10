var Marketplace = artifacts.require ("Marketplace");

module.exports = function (deployer) {
    deployer.deploy (Marketplace);
};