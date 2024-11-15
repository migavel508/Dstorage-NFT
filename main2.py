



from flask import Flask, render_template, request, jsonify, send_file
from web3 import Web3
import requests
import json
import os
from Crypto.Cipher import DES3
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import io

app = Flask(__name__)

# Pinata JWT Token (Replace with your actual JWT token)
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySW5mb3JtYXRpb24iOnsiaWQiOiJhNzAwYWJkYi04ZmM4LTQyYWYtYmE4ZS0yMjRmMWM3ZDE0ZGQiLCJlbWFpbCI6ImFpc2h3aW5taWdhdmVsQGdtYWlsLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJwaW5fcG9saWN5Ijp7InJlZ2lvbnMiOlt7ImRlc2lyZWRSZXBsaWNhdGlvbkNvdW50IjoxLCJpZCI6IkZSQTEifSx7ImRlc2lyZWRSZXBsaWNhdGlvbkNvdW50IjoxLCJpZCI6Ik5ZQzEifV0sInZlcnNpb24iOjF9LCJtZmFfZW5hYmxlZCI6ZmFsc2UsInN0YXR1cyI6IkFDVElWRSJ9LCJhdXRoZW50aWNhdGlvblR5cGUiOiJzY29wZWRLZXkiLCJzY29wZWRLZXlLZXkiOiI2OTkyODQyNDc4YWZlMWU2ZmZlZiIsInNjb3BlZEtleVNlY3JldCI6ImY1M2VlNjU0YzNhZThkYjdjZWIxZDZjYzhjOWQ3OTE5YTAxMzI2ZjM3N2Y0MzM2ZTE5YWZmNDE4MDEzMjQ3OTMiLCJleHAiOjE3NTcyNTI2NTR9.R1cMxYnyx5JGbl0Mkq0CoLCvpesfyFBLei1fkpWqKu0"  # Replace with your JWT

# Web3 Setup (Use Ganache local URL or your blockchain provider)
ganache_url = "http://127.0.0.1:7545"  # Default Ganache RPC URL
w3 = Web3(Web3.HTTPProvider(ganache_url))

# Contract details
nft_contract_address = Web3.to_checksum_address('0x1bf063b50ad920b696dc88bb834e3678b24b687f')  # Replace with your contract address
with open('NFTManagement_abi.json', 'r') as abi_file:
    nft_contract_abi = json.load(abi_file)

nft_contract = w3.eth.contract(address=nft_contract_address, abi=nft_contract_abi)

# Wallet details (Replace with your Ganache wallet details)
wallet_address = Web3.to_checksum_address('0x9Db6BE82B4781168111F5eE9D07698ee1809F57c')
private_key = '0x646dfaee5181485a16f2589854c7a100106cd69c95a9c50c0492c0faefecdd86'  # Replace with your wallet's private key

# Directory for temporarily storing uploaded files
UPLOAD_DIR = 'uploads'
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 3DES Encryption parameters
secret_key = b'z9\x8c-\xbd\xa5\x84\x00\xefl\x7fl\xb2\xba^<\t\xb3pN\xa7\xbd\x93\xca'  # Must be exactly 24 bytes
# It's better to load this from an environment variable or secure storage

# Function to encrypt file using 3DES
def encrypt_file(input_file_path, output_file_path):
    iv = get_random_bytes(8)  # DES3 uses an 8-byte IV
    cipher = DES3.new(secret_key, DES3.MODE_CBC, iv)
    with open(input_file_path, 'rb') as file:
        file_data = file.read()
    encrypted_data = cipher.encrypt(pad(file_data, DES3.block_size))
    with open(output_file_path, 'wb') as enc_file:
        enc_file.write(iv + encrypted_data)  # Write IV + encrypted data to the output file

# Function to decrypt file using 3DES
def decrypt_file(encrypted_data):
    iv = encrypted_data[:8]  # Extract the first 8 bytes for IV
    encrypted_content = encrypted_data[8:]
    cipher = DES3.new(secret_key, DES3.MODE_CBC, iv)
    decrypted_data = unpad(cipher.decrypt(encrypted_content), DES3.block_size)
    return decrypted_data

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

# Route for uploading the file from Flutter app, encrypting it, and uploading to IPFS
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

# Function to mint an NFT
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

@app.route('/mint', methods=['POST'])
def mint_nft_endpoint():
    owner_address = request.form.get('owner_address', '0x893fb3f2267D11e7dbE4b19f553158Ee20AF0D52')  # Get from form
    ipfs_hash = request.form['ipfs_hash']  # IPFS hash from form
    token_uri = f"https://gateway.pinata.cloud/ipfs/{ipfs_hash}"

    txn_hash = mint_nft(owner_address, token_uri)
    return jsonify({'success': True, 'txn_hash': txn_hash.hex()})

# Route to transfer NFT ownership (if required)


@app.route('/transfer', methods=['POST'])
def transfer_nft_endpoint():
    try:
        from_address = request.form['from_address']
        to_address = request.form['to_address']
        token_id = request.form['token_id']
        
        # Assuming you have a function to build your transaction
        signed_txn = build_signed_transaction(from_address, to_address, token_id)
        
        txn_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        
        return jsonify({'success': True, 'txn_hash': txn_hash.hex()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})





# Route to view NFTs owned by a particular user
@app.route('/view_nfts', methods=['GET'])
def view_nfts():
    owner_address = '0x893fb3f2267D11e7dbE4b19f553158Ee20AF0D52'
    
    try:
        # Get total supply of NFTs minted so far
        total_supply = nft_contract.functions.totalSupply().call()
    except Exception as e:
        return jsonify({'error': 'Failed to retrieve total supply', 'message': str(e)}), 500

    nfts = []
    for token_id in range(total_supply):
        try:
            token_owner = nft_contract.functions.ownerOf(token_id).call()
            if token_owner.lower() == owner_address.lower():
                token_uri = nft_contract.functions.tokenURI(token_id).call()
                nfts.append({'token_id': token_id, 'token_uri': token_uri})
        except Exception as e:
            return jsonify({'error': f'Failed to retrieve token {token_id}', 'message': str(e)}), 500

    if nfts:
        return render_template('nfts.html', nfts=nfts)
    else:
        return jsonify({'message': 'No NFTs found for the specified owner.'}), 404

# Route to decrypt and serve the file
@app.route('/decrypt/<int:token_id>', methods=['GET'])
def decrypt_file_route(token_id):
    try:
        # Retrieve the token URI from the smart contract
        token_uri = nft_contract.functions.tokenURI(token_id).call()
        
        # Download the encrypted file from IPFS
        response = requests.get(token_uri)
        if response.status_code != 200:
            return jsonify({'success': False, 'message': 'Failed to download file from IPFS'}), 500
        
        encrypted_data = response.content
        
        # Decrypt the file
        decrypted_data = decrypt_file(encrypted_data)
        
        # Optionally, determine the original filename or type
        # For demonstration, we'll name it as decrypted_{token_id}.bin
        decrypted_filename = f"decrypted_{token_id}.bin"
        
        # Serve the decrypted file to the user
        return send_file(
            io.BytesIO(decrypted_data),
            as_attachment=True,
            download_name=decrypted_filename,
            mimetype='application/octet-stream'  # Change as per your file type
        )
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Home route to render the HTML page
@app.route('/')
def index():
    return render_template('index.html')  # Ensure index.html is in the 'templates' folder

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
