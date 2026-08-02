#!/usr/bin/env python3
import json
import sys

payload = json.load(sys.stdin)
print(f"network:       {payload['network']}")
print(f"mode:          {payload['mode']}")
print(f"address:       {payload['address'][:8]}...{payload['address'][-6:]}")
print(f"balance:       {payload['balance_sol']} SOL")
print(f"slot:          {payload['slot']}")
for index, item in enumerate(payload["recent_activity"], start=1):
    signature = item["signature"]
    print(f"signature {index}:  {signature[:8]}...{signature[-6:]}  {item['status']}")
print(f"safety:        {payload['safety']}")
