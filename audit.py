"""SentinelAgent - audit core.

Usage:  python audit.py 0xContractAddressOnFuji      (verified contracts)
        python audit.py samples/Contract.sol          (local Solidity file)
Flow:   source -> Gemini findings -> score 0..100
"""
import json
import os
import sys
import time

import requests
from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from web3 import Web3

load_dotenv()

ROUTESCAN_URL = "https://api.routescan.io/v2/network/testnet/evm/43113/etherscan/api"
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "")  # optional second model
RETRY_STATUS = {429, 500, 502, 503, 504}  # busy / temporary errors worth retrying
MAX_SOURCE_CHARS = 60_000  # keep the prompt small enough for the free tier

# Penalty points for each finding, by severity.
PENALTY = {"critical": 40, "high": 25, "medium": 10, "low": 3, "info": 0}
# Every 40 penalty points cut the score in half: it keeps falling but never
# gets stuck at 0, so "very bad" and "terrible" stay different numbers.
SCORE_HALF_LIFE = 40

SYSTEM_PROMPT = """You are a smart contract code reviewer for a defensive security tool.
Users submit a Solidity contract before deploying it, or before trusting it with
their funds, and you write a safety review that helps them fix problems or decide
not to interact with it. Your job is review and remediation only: never write
exploit code or attack steps.

Review the code for these risk categories: reentrancy (state updated after an
external call), unchecked results of low-level calls, missing access control on
functions that move funds or change ownership or privileged settings, dangerous
token approval patterns, selfdestruct, delegatecall to arbitrary addresses,
tx.origin used for authorization, unbounded loops, arithmetic inside unchecked
blocks, and owner-only privileges that let one account move or freeze user funds
(centralization risk). Also look for: prices read from the current reserves of a
single AMM pool (spot-price manipulation), randomness taken from block.timestamp,
block.prevrandao or blockhash, critical logic that depends on block.timestamp,
missing zero-address checks on privileged settings, unprotected initializer or
upgrade functions, replayable signatures, token transfers whose return value is
ignored, and missing slippage or deadline limits on swaps.

Use this severity rubric consistently:
- critical: anyone, with no special role, can take most or all user funds or take
  over the contract.
- high: user funds can be lost or locked under realistic conditions, or a
  privileged role can take or freeze user funds without limits.
- medium: needs unusual conditions, or causes only limited loss or denial of service.
- low: best-practice or robustness issue with no direct loss of funds.
- info: style or gas notes.

Report only real, specific issues that are present in the code. If the contract
looks safe, return an empty findings list.
Reply with JSON only, in this exact shape:
{"summary": "<2 sentences>",
 "findings": [{"title": "...",
               "severity": "critical|high|medium|low|info",
               "function": "<function or contract name>",
               "description": "<why this is risky for users of the contract>",
               "recommendation": "<how the developer should fix it>"}]}"""


SOURCIFY_URL = "https://sourcify.dev/server/v2/contract/43113"


