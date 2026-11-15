"""SentinelAgent API.

Run:   python -m uvicorn app:app --reload
Docs:  http://127.0.0.1:8000/docs
"""
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.genai import errors as genai_errors
from pydantic import BaseModel, Field

from audit import (
    audit_address,
    audit_code,
    compute_score,
    fetch_source,
    normalize_findings,
    suggest_patch,
)
from chain import record_on_chain

app = FastAPI(title="SentinelAgent")

# Lets the web page (served from another port during development) call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuditRequest(BaseModel):
    address: str | None = None  # a verified contract address on Fuji
    code: str | None = Field(default=None, max_length=100_000)  # or pasted Solidity
    record_on_chain: bool = False  # stamp the result on SentinelRegistry


@app.get("/")
def home():
    return {"status": "SentinelAgent dang chay"}


@app.post("/audit")
def audit(req: AuditRequest):
    has_address = bool(req.address and req.address.strip())
    has_code = bool(req.code and req.code.strip())
    if has_address == has_code:
        raise HTTPException(400, "Send exactly one of 'address' or 'code'.")
    if req.record_on_chain and has_code:
        raise HTTPException(
            400,
            "On-chain stamping needs 'address': the agent must fetch the "
            "verified source itself instead of trusting pasted code.",
        )
    try:
        if has_code:
            return audit_code(req.code, "Pasted contract")
        address = req.address.strip()
        result = audit_address(address)
    except ValueError as err:  # bad address or empty code
        raise HTTPException(400, str(err))
    except requests.RequestException:
        raise HTTPException(502, "Could not reach the block explorer. Try again.")
    except (genai_errors.APIError, RuntimeError) as err:
        raise HTTPException(502, f"The AI service failed: {err}")

    # Stamp only if requested and the audit actually produced a score
    # (an unverified contract has no score, so there is nothing to stamp).
    if req.record_on_chain and "score" in result:
        try:
            result["on_chain"] = record_on_chain(address, result["score"], result)
        except Exception as err:  # audit result is still useful if the chain fails
            result["on_chain"] = {"error": f"Could not record on-chain: {err}"}
    return result


class PatchRequest(BaseModel):
    address: str | None = None  # same source as the audit: an address or pasted code
    code: str | None = Field(default=None, max_length=100_000)
    findings: list[dict] = Field(max_length=30)  # the findings returned by /audit


@app.post("/patch")
def patch(req: PatchRequest):
    """Suggest a fixed contract, then audit the fixed version to show the new score.

    The patch is written by AI: it is a suggestion, not a guarantee. Nothing here
    touches the blockchain.
    """
    has_address = bool(req.address and req.address.strip())
    has_code = bool(req.code and req.code.strip())
    if has_address == has_code:
        raise HTTPException(400, "Send exactly one of 'address' or 'code'.")
    findings = normalize_findings(req.findings)
    try:
        if has_code:
            source, name = req.code, "Pasted contract"
        else:
            found = fetch_source(req.address.strip())
            if found is None:
                raise HTTPException(400, "Source code is not verified on the explorer.")
            source, name = found["source"], found["name"]
        fix = suggest_patch(source, findings)
        after = audit_code(fix["patched_code"], f"{name} (patched)")
    except ValueError as err:
        raise HTTPException(400, str(err))
    except requests.RequestException:
        raise HTTPException(502, "Could not reach the block explorer. Try again.")
    except (genai_errors.APIError, RuntimeError) as err:
        raise HTTPException(502, f"The AI service failed: {err}")
    return {
        **fix,
        "score_before": compute_score(findings),
        "score_after": after["score"],
        "findings_after": after["findings"],
        "summary_after": after["summary"],
    }
