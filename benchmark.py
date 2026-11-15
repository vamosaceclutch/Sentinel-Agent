"""
benchmark.py - chay thu SentinelAgent tren cac contract mau co loi da biet.

Cach dung (backend phai dang chay o cong 8000):
    python benchmark.py                 # chay 1 lan moi contract
    python benchmark.py 3               # chay 3 lan, de do do lech giua cac lan
    python benchmark.py 3 after         # chay 3 lan va luu vao benchmark_after.json

Ket qua: in bang ra man hinh va luu benchmark_<nhan>.json (mac dinh nhan = results).
Tieu chi: contract co loi -> "bat duoc" neu bao cao nhac den tu khoa cua loi do.
Contract SAFE -> dat neu diem >= 80 (do kha nang bao dong nham).
"""
import json
import os
import sys
import time

import requests

API = "http://127.0.0.1:8000/audit"
PAUSE = int(os.getenv("BENCH_PAUSE", "5"))  # giay nghi giua cac lan goi de tranh loi 429
RETRY_WAIT = 25  # neu gap loi tam thoi (429/502/503), doi roi thu lai 1 lan

CASES = [
    {
        "name": "reentrancy",
        "keywords": ["reentran"],
        "code": """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract ReentrancyBank {
    mapping(address => uint256) public balances;
    function deposit() external payable { balances[msg.sender] += msg.value; }
    function withdraw() external {
        uint256 amount = balances[msg.sender];
        require(amount > 0, "no balance");
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "send failed");
        balances[msg.sender] = 0;
    }
}
""",
    },
    {
        "name": "tx.origin",
        "keywords": ["tx.origin"],
        "code": """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract TxOriginWallet {
    address public owner;
    constructor() { owner = msg.sender; }
    receive() external payable {}
    function transferTo(address payable to, uint256 amount) external {
        require(tx.origin == owner, "not owner");
        to.transfer(amount);
    }
}
""",
    },
    {
        "name": "missing access control",
        "keywords": ["access control", "anyone", "unauthorized", "onlyowner", "permission"],
        "code": """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract OpenVault {
    address public owner;
    constructor() { owner = msg.sender; }
    receive() external payable {}
    function setOwner(address newOwner) external { owner = newOwner; }
    function withdrawAll() external { payable(msg.sender).transfer(address(this).balance); }
}
""",
    },
    {
        "name": "selfdestruct",
        "keywords": ["selfdestruct"],
        "code": """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract Killable {
    address public owner;
    constructor() { owner = msg.sender; }
    function destroy() external { selfdestruct(payable(msg.sender)); }
}
""",
    },
    {
        "name": "delegatecall",
        "keywords": ["delegatecall"],
        "code": """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract Proxy {
    address public owner;
    constructor() { owner = msg.sender; }
    function execute(address target, bytes calldata data) external {
        (bool ok, ) = target.delegatecall(data);
        require(ok, "failed");
    }
}
""",
    },
    {
        "name": "unchecked call",
        "keywords": ["unchecked", "return value", "return-value", "ignored"],
        "code": """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract Payout {
    mapping(address => uint256) public owed;
    function credit(address user) external payable { owed[user] += msg.value; }
    function pay() external {
        uint256 amount = owed[msg.sender];
        owed[msg.sender] = 0;
        payable(msg.sender).call{value: amount}("");
    }
}
""",
    },
    {
        "name": "weak randomness",
        "keywords": ["random", "timestamp", "predictable", "prevrandao"],
        "code": """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract Lottery {
    address[] public players;
    function enter() external payable {
        require(msg.value == 0.1 ether, "need 0.1");
        players.push(msg.sender);
    }
    function draw() external {
        uint256 i = uint256(keccak256(abi.encodePacked(block.timestamp, block.prevrandao))) % players.length;
        payable(players[i]).transfer(address(this).balance);
    }
}
""",
    },
    {
        "name": "oracle manipulation",
        "keywords": ["oracle", "manipul", "spot price", "flash"],
        "code": """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
interface IPair { function getReserves() external view returns (uint112, uint112, uint32); }
interface IToken {
    function transfer(address to, uint256 amt) external returns (bool);
    function transferFrom(address from, address to, uint256 amt) external returns (bool);
}
contract SpotLender {
    IPair public pair;
    IToken public collateral;
    IToken public stable;
    mapping(address => uint256) public collateralOf;
    constructor(IPair p, IToken c, IToken s) { pair = p; collateral = c; stable = s; }
    function price() public view returns (uint256) {
        (uint112 r0, uint112 r1, ) = pair.getReserves();
        return uint256(r1) * 1e18 / uint256(r0);
    }
    function deposit(uint256 amt) external {
        collateral.transferFrom(msg.sender, address(this), amt);
        collateralOf[msg.sender] += amt;
    }
    function borrow(uint256 amt) external {
        require(collateralOf[msg.sender] * price() / 1e18 >= amt * 2, "undercollateralized");
        stable.transfer(msg.sender, amt);
    }
}
""",
    },
    {
        "name": "SAFE control",
        "keywords": None,  # contract sach: dat neu diem >= 80
        "code": """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract SafeBank {
    address public immutable owner;
    mapping(address => uint256) public balances;
    bool private locked;
    modifier nonReentrant() { require(!locked, "locked"); locked = true; _; locked = false; }
    constructor(address _owner) {
        require(_owner != address(0), "zero owner");
        owner = _owner;
    }
    function deposit() external payable { balances[msg.sender] += msg.value; }
    function withdraw() external nonReentrant {
        uint256 amount = balances[msg.sender];
        require(amount > 0, "no balance");
        balances[msg.sender] = 0;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "send failed");
    }
}
""",
    },
]


