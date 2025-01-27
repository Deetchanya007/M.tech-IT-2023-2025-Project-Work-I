// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DataStore {
    mapping(bytes32 => string) private dataPointers; // Encrypted value to data pointer (e.g., S3 URL)
    mapping(bytes32 => mapping(address => bool)) public signatures; // For multi-signature query verification
    address[] public signers; // List of signers' addresses
    uint256 public requiredSignatures; // Number of required signatures for verification

    event DataStored(bytes32 indexed encryptedValue, string dataPointer);
    event QueryVerified(bytes32 indexed encryptedValue, bool isVerified);

    modifier onlySigner() {
        bool isSigner = false;
        for (uint256 i = 0; i < signers.length; i++) {
            if (msg.sender == signers[i]) {
                isSigner = true;
                break;
            }
        }
        require(isSigner, "Not an authorized signer");
        _;
    }

    constructor(address[] memory _signers, uint256 _requiredSignatures) {
        require(_signers.length > 0, "Signers required");
        require(
            _requiredSignatures > 0 && _requiredSignatures <= _signers.length,
            "Invalid required signatures"
        );
        signers = _signers;
        requiredSignatures = _requiredSignatures;
    }

    // Store encrypted data along with its pointer (S3 URL or metadata)
    function storeData(bytes32 encryptedValue, string memory dataPointer) public {
        require(bytes(dataPointer).length > 0, "Data pointer cannot be empty.");
        require(bytes(dataPointers[encryptedValue]).length == 0, "Data already exists.");
        dataPointers[encryptedValue] = dataPointer;
        emit DataStored(encryptedValue, dataPointer);
    }

    // Get the data pointer for the encrypted value
    function getData(bytes32 encryptedValue) public view returns (string memory) {
        require(bytes(dataPointers[encryptedValue]).length > 0, "Data not found.");
        return dataPointers[encryptedValue];
    }

    // Store signature for a specific query (multi-signature mechanism)
    function storeSignature(bytes32 encryptedValue) public onlySigner {
        require(bytes(dataPointers[encryptedValue]).length > 0, "Data not found.");
        require(!signatures[encryptedValue][msg.sender], "Signature already stored.");
        signatures[encryptedValue][msg.sender] = true;
    }

    // Verify if a query has enough signatures
    function verifyQuery(bytes32 encryptedValue) public view returns (bool) {
        uint256 signatureCount = 0;
        for (uint256 i = 0; i < signers.length; i++) {
            if (signatures[encryptedValue][signers[i]]) {
                signatureCount++;
            }
        }
        return signatureCount >= requiredSignatures;
    }

    // Reset signatures for a specific query (for a new query)
    function resetSignatures(bytes32 encryptedValue) public onlySigner {
        require(bytes(dataPointers[encryptedValue]).length > 0, "Data not found.");
        for (uint256 i = 0; i < signers.length; i++) {
            signatures[encryptedValue][signers[i]] = false;
        }
    }
}
