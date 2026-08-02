# ColdWatch for ZeroClaw

ColdWatch is a Tier 1, watch-only Solana incident monitor built for the
ZeroClaw Solana bounty. It lets a ZeroClaw agent inspect one public address,
report its SOL balance and three latest confirmed signatures, and refuse every
request involving keys, signing, trading, or transfers.

## Why this is safe

- No wallet is created or imported.
- No secrets, seed phrases, or private keys exist in the project.
- The helper exposes GET endpoints only and makes two fixed, read-only Solana
  RPC calls: `getBalance` and `getSignaturesForAddress`.
- RPC memos and other arbitrary on-chain text are dropped before the model sees
  the response, reducing prompt-injection exposure.
- ZeroClaw can contact only `127.0.0.1`, not arbitrary remote hosts.

## Architecture

User → ZeroClaw CLI → `solana-coldwatch` skill → local read-only helper →
Solana mainnet RPC.

## Run

1. Start the helper: `python3 service/watch_service.py`
2. Check it: `curl http://127.0.0.1:8765/health`
3. Ask the configured `sentinel` agent to inspect a public Solana address.

## Threat model

| Threat | Control |
|---|---|
| Seed/private-key theft | Keys are neither requested nor supported |
| Prompt injection in memo/RPC data | Arbitrary memo text is discarded |
| Transaction submission | No method or endpoint exists |
| SSRF/arbitrary host access | Fixed RPC host in helper; ZeroClaw allowlisted to localhost |
| Oversized RPC response | 256 KB hard response cap |
| Invalid address payload | Strict base58 format and length validation |

## Tests

`python3 -m unittest discover -s tests -v`

The tests verify input rejection, method allowlisting, result shaping, removal
of malicious memo content, and absence of transaction/secret fields.