def run_once(case):
    for attempt in range(2):
        try:
            r = requests.post(API, json={"code": case["code"]}, timeout=240)
        except requests.RequestException as e:
            return {"error": str(e)}
        if r.status_code == 200:
            return r.json()
        err = {"error": f"HTTP {r.status_code}: {r.text[:300]}"}
        if r.status_code in (429, 502, 503) and attempt == 0:
            time.sleep(RETRY_WAIT)  # loi tam thoi cua dich vu AI: thu lai
            continue
        return err
    return err


def judge(case, result):
    if "error" in result:
        return False, None
    score = result.get("score")
    if case["keywords"] is None:
        return (score is not None and score >= 80), score
    text = json.dumps(result.get("findings", result), ensure_ascii=False).lower()
    return any(k in text for k in case["keywords"]), score


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    label = sys.argv[2] if len(sys.argv) > 2 else "results"
    rows = []
    for case in CASES:
        outcomes, scores, errors, models = [], [], [], []
        for n in range(runs):
            result = run_once(case)
            ok, score = judge(case, result)
            outcomes.append(ok)
            scores.append(score)
            errors.append(result.get("error"))
            models.append(result.get("model"))
            err = result.get("error")
            print(f"  {case['name']} lan {n + 1}: {'OK' if ok else ('ERROR' if err else 'MISS')} score={score}" + (f" ({err})" if err else ""))
            time.sleep(PAUSE)
        rows.append({"name": case["name"], "pass": outcomes, "scores": scores, "errors": errors, "models": models})

    print()
    print(f"{'contract':<24}{'dat':<10}{'diem cac lan'}")
    print("-" * 56)
    total = 0
    for row in rows:
        passed = sum(row["pass"])
        total += passed
        print(f"{row['name']:<24}{passed}/{runs:<8}{row['scores']}")
    print("-" * 56)
    print(f"Tong: {total}/{len(rows) * runs}")
    n_err = sum(1 for row in rows for e in row["errors"] if e)
    if n_err:
        print(f"Co {n_err} lan loi (khong phai bo sot): xem truong 'errors' trong file ket qua.")

    out = f"benchmark_{label}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"Da luu {out}")


if __name__ == "__main__":
    main()
