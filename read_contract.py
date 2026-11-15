import json
from web3 import Web3

RPC = "https://api.avax-test.network/ext/bc/C/rpc"
ADDRESS = "0x2ABfB402211b16de90c7411434a7E64CC33a5Dc7"

w3 = Web3(Web3.HTTPProvider(RPC))
abi = json.load(open("abi.json"))
c = w3.eth.contract(address=ADDRESS, abi=abi)
print("chain id:", w3.eth.chain_id)
print("owner:", c.functions.owner().call())
print("agent:", c.functions.agent().call())