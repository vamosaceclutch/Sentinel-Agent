import requests

ADDR = "0x2ABfB402211b16de90c7411434a7E64CC33a5Dc7"
r = requests.get(
    f"https://sourcify.dev/server/v2/contract/43113/{ADDR}",
    params={"fields": "sources"},
    timeout=30,
)
print("HTTP:", r.status_code)
if r.ok:
    d = r.json()
    print("match:", d.get("match"))
    print("files:", list((d.get("sources") or {}).keys()))
else:
    print(r.text[:300])