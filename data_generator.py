import os
import json
import random
import uuid
from datetime import datetime
from openai import OpenAI

def generate_fallback_data(seed=None):
    if seed is not None:
        random.seed(seed)
        
    accounts = {}
    for i in range(1000, 1050):
        accounts[f"ACC-{i}"] = {
            "name": f"Entity_{i}", 
            "country": random.choice(["USA", "UK", "UAE", "Panama"]),
            "account_type": random.choice(["corporate", "retail"]),
            "kyc_status": random.choice(["APPROVED", "PENDING_REVIEW"]),
            "occupation": random.choice(["Consulting", "Import Export", "Retail"]),
            "risk_score": random.randint(10, 99), 
            "dob": f"{random.randint(1960, 2000)}-01-01",
            "balance": random.randint(5000, 500000)
        }
        
    acc_keys = list(accounts.keys())
    
    st = random.choice(acc_keys)
    acc_keys.remove(st)
    dt = random.choice(acc_keys)
    acc_keys.remove(dt)
    ls = random.choice(acc_keys)
    acc_keys.remove(ls)
    lm1 = random.choice(acc_keys)
    acc_keys.remove(lm1)
    ld = random.choice(acc_keys)
    acc_keys.remove(ld)
    
    transactions = {k: [] for k in accounts.keys()}
    
    sd = ["2026-04-01", "2026-04-02", "2026-04-03"]
    for d in sd:
        transactions[dt].append({
            "transaction_id": f"TXN-{uuid.uuid4().hex[:12].upper()}",
            "date": d,
            "amount": random.randint(9500, 9900),
            "currency": "USD",
            "type": "cash_deposit",
            "sender_id": dt,
            "receiver_id": dt,
            "status": "COMPLETED"
        })
        
    for acc in [dt, ls] + random.sample(acc_keys, 10):
        for _ in range(15):
            sender = random.choice(acc_keys)
            transactions[acc].append({
                "transaction_id": f"TXN-{uuid.uuid4().hex[:12].upper()}",
                "date": f"2026-03-{random.randint(1,28):02d}",
                "amount": random.randint(50, 3000),
                "currency": "USD",
                "type": "payroll",
                "sender_id": sender,
                "receiver_id": acc,
                "status": "COMPLETED"
            })
            
    transactions[ls].append({
        "transaction_id": f"TXN-{uuid.uuid4().hex[:12].upper()}",
        "date": "2026-04-05", 
        "amount": 8000, 
        "currency": "USD",
        "type": "wire_transfer", 
        "sender_id": ls,
        "receiver_id": lm1,
        "status": "COMPLETED"
    })
    
    transactions[lm1].append({
        "transaction_id": f"TXN-{uuid.uuid4().hex[:12].upper()}",
        "date": "2026-04-06", 
        "amount": 7900, 
        "currency": "USD",
        "type": "wire_transfer", 
        "sender_id": lm1,
        "receiver_id": ld,
        "status": "COMPLETED"
    })

    sanctions_list = [
        {
            "name": accounts[st]["name"],
            "list": "OFAC_SDN",
            "dob": "1900-01-01",
            "country": "North Korea"
        }
    ]
    
    ground_truth = {
        "false_positive_sanctions": {
            "alert_id": f"ALT-{random.randint(100, 999)}",
            "target": st,
            "outcome": "FALSE_POSITIVE"
        },
        "detect_structuring": {
            "alert_id": f"ALT-{random.randint(100, 999)}",
            "target": dt,
            "evasion_dates": sd
        },
        "shell_company_layering": {
            "alert_id": f"ALT-{random.randint(100, 999)}",
            "target": ls,
            "chain": [ls, lm1, ld]
        }
    }

    if seed is not None:
        random.seed()

    return accounts, transactions, sanctions_list, ground_truth

def generate_data(seed=None, feedback=None, task_id="false_positive_sanctions"):
    api_key = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")
    base_url = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
    model = os.getenv("LAUNDERER_MODEL") or os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"

    if not api_key or os.getenv("DISABLE_LAUNDERER", "false").lower() == "true":
        return generate_fallback_data(seed)

    client = OpenAI(base_url=base_url, api_key=api_key)

    prompt = f"""
You are the Launderer Agent. Generate a highly obfuscated, completely realistic financial ledger in strict JSON.
Target Task: {task_id}
Investigator Feedback from last episode: {feedback or "No prior feedback. Establish baseline difficulty."}

Generate exactly 8 to 12 accounts and 25 to 35 transactions total. Include baseline noise.
Maintain strict referential integrity. No orphaned IDs. Every transaction must have a unique transaction_id.

Required JSON Schema:
{{
  "accounts": {{"ACC-XXXX": {{"name": "...", "country": "...", "account_type": "corporate|retail", "kyc_status": "APPROVED|PENDING", "occupation": "...", "risk_score": 50, "dob": "YYYY-MM-DD", "balance": 10000}}}},
  "transactions": {{"ACC-XXXX": [{{"transaction_id": "TXN-...", "date": "YYYY-MM-DD", "amount": 1000, "currency": "USD", "type": "wire_transfer", "sender_id": "ACC-...", "receiver_id": "ACC-...", "status": "COMPLETED"}}]}},
  "sanctions_list": [{{"name": "...", "list": "...", "dob": "...", "country": "..."}}],
  "ground_truth": {{
    "false_positive_sanctions": {{"alert_id": "ALT-101", "target": "ACC-...", "outcome": "FALSE_POSITIVE"}},
    "detect_structuring": {{"alert_id": "ALT-102", "target": "ACC-...", "evasion_dates": ["YYYY-MM-DD"]}},
    "shell_company_layering": {{"alert_id": "ALT-103", "target": "ACC-...", "chain": ["ACC-...", "ACC-..."]}}
  }}
}}
"""

    try:
        res = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=8192,
            response_format={"type": "json_object"}
        )
        
        content = res.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
            
        data = json.loads(content.strip())
        
        acc = data.get("accounts", {})
        tx = data.get("transactions", {})
        sanc = data.get("sanctions_list", [])
        gt = data.get("ground_truth", {})
        
        if not acc or not tx or not gt:
            print("[LAUNDERER WARNING] Missing keys in generated JSON. Using fallback.")
            return generate_fallback_data(seed)
            
        return acc, tx, sanc, gt
        
    except Exception as e:
        print(f"\n[LAUNDERER FATAL ERROR] {str(e)}\n") 
        return generate_fallback_data(seed)

if __name__ == "__main__":
    a, t, s, g = generate_data()
    print(json.dumps(g, indent=2))
