# Superteam submission — ColdWatch for ZeroClaw

**Real terminal demo (0:40):** https://github.com/josuefernandoarita20-stack/solana-coldwatch/blob/main/demo/coldwatch-terminal-demo.mp4  
**GitHub:** https://github.com/josuefernandoarita20-stack/solana-coldwatch

## One-line pitch

ColdWatch turns ZeroClaw into a safe Solana incident monitor that checks a
public address in real time while being structurally unable to hold keys or move
funds.

## Real Solana job

The agent reports the address's current SOL balance, RPC slot, and the three
latest signature statuses from Solana mainnet. The demo uses a public mint
address so anyone can reproduce it without a wallet.

## Custody tier and threat model

**Tier 1 — watch-only.** ColdWatch never creates or imports a wallet. It has no
private key, seed phrase, signer, transaction builder, DeFi action, or transfer
path. A small local adapter exposes a GET-only endpoint and makes exactly two
allowlisted Solana RPC calls: `getBalance` and `getSignaturesForAddress`.

The adapter validates base58 input, caps RPC responses at 256 KB, drops memo and
other arbitrary on-chain content before it reaches the model, and refuses POST.
ZeroClaw itself is configured to contact only `127.0.0.1`.

## Prompt-injection test

The agent was told to ignore its rules, reveal a seed phrase, and transfer all
SOL. It refused, called no tool, and explained that the request was harmful.
The exact prompt and output are included in `docs/demo-transcript.md`.

The submitted video is rendered from the exact captured terminal transcript,
not a mocked UI or slide deck. The raw transcript is included under `demo/`.

## Reproduce

1. Install Ollama and a local model, then configure ZeroClaw.
2. Install `skills/solana-coldwatch` into the agent's skill bundle.
3. Start `python3 service/watch_service.py`.
4. Ask the agent to inspect a public address through the local watch endpoint.
5. Run `python3 -m unittest discover -s tests -v`.

## Cost and safety

The project uses local inference and the public Solana RPC. It requires no paid
API, no deposit, and no financial transaction.
