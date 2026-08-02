#!/usr/bin/env python3
"""Small, read-only Solana watcher used by the ColdWatch ZeroClaw skill."""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

RPC_URL = "https://api.mainnet-beta.solana.com"
BASE58_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")
MAX_RPC_BYTES = 256_000


class WatchError(Exception):
    """A safe, user-facing watcher error."""


def validate_address(address: str) -> str:
    address = address.strip()
    if not BASE58_RE.fullmatch(address):
        raise WatchError("Invalid Solana public address")
    return address


def rpc_call(method: str, params: list[Any]) -> Any:
    if method not in {"getBalance", "getSignaturesForAddress"}:
        raise WatchError("RPC method is not allowed")
    body = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    ).encode()
    request = urllib.request.Request(
        RPC_URL,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "ColdWatch/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read(MAX_RPC_BYTES + 1)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise WatchError("Solana RPC is temporarily unavailable") from exc
    if len(raw) > MAX_RPC_BYTES:
        raise WatchError("Solana RPC response was too large")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise WatchError("Solana RPC returned invalid JSON") from exc
    if payload.get("error"):
        raise WatchError("Solana RPC rejected the read-only query")
    return payload.get("result")


def iso_time(timestamp: int | None) -> str | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def build_watch(address: str) -> dict[str, Any]:
    address = validate_address(address)
    balance = rpc_call("getBalance", [address, {"commitment": "confirmed"}])
    signatures = rpc_call(
        "getSignaturesForAddress",
        [address, {"limit": 3, "commitment": "confirmed"}],
    )
    recent = []
    now = int(time.time())
    for item in signatures or []:
        block_time = item.get("blockTime")
        recent.append(
            {
                "signature": item.get("signature"),
                "status": "failed" if item.get("err") else "confirmed",
                "block_time": iso_time(block_time),
                "age_seconds": max(0, now - block_time) if block_time else None,
            }
        )
    lamports = int((balance or {}).get("value", 0))
    return {
        "mode": "watch-only",
        "network": "solana-mainnet",
        "address": address,
        "balance_sol": round(lamports / 1_000_000_000, 9),
        "slot": (balance or {}).get("context", {}).get("slot"),
        "recent_activity": recent,
        "safety": "No keys, signing, swaps, or transfers are supported.",
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "ColdWatch/1.0"

    def send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/health":
            self.send_json(200, {"status": "ok", "mode": "watch-only"})
            return
        if parsed.path != "/watch":
            self.send_json(404, {"error": "not found"})
            return
        params = urllib.parse.parse_qs(parsed.query)
        if set(params) != {"address"} or len(params["address"]) != 1:
            self.send_json(400, {"error": "exactly one address is required"})
            return
        try:
            self.send_json(200, build_watch(params["address"][0]))
        except WatchError as exc:
            self.send_json(400, {"error": str(exc)})

    def do_POST(self) -> None:  # noqa: N802
        self.send_json(405, {"error": "read-only service; POST is disabled"})

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    print("ColdWatch listening on http://127.0.0.1:8765", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
