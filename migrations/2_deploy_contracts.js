const DataStore = artifacts.require("DataStore");

module.exports = async function (deployer, network, accounts) {
  // Ensure you have valid Ethereum addresses (accounts[0], accounts[1], etc.)
  const signers = [accounts[0], accounts[1], accounts[2]];  // Add more signers as needed
  const requiredSignatures = 2;  // Specify the required number of signatures
  
  // Deploy the contract with the array of signers and the required signatures
  await deployer.deploy(DataStore, signers, requiredSignatures);
};

// truffle compile
// truffle migrate --network development
