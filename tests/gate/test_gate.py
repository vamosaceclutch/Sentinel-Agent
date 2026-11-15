import json, sys
from pathlib import Path
from web3 import Web3, EthereumTesterProvider
from eth_tester import EthereumTester

evm = sys.argv[1]
c = json.load(open(Path(__file__).with_name(f"compiled_{evm}.json")))
t = EthereumTester()
w3 = Web3(EthereumTesterProvider(t))
owner, agent, other = w3.eth.accounts[0], w3.eth.accounts[1], w3.eth.accounts[2]
target = "0x000000000000000000000000000000000000dEaD"

def deploy(name, *args):
    k = w3.eth.contract(abi=c[name]["abi"], bytecode=c[name]["bin"])
    h = k.constructor(*args).transact({"from": owner})
    r = w3.eth.wait_for_transaction_receipt(h)
    return w3.eth.contract(address=r.contractAddress, abi=c[name]["abi"])

reg = deploy("SentinelRegistry", agent)
gate = deploy("AuditGate", reg.address, 70, 30 * 24 * 3600)
pad = deploy("GuardedLaunchpad", gate.address)
VERDICT = ["NotAudited", "ScoreTooLow", "Expired", "Safe"]
ok = True

def expect(label, cond):
    global ok
    ok &= bool(cond)
    print(("PASS  " if cond else "FAIL  ") + label)

def stamp(score, sender=None):
    h = reg.functions.recordAudit(target, score, b"\x11" * 32).transact({"from": sender or agent})
    w3.eth.wait_for_transaction_receipt(h)

def reverts(fn):
    try:
        fn.call({"from": other}); return None
    except Exception as e:
        return str(e)

# 1. chua audit
v, s, ts = gate.functions.check(target).call()
expect("chua audit -> NotAudited, khong revert", VERDICT[v] == "NotAudited" and s == 0)
expect("chua audit -> isSafe = false", gate.functions.isSafe(target).call() is False)
err = reverts(pad.functions.listProject(target))
expect("chua audit -> listProject bi chan (NotSafe)", err is not None)

# 2. diem thap
stamp(40)
v, s, ts = gate.functions.check(target).call()
expect("diem 40 -> ScoreTooLow", VERDICT[v] == "ScoreTooLow" and s == 40)
expect("diem 40 -> isSafe = false", gate.functions.isSafe(target).call() is False)
expect("diem 40 -> listProject bi chan", reverts(pad.functions.listProject(target)) is not None)

# 3. diem cao (audit moi nhat duoc dung)
stamp(95)
v, s, ts = gate.functions.check(target).call()
expect("sau khi vá, diem 95 -> Safe", VERDICT[v] == "Safe" and s == 95)
expect("diem 95 -> isSafe = true", gate.functions.isSafe(target).call() is True)
h = pad.functions.listProject(target).transact({"from": other})
w3.eth.wait_for_transaction_receipt(h)
expect("diem 95 -> listProject thanh cong", pad.functions.listedCount().call() == 1)
expect("lich su giu du 2 lan audit", reg.functions.auditCount(target).call() == 2)

# 4. het han sau 30 ngay
now = w3.eth.get_block("latest")["timestamp"]
t.time_travel(now + 31 * 24 * 3600); t.mine_blocks(1)
v, s, ts = gate.functions.check(target).call()
expect("31 ngay sau -> Expired", VERDICT[v] == "Expired")
expect("het han -> isSafe = false", gate.functions.isSafe(target).call() is False)

# 5. chi agent duoc ghi
err = None
try:
    reg.functions.recordAudit(target, 100, b"\x22" * 32).call({"from": other})
except Exception as e:
    err = str(e)
expect("khong phai agent -> recordAudit bi tu choi", err is not None and "not agent" in err)

# 6. audit moi thap hon lam mat qua cong
stamp(50)
v, s, ts = gate.functions.check(target).call()
expect("audit moi 50 ghi de ket luan cu -> ScoreTooLow", VERDICT[v] == "ScoreTooLow")

# 7. tham so khong hop le
try:
    deploy("AuditGate", reg.address, 101, 0); bad = False
except Exception:
    bad = True
expect("minScore > 100 bi tu choi khi deploy", bad)

print("\nALL PASS" if ok else "\nCO LOI")
sys.exit(0 if ok else 1)
