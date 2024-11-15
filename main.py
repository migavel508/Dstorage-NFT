from flask import Flask, render_template, request, jsonify
from web3 import Web3
import requests
import json
import os
from Crypto.Cipher import DES3
from Crypto.Util.Padding import pad
from Crypto.Random import get_random_bytes

app = Flask(__name__)

# Pinata JWT Token (Replace with your actual JWT token)
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySW5mb3JtYXRpb24iOnsiaWQiOiJhNzAwYWJkYi04ZmM4LTQyYWYtYmE4ZS0yMjRmMWM3ZDE0ZGQiLCJlbWFpbCI6ImFpc2h3aW5taWdhdmVsQGdtYWlsLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJwaW5fcG9saWN5Ijp7InJlZ2lvbnMiOlt7ImRlc2lyZWRSZXBsaWNhdGlvbkNvdW50IjoxLCJpZCI6IkZSQTEifSx7ImRlc2lyZWRSZXBsaWNhdGlvbkNvdW50IjoxLCJpZCI6Ik5ZQzEifV0sInZlcnNpb24iOjF9LCJtZmFfZW5hYmxlZCI6ZmFsc2UsInN0YXR1cyI6IkFDVElWRSJ9LCJhdXRoZW50aWNhdGlvblR5cGUiOiJzY29wZWRLZXkiLCJzY29wZWRLZXlLZXkiOiI2OTkyODQyNDc4YWZlMWU2ZmZlZiIsInNjb3BlZEtleVNlY3JldCI6ImY1M2VlNjU0YzNhZThkYjdjZWIxZDZjYzhjOWQ3OTE5YTAxMzI2ZjM3N2Y0MzM2ZTE5YWZmNDE4MDEzMjQ3OTMiLCJleHAiOjE3NTcyNTI2NTR9.R1cMxYnyx5JGbl0Mkq0CoLCvpesfyFBLei1fkpWqKu0"

# Web3 Setup (Use Ganache local URL)
ganache_url = "http://127.0.0.1:7545"  # Default Ganache RPC URL
w3 = Web3(Web3.HTTPProvider(ganache_url))

# Contract details
nft_contract_address = Web3.to_checksum_address('0xfc1a32dfd8a1ddfed55f824cfde72de46194d1cc')  # Replace with your contract address on Ganache

# Load contract ABI from file
with open('NFTManagement_abi.json', 'r') as abi_file:
    nft_contract_abi = json.load(abi_file)

nft_contract = w3.eth.contract(address=nft_contract_address, abi=nft_contract_abi)

# Wallet details (Replace with your wallet details from Ganache)
wallet_address = Web3.to_checksum_address('0x0d23c5A80BA4e8A777Af48713ACf1261c5389434')
private_key = '0x72483e8c7f3fc61407ad4b7f78d9cde0fe29feb237e6f79fc944e2c1b3dea41b'  # Replace with your wallet's private key

# Directory for temporarily storing uploaded files
UPLOAD_DIR = 'uploads'
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 3DES Encryption parameters
secret_key = b'z9\x8c-\xbd\xa5\x84\x00\xefl\x7fl\xb2\xba^<\t\xb3pN\xa7\xbd\x93\xca'  # Must be 24 bytes
iv = get_random_bytes(8)  # DES3 uses an 8-byte IV

# Function to encrypt file using 3DES
def encrypt_file(input_file_path, output_file_path):
    cipher = DES3.new(secret_key, DES3.MODE_CBC, iv)
    with open(input_file_path, 'rb') as file:
        file_data = file.read()
    
    encrypted_data = cipher.encrypt(pad(file_data, DES3.block_size))
    
    with open(output_file_path, 'wb') as enc_file:
        enc_file.write(iv + encrypted_data)  # Write IV + encrypted data to the output file

# Upload file to Pinata
def upload_to_pinata(file_path):
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    headers = {"Authorization": f"Bearer {JWT_TOKEN}"}
    
    with open(file_path, 'rb') as file:
        files = {'file': file}

        response = requests.post(url, headers=headers, files=files)
        if response.status_code == 200:
            return response.json()["IpfsHash"]
        else:
            return None

# Upload and handle the file from the Flutter app
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'}), 400

    # Save the uploaded file
    original_file_path = os.path.join(UPLOAD_DIR, file.filename)
    encrypted_file_path = os.path.join(UPLOAD_DIR, f"enc_{file.filename}")
    file.save(original_file_path)

    # Encrypt the file
    encrypt_file(original_file_path, encrypted_file_path)

    # Upload encrypted file to Pinata
    ipfs_hash = upload_to_pinata(encrypted_file_path)

    if ipfs_hash:
        return jsonify({
            'success': True,
            'filename': file.filename,
            'ipfs_hash': ipfs_hash,
            'successMessage': "File successfully encrypted and uploaded"
        })
    else:
        return jsonify({'success': False, 'message': 'Failed to upload to IPFS'}), 500

# Mint NFT
def mint_nft(owner_address, token_uri):
    nonce = w3.eth.get_transaction_count(wallet_address)
    transaction = nft_contract.functions.mintNFT(owner_address, token_uri).build_transaction({
        'chainId': 1337,  # Default chain ID for Ganache
        'gas': 2000000,
        'gasPrice': w3.to_wei('20', 'gwei'),
        'nonce': nonce,
    })
    signed_txn = w3.eth.account.sign_transaction(transaction, private_key=private_key)
    txn_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    return txn_hash

# Mint NFT after uploading the file
@app.route('/mint', methods=['POST'])
def mint_nft_endpoint():
    owner_address = request.form['owner_address']
    ipfs_hash = request.form['ipfs_hash']
    token_uri = f"https://gateway.pinata.cloud/ipfs/{ipfs_hash}"

    txn_hash = mint_nft(owner_address, token_uri)

    return jsonify({'success': True, 'txn_hash': txn_hash.hex()})

# Transfer NFT ownership (optional, if required)
@app.route('/transfer', methods=['POST'])
def transfer_nft_endpoint():
    from_address = request.form['from_address']
    to_address = request.form['to_address']
    token_id = int(request.form['token_id'])  # Token ID as an integer

    nonce = w3.eth.get_transaction_count(wallet_address)
    transaction = nft_contract.functions.transferNFT(from_address, to_address, token_id).build_transaction({
        'chainId': 1337,  # Default chain ID for Ganache
        'gas': 2000000,
        'gasPrice': w3.to_wei('20', 'gwei'),
        'nonce': nonce,
    })
    signed_txn = w3.eth.account.sign_transaction(transaction, private_key=private_key)
    txn_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)

    return jsonify({'success': True, 'txn_hash': txn_hash.hex()})

# View NFTs owned by a specific address
@app.route('/view_nfts', methods=['GET'])
def view_nfts():
    owner_address = request.args.get('owner_address')

    # Get the number of tokens owned by this address
    balance = nft_contract.functions.balanceOf(owner_address).call()
    
    # Retrieve the token IDs owned by this address
    token_ids = []
    for i in range(balance):
        token_id = nft_contract.functions.tokenOfOwnerByIndex(owner_address, i).call()
        token_ids.append(token_id)

    # Retrieve the token URIs for each token ID
    token_uris = []
    for token_id in token_ids:
        token_uri = nft_contract.functions.tokenURI(token_id).call()
        token_uris.append(token_uri)

    return jsonify({'success': True, 'nfts': token_uris})

# Home route to render the HTML page
@app.route('/')
def index():
    return render_template('index.html')  # Ensure index.html is in the 'templates' folder

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
