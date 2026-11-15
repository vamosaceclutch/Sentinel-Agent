"""Backend tests with a fake Gemini: no network, no API quota, no gas.

Run from anywhere:  python tests/test_backend.py   (needs: pip install -r requirements-dev.txt)
"""
import json, os, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)  # chain.py reads abi.json from the current folder
os.environ["GEMINI_API_KEY"] = "fake"
os.environ["GEMINI_FALLBACK_MODEL"] = "fallback-model"
sys.path.insert(0, str(ROOT))
import audit
from google.genai import errors as ge
from fastapi.testclient import TestClient
import app as appmod

ok = True
def expect(label, cond):
    global ok; ok &= bool(cond); print(("PASS  " if cond else "FAIL  ") + label)

class R:  # fake response
    def __init__(self, text): self.text = text; self.candidates = []; self.prompt_feedback = None

calls = []
fail_main = {"on": False}
def fake_generate_content(model, contents, config):
    calls.append(model)
    if fail_main["on"] and model == audit.MODEL:
        raise ge.ServerError(503, {"error": {"message": "busy", "status": "UNAVAILABLE"}})
    if "Fix this Solidity contract" in contents:
        return R(json.dumps({"patched_code": "pragma solidity ^0.8.20;\ncontract Fixed { }", "changes": ["added guard"]}))
    if "(patched)" in contents:
        return R(json.dumps({"summary": "clean", "findings": []}))
    return R(json.dumps({"summary": "two issues", "findings": [
        {"title": "Reentrancy", "severity": "HIGH ", "function": "withdraw", "description": "d", "recommendation": "r"},
        {"title": "Zero check", "severity": "low", "function": "ctor", "description": "d", "recommendation": "r"},
        {"title": "weird", "severity": "banana", "function": "x", "description": "d", "recommendation": "r"}]}))

class FakeClient:
    def __init__(self, api_key=None):
        self.models = self
    generate_content = staticmethod(fake_generate_content)
audit.genai.Client = FakeClient
audit.time.sleep = lambda s: None
c = TestClient(appmod.app)

# ---- scoring
sc = audit.compute_score
expect("score: sach = 100", sc([]) == 100)
expect("score: 1 high = 65", sc([{"severity": "high"}]) == 65)
expect("score: 5 critical = 3, khong bi ket o 0", sc([{"severity": "critical"}] * 5) == 3)
expect("score: nang hon thi thap hon (don dieu)", sc([{"severity": "critical"}] * 3) > sc([{"severity": "critical"}] * 4))

# ---- /audit (code mode)
r = c.post("/audit", json={"code": "contract A {}"})
d = r.json()
expect("/audit 200", r.status_code == 200)
expect("severity duoc chuan hoa (HIGH -> high, banana -> info)", [f["severity"] for f in d["findings"]] == ["high", "low", "info"])
expect("diem = 100*0.5^(28/40) = 62", d["score"] == 62)
expect("ghi nhan model da cham", d["model"] == audit.MODEL)
expect("truncated = False voi code ngan", d["truncated"] is False and d["source_chars"] == len("contract A {}"))
big = "// x\n" * 20000
d2 = c.post("/audit", json={"code": big}).json()
expect("truncated = True voi code qua dai", d2["truncated"] is True)

# ---- fallback
fail_main["on"] = True; calls.clear()
d3 = c.post("/audit", json={"code": "contract A {}"}).json()
expect("model chinh 503 -> chuyen sang du phong", d3.get("model") == "fallback-model")
fail_main["on"] = False

# ---- /patch
f = d["findings"]
r = c.post("/patch", json={"code": "contract A {}", "findings": f})
p = r.json()
expect("/patch 200", r.status_code == 200)
expect("co patched_code va changes", "contract Fixed" in p["patched_code"] and p["changes"] == ["added guard"])
expect("score_before = 62, score_after = 100", p["score_before"] == 62 and p["score_after"] == 100)
expect("/patch khong co findings -> 400", c.post("/patch", json={"code": "contract A {}", "findings": []}).status_code == 400)
expect("/patch gui ca address va code -> 400", c.post("/patch", json={"address": "0x" + "1" * 40, "code": "x", "findings": f}).status_code == 400)
expect("/patch code qua dai -> 400", c.post("/patch", json={"code": "x" * 25000, "findings": f}).status_code == 400)
expect("/patch findings > 30 -> 422", c.post("/patch", json={"code": "x", "findings": [{}] * 31}).status_code == 422)

# ---- loi tu dich vu AI
def boom(model, contents, config): raise ge.ClientError(400, {"error": {"message": "bad key", "status": "INVALID"}})
FakeClient.generate_content = staticmethod(boom)
expect("loi AI -> 502 (khong 500)", c.post("/audit", json={"code": "contract A {}"}).status_code == 502)

# ---- chain.summarize_receipt
import chain
rc = {"gasUsed": 120000, "effectiveGasPrice": 25 * 10**9, "blockNumber": 77}
s = chain.summarize_receipt(rc, 1.2345)
expect("receipt: phi = 120000 * 25 gwei = 0.003 AVAX", abs(s["fee_avax"] - 0.003) < 1e-12 and s["gas_used"] == 120000 and s["confirm_seconds"] == 1.23 and s["block_number"] == 77)

# ---- hash on dinh voi truong moi
h1 = chain.hash_report(d); h2 = chain.hash_report(json.loads(json.dumps(d)))
expect("hash bao cao on dinh khi di qua JSON", h1 == h2)

print("\nALL PASS" if ok else "\nCO LOI"); sys.exit(0 if ok else 1)
