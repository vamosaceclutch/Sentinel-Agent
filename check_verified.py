import requests

ADDR = "0x2ABfB402211b16de90c7411434a7E64CC33a5Dc7"
URL = "https://api.routescan.io/v2/network/testnet/evm/43113/etherscan/api"

r = requests.get(
    URL,
    params={"module": "contract", "action": "getsourcecode", "address": ADDR},
    timeout=30,
)
print("HTTP:", r.status_code)
data = r.json()
print("status/message:", data.get("status"), data.get("message"))
res = data.get("result")
if isinstance(res, list) and res:
    item = res[0]
    print("ContractName:", item.get("ContractName"))
    print("CompilerVersion:", item.get("CompilerVersion"))
    print("SourceCode length:", len(item.get("SourceCode") or ""))
else:
    print("result:", str(res)[:300])