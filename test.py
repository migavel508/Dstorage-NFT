from web3 import Web3

# Replace with your actual Web3 provider URL (e.g., Infura, Alchemy, or local node)
provider_url = "https://polygon-amoy.infura.io/v3/d46a139017234ecd8352b263fa61f489"

web3 = Web3(Web3.HTTPProvider(provider_url))

# Check if connected
if web3.is_connected():
    print("Connected to Ethereum node!")
else:
    print("Failed to connect to Ethereum node.")
