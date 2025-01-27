from flask import Flask, render_template, request, jsonify
from web3 import Web3
import boto3
import hashlib
import json

app = Flask(__name__)

# Ganache Connection
ganache_url = "http://127.0.0.1:7545"
web3 = Web3(Web3.HTTPProvider(ganache_url))
if not web3.is_connected():
    print("Failed to connect to Ganache")
    exit()
web3.eth.default_account = web3.eth.accounts[0]

# Contract ABI and Address
truffle_build_path = './build/contracts/DataStore.json'
with open(truffle_build_path) as file:
    contract_json = json.load(file)
    contract_abi = contract_json['abi']
    contract_address = contract_json['networks']['5777']['address']
contract = web3.eth.contract(address=contract_address, abi=contract_abi)

# AWS S3 Config
AWS_ACCESS_KEY = ''
AWS_SECRET_KEY = ''
AWS_BUCKET_NAME = ''

s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)

# Utility Functions
def to_bytes32(num):
    if num < 0 or num >= 2**256:
        raise ValueError(f"Numeric value {num} exceeds bytes32 range.")
    return num.to_bytes(32, byteorder='big')

def text_to_numeric(text):
    text_hash = hashlib.sha256(text.encode()).hexdigest()
    return int(text_hash, 16)

def caesar_cipher_encrypt(text, shift):
    encrypted_text = []
    for char in text:
        if char.isalpha():
            shift_base = ord('A') if char.isupper() else ord('a')
            encrypted_char = chr((ord(char) - shift_base + shift) % 26 + shift_base)
            encrypted_text.append(encrypted_char)
        else:
            encrypted_text.append(char)
    return ''.join(encrypted_text)

def verify_signatures(data_hash):
    # Define the first 5 nodes to be signed
    nodes = web3.eth.accounts[:5]
    signature_status = {}
    all_signed = True  # Assume all nodes sign unless proven otherwise
    
    # Iterate through the nodes to check if each has signed
    for node in nodes:
        try:
            # Check if this node has signed the data
            is_signed = contract.functions.signatures(data_hash, node).call()
            if is_signed:
                signature_status[node] = "Node signed the data"
            else:
                # If not signed, sign it
                tx_hash = contract.functions.storeSignature(data_hash).transact({'from': node})
                web3.eth.wait_for_transaction_receipt(tx_hash)
                signature_status[node] = "Node signed the data"
        except Exception as e:
            signature_status[node] = "Node not authorized to sign"
            all_signed = False  # If any node doesn't sign, set all_signed to False
    
    # Check if all 5 nodes have signed
    if all_signed:
        print("All nodes signed the data.")
    else:
        print("Some nodes have not signed the data.")
    
    # Log the signature status for each node
    for node, status in signature_status.items():
        print(f"{node}: {status}")

    return signature_status


def upload_to_s3(file_name, file_data):
    try:
        s3_client.put_object(Bucket=AWS_BUCKET_NAME, Key=file_name, Body=file_data)
        s3_pointer = f"s3://{AWS_BUCKET_NAME}/{file_name}"
        print(f"File uploaded successfully to {s3_pointer}")
        return s3_pointer
    except Exception as e:
        print(f"Error uploading to S3: {str(e)}")
        raise

# Flask Routes
@app.route('/store_text_ope', methods=['POST'])
def store_text_ope():
    user_data = request.form.get('user_data', '')
    if not user_data:
        return jsonify({"error": "Missing 'user_data' in form."}), 400
    try:
        shift = 3
        encrypted_data = caesar_cipher_encrypt(user_data, shift)
        numeric_representation = text_to_numeric(encrypted_data)
        encrypted_value_bytes32 = to_bytes32(numeric_representation)

        tx_hash = contract.functions.storeData(encrypted_value_bytes32, encrypted_data).transact()
        web3.eth.wait_for_transaction_receipt(tx_hash)

        print(f"Data stored on-chain: {user_data} (Encrypted with Caesar Cipher)")

        signature_status = verify_signatures(encrypted_value_bytes32)

        return jsonify({
            "message": "Data encrypted and stored on-chain.",
            "signature_status": signature_status
        })
    except Exception as e:
        print(f"Error storing data: {str(e)}")
        if "Data already exists" in str(e):
            return jsonify({"message": "Data already exists."})
        return jsonify({"error": "An error occurred during data storage."}), 400

@app.route('/search_text', methods=['POST'])
def search_text():
    search_word = request.form.get('search_word', '')
    if not search_word:
        return jsonify({"error": "Missing 'search_word' in form."}), 400
    try:
        shift = 3
        encrypted_search_word = caesar_cipher_encrypt(search_word, shift)
        numeric_search_key = text_to_numeric(encrypted_search_word)
        encrypted_search_key_bytes32 = to_bytes32(numeric_search_key)

        print(f"Initiating search operation for hashed input: {encrypted_search_key_bytes32.hex()}")

        stored_data_pointer = contract.functions.getData(encrypted_search_key_bytes32).call()

        signature_status = verify_signatures(encrypted_search_key_bytes32)

        return jsonify({
            "message": "Data found on-chain.",
            "pointer": stored_data_pointer,
            "signature_status": signature_status
        })
    except Exception as e:
        print(f"Error searching for data: {str(e)}")
        if "Data not found" in str(e):
            return jsonify({"message": "Data not found."})
        return jsonify({"error": "An error occurred during the search."}), 404

@app.route('/store_image', methods=['POST'])
def store_image():
    image_file = request.files.get('image_file')
    if not image_file:
        return jsonify({"error": "Missing 'image_file' in form."}), 400
    try:
        file_name = f"image_{hashlib.sha256(image_file.read()).hexdigest()[:10]}.jpg"
        image_file.seek(0)
        s3_pointer = upload_to_s3(file_name, image_file.read())

        metadata_hash = text_to_numeric(s3_pointer)
        encrypted_metadata_bytes32 = to_bytes32(metadata_hash)

        tx_hash = contract.functions.storeData(encrypted_metadata_bytes32, "Image Metadata Encrypted").transact()
        web3.eth.wait_for_transaction_receipt(tx_hash)

        return jsonify({
            "message": "Image stored off-chain.",
            "s3_pointer": s3_pointer
        }), 200
    except Exception as e:
        print(f"Error storing image: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