def _fetch_routescan(address: str) -> dict | None:
    resp = requests.get(
        ROUTESCAN_URL,
        params={"module": "contract", "action": "getsourcecode", "address": address},
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json().get("result")
    if not isinstance(result, list) or not result:
        return None
    item = result[0]
    raw = (item.get("SourceCode") or "").strip()
    if not raw:  # contract exists but source is not verified
        return None
    return {"name": item.get("ContractName") or "Unknown", "source": flatten_source(raw)}


def _fetch_sourcify(address: str) -> dict | None:
    resp = requests.get(
        f"{SOURCIFY_URL}/{address}",
        params={"fields": "sources"},
        timeout=30,
    )
    if resp.status_code == 404:  # Sourcify has never seen this contract
        return None
    resp.raise_for_status()
    files = resp.json().get("sources") or {}
    parts = []
    for path, info in files.items():
        content = info.get("content") if isinstance(info, dict) else None
        if content:
            parts.append(f"// ===== {path} =====\n{content}")
    if not parts:
        return None
    # Name is only a label: use the first file's name without ".sol".
    first = next(iter(files)).rsplit("/", 1)[-1]
    name = first[:-4] if first.endswith(".sol") else first
    return {"name": name or "Unknown", "source": "\n\n".join(parts)}


def fetch_source(address: str) -> dict | None:
    """Return {"name": str, "source": str} for a verified contract, else None.

    Tries Routescan first, then Sourcify as a fallback.
    """
    if not Web3.is_address(address):
        raise ValueError("Not a valid address")
    address = Web3.to_checksum_address(address)
    try:
        found = _fetch_routescan(address)
        if found:
            return found
    except requests.RequestException:
        pass  # Routescan is down: Sourcify may still answer
    return _fetch_sourcify(address)


def flatten_source(raw: str) -> str:
    """Explorers return plain text, a JSON map of files, or Standard-JSON in {{ }}."""
    text = raw
    if text.startswith("{{") and text.endswith("}}"):
        text = text[1:-1]  # strip the extra outer braces
    if text.startswith("{"):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return raw
        files = data.get("sources", data)  # Standard-JSON or {path: {content}}
        parts = []
        for path, info in files.items():
            content = info.get("content") if isinstance(info, dict) else None
            if content:
                parts.append(f"// ===== {path} =====\n{content}")
        if parts:
            return "\n\n".join(parts)
    return raw


def _explain_empty(response) -> str:
    """Why did Gemini return no text? (blocked prompt, finish reason...)"""
    bits = []
    feedback = getattr(response, "prompt_feedback", None)
    if feedback is not None and getattr(feedback, "block_reason", None):
        bits.append(f"prompt blocked: {feedback.block_reason}")
    for candidate in getattr(response, "candidates", None) or []:
        reason = getattr(candidate, "finish_reason", None)
        if reason:
            bits.append(f"finish_reason={reason}")
    return "; ".join(bits) or "no details from the API"


def parse_model_json(text: str) -> dict:
    """Parse the model reply: plain JSON, ```json fences, or JSON inside extra prose."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        first, last = text.find("{"), text.rfind("}")
        if first != -1 and last > first:
            return json.loads(text[first : last + 1])
        raise


def _generate(client, model: str, contents: str, config, tries: int = 4):
    """Call Gemini; when the service is busy (503, 429...) wait and try again."""
    delay = 3
    for attempt in range(tries):
        try:
            return client.models.generate_content(model=model, contents=contents, config=config)
        except genai_errors.APIError as err:
            code = getattr(err, "code", None)
            if code not in RETRY_STATUS or attempt == tries - 1:
                raise
            print(f"[retry] Gemini busy (HTTP {code}), waiting {delay}s...", file=sys.stderr)
            time.sleep(delay)
            delay *= 2


def _generate_with_fallback(client, contents: str, config):
    """Try the main model (with retries); on failure try the fallback model, if any.

    Returns (response, name of the model that answered).
    """
    try:
        return _generate(client, MODEL, contents, config), MODEL
    except genai_errors.APIError:
        if not FALLBACK_MODEL:
            raise
        print(f"[fallback] switching to {FALLBACK_MODEL}", file=sys.stderr)
        return _generate(client, FALLBACK_MODEL, contents, config), FALLBACK_MODEL


def ask_gemini(name: str, source: str, attempts: int = 2) -> tuple[dict, str]:
    """Return (parsed findings, name of the model that answered)."""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    last_problem = ""
    for _ in range(attempts):
        contents = (
            f"Please review this Solidity contract ({name}) for safety issues and "
            f"suggest fixes.\n\n```solidity\n{source[:MAX_SOURCE_CHARS]}\n```"
        )
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.0,
        )
        response, model_used = _generate_with_fallback(client, contents, config)
        text = (response.text or "").strip()
        if not text:
            last_problem = f"Gemini returned no text ({_explain_empty(response)})"
            continue
        try:
            return parse_model_json(text), model_used
        except json.JSONDecodeError:
            last_problem = f"Gemini did not return valid JSON. Start of reply: {text[:300]!r}"
    raise RuntimeError(last_problem)


PATCH_PROMPT = """You are a Solidity engineer who fixes security problems for a defensive
tool. You receive one contract and the list of review findings about it. Return the
complete corrected contract.

Rules:
- Keep the contract name, the pragma line, and the public function names, parameters
  and behaviour. Change only what is needed to fix the listed findings.
- The result must be one self-contained file: no new imports or dependencies.
- Prefer small, standard fixes: checks-effects-interactions, a reentrancy guard written
  inline, an owner check, input validation, checking the result of a low-level call.
- Do not add features and do not write exploit code.

Reply with JSON only, in this exact shape:
{"patched_code": "<the full corrected Solidity source>",
 "changes": ["<one short sentence per change>"]}"""

MAX_PATCH_CHARS = 20_000  # patching returns the whole contract, so keep it small


def suggest_patch(source: str, findings: list[dict]) -> dict:
    """Ask Gemini for a corrected contract. Returns {patched_code, changes, model}."""
    findings = [f for f in findings if isinstance(f, dict)]
    if not findings:
        raise ValueError("Nothing to fix: there are no findings.")
    if len(source) > MAX_PATCH_CHARS:
        raise ValueError(
            f"This contract is too long for automatic patching (limit {MAX_PATCH_CHARS} characters)."
        )
    brief = [
        {k: f.get(k, "") for k in ("title", "severity", "function", "description", "recommendation")}
        for f in findings[:30]
    ]
    contents = (
        "Fix this Solidity contract.\n\nFindings (JSON):\n"
        + json.dumps(brief, ensure_ascii=False, indent=1)
        + f"\n\nContract:\n```solidity\n{source}\n```"
    )
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    config = types.GenerateContentConfig(
        system_instruction=PATCH_PROMPT,
        response_mime_type="application/json",
        temperature=0.0,
    )
    response, model_used = _generate_with_fallback(client, contents, config)
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError(f"Gemini returned no text ({_explain_empty(response)})")
    try:
        data = parse_model_json(text)
    except json.JSONDecodeError:
        raise RuntimeError("Gemini did not return valid JSON for the patch.")
    code = str(data.get("patched_code", "")).strip()
    if code.startswith("```"):  # some replies wrap the code in a fence
        code = code.strip("`").removeprefix("solidity").strip()
    if "contract" not in code:
        raise RuntimeError("Gemini did not return Solidity code.")
    changes = [str(c) for c in data.get("changes", []) if c][:20]
    return {"patched_code": code, "changes": changes, "model": model_used}


def normalize_findings(findings: list) -> list[dict]:
    """Keep only dict findings and force each severity into the known set."""
    clean = [dict(f) for f in findings if isinstance(f, dict)]
    for f in clean:
        sev = str(f.get("severity", "info")).strip().lower()
        f["severity"] = sev if sev in PENALTY else "info"
    return clean


def compute_score(findings: list[dict]) -> int:
    """Deterministic score: same findings always give the same number."""
    total = sum(PENALTY.get(f.get("severity", "info"), 0) for f in findings)
    return max(0, min(100, round(100 * 0.5 ** (total / SCORE_HALF_LIFE))))


def audit_code(source: str, name: str = "Pasted contract") -> dict:
    """Audit Solidity source text directly (no explorer needed)."""
    if not source or not source.strip():
        raise ValueError("Source code is empty")
    data, model_used = ask_gemini(name, source)
    findings = normalize_findings(data.get("findings", []))
    return {
        "contract_name": name,
        "score": compute_score(findings),
        "summary": data.get("summary", ""),
        "findings": findings,
        "model": model_used,  # which Gemini model wrote this review
        "truncated": len(source) > MAX_SOURCE_CHARS,  # True = only the first part was reviewed
        "source_chars": len(source),
    }


def audit_address(address: str) -> dict:
    found = fetch_source(address)
    if found is None:
        return {
            "address": address,
            "verified": False,
            "error": "Source code is not verified on the explorer. Paste the Solidity code instead.",
        }
    result = audit_code(found["source"], found["name"])
    result["address"] = Web3.to_checksum_address(address)
    result["verified"] = True
    return result


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python audit.py <0xAddress | path/to/Contract.sol>")
    arg = sys.argv[1]
    if arg.lower().endswith(".sol"):
        with open(arg, encoding="utf-8") as f:
            result = audit_code(f.read(), os.path.basename(arg))
    else:
        result = audit_address(arg)
    print(json.dumps(result, indent=2, ensure_ascii=False))