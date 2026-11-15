import sys
import json
import requests

URL = "http://127.0.0.1:8000/audit"

if len(sys.argv) < 2:
    print("Cách dùng: python send_audit.py <file.sol | địa_chỉ> [--record]")
    sys.exit(1)

arg = sys.argv[1]
if arg.endswith(".sol"):
    with open(arg, encoding="utf-8") as f:
        payload = {"code": f.read()}
else:
    payload = {"address": arg}
if "--record" in sys.argv:
    payload["record_on_chain"] = True

r = requests.post(URL, json=payload, timeout=180)
print("HTTP status:", r.status_code)
print(json.dumps(r.json(), indent=2, ensure_ascii=False))