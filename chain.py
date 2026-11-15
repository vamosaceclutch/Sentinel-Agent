import os
import json
import time
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

RPC = "https://api.avax-test.network/ext/bc/C/rpc"
REGISTRY = "0x2ABfB402211b16de90c7411434a7E64CC33a5Dc7"

w3 = Web3(Web3.HTTPProvider(RPC))
with open("abi.json", encoding="utf-8") as f:
    abi = json.load(f)
contract = w3.eth.contract(address=Web3.to_checksum_address(REGISTRY), abi=abi)


def hash_report(report: dict) -> bytes:
    """Dấu vân tay 32 byte của báo cáo (JSON chuẩn hóa)."""
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False)
    return Web3.keccak(text=canonical)


def summarize_receipt(receipt, seconds: float) -> dict:
    """Real numbers measured on Avalanche for one stamp: gas, fee in AVAX, time."""
    fee_wei = int(receipt["gasUsed"]) * int(receipt["effectiveGasPrice"])
    return {
        "block_number": int(receipt["blockNumber"]),
        "gas_used": int(receipt["gasUsed"]),
        "fee_avax": float(Web3.from_wei(fee_wei, "ether")),
        "confirm_seconds": round(seconds, 2),
    }


def record_on_chain(target: str, score: int, report: dict) -> dict:
    key = os.getenv("AGENT_PRIVATE_KEY")
    if not key:
        raise RuntimeError("Thiếu AGENT_PRIVATE_KEY trong .env")
    agent = w3.eth.account.from_key(key)

    report_hash = hash_report(report)
    tx = contract.functions.recordAudit(
        Web3.to_checksum_address(target), int(score), report_hash
    ).build_transaction({
        "from": agent.address,
        "nonce": w3.eth.get_transaction_count(agent.address),
        "chainId": 43113,
    })

    started = time.monotonic()
    signed = agent.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    if receipt.status != 1:
        raise RuntimeError("Giao dịch bị revert")
    return {
        "tx_hash": tx_hash.hex(),
        "report_hash": report_hash.hex(),
        "explorer": f"https://testnet.snowtrace.io/tx/0x{tx_hash.hex().removeprefix('0x')}",
        **summarize_receipt(receipt, time.monotonic() - started),
    }


if __name__ == "__main__":
    # Test nhanh: ghi một audit thử cho SafeVault giả định
    demo_target = "0x000000000000000000000000000000000000dEaD"
    demo_report = {"summary": "test", "findings": []}
    print(record_on_chain(demo_target, 100, demo_report))

    count = contract.functions.auditCount(
        Web3.to_checksum_address(demo_target)).call()
    print("Số audit đã ghi cho địa chỉ này:", count)
    print("Audit mới nhất:", contract.functions.latestAudit(
        Web3.to_checksum_address(demo_target)).call())