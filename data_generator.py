import random

def generate_data(seed: int = None):
    if seed is not None:
        random.seed(seed)
        
    accounts = {}
    for i in range(1000, 1200):
        acc_id = f"ACC-{i}"
        accounts[acc_id] = {
            "name": f"Entity_{i}", 
            "country": random.choice(["USA", "UK", "UAE", "Panama", "BVI", "Cayman Islands", "Cyprus"]),
            "occupation": random.choice(["Consulting", "Import Export", "Holding Co", "Retail", "Software"]),
            "risk_score": random.randint(10, 99), 
            "dob": f"{random.randint(1960, 2000)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
        }

    acc_keys = list(accounts.keys())
    
    sanctions_target = random.choice(acc_keys)
    acc_keys.remove(sanctions_target)
    
    structuring_target = random.choice(acc_keys)
    acc_keys.remove(structuring_target)
    
    layer_source = random.choice(acc_keys)
    acc_keys.remove(layer_source)
    layer_mid_1 = random.choice(acc_keys)
    acc_keys.remove(layer_mid_1)
    layer_mid_2 = random.choice(acc_keys)
    acc_keys.remove(layer_mid_2)
    layer_dest = random.choice(acc_keys)
    acc_keys.remove(layer_dest)
    
    transactions = {k: [] for k in accounts.keys()}
    
    structuring_dates = [f"2026-04-{i:02d}" for i in range(1, 5)]
    for d in structuring_dates:
        transactions[structuring_target].append({
            "date": d,
            "amount": random.randint(9500, 9999),
            "type": "cash_deposit",
            "receiver_id": structuring_target
        })
        
    for acc in [structuring_target, layer_source] + random.sample(acc_keys, 20):
        for _ in range(random.randint(40, 80)):
            month = random.choice([3, 4])
            transactions[acc].append({
                "date": f"2026-{month:02d}-{random.randint(1,28):02d}",
                "amount": random.randint(50, 3000),
                "type": random.choice(["payroll", "vendor_payment", "utility"]),
                "receiver_id": random.choice(list(accounts.keys()))
            })
            
    smurf_amounts = [random.randint(7000, 9000) for _ in range(random.randint(8, 14))]
    receivers = [layer_mid_1, layer_mid_2]
    
    for i, amt in enumerate(smurf_amounts):
        receiver = receivers[i % 2]
        transactions[layer_source].append({
            "date": f"2026-04-{random.randint(1,5):02d}", 
            "amount": amt, 
            "type": "wire_transfer", 
            "receiver_id": receiver
        })
        transactions[receiver].append({
            "date": f"2026-04-{random.randint(6,9):02d}", 
            "amount": amt - random.randint(50, 200),
            "type": "wire_transfer", 
            "receiver_id": layer_dest
        })

    is_false_positive = random.choice([True, False])
    sanctions_list = []
    
    if is_false_positive:
        sanctions_list.append({
            "name": accounts[sanctions_target]["name"],
            "list": "OFAC_SDN",
            "dob": "1900-01-01",
            "country": "North Korea"
        })
        sanctions_outcome = "FALSE_POSITIVE"
    else:
        sanctions_list.append({
            "name": accounts[sanctions_target]["name"],
            "list": "INTERPOL_RED",
            "dob": accounts[sanctions_target]["dob"],
            "country": accounts[sanctions_target]["country"]
        })
        sanctions_outcome = "SANCTIONS_MATCH"
        
    for _ in range(10):
        sanctions_list.append({
            "name": f"Entity_{random.randint(2000, 3000)}",
            "list": random.choice(["OFAC_SDN", "EU_SANCTIONS", "UN_RESTRICTED"]),
            "dob": f"{random.randint(1950, 1990)}-01-01",
            "country": "Russia"
        })

    ground_truth = {
        "false_positive_sanctions": {
            "alert_id": f"ALT-{random.randint(100, 999)}",
            "target": sanctions_target,
            "outcome": sanctions_outcome
        },
        "detect_structuring": {
            "alert_id": f"ALT-{random.randint(100, 999)}",
            "target": structuring_target,
            "evasion_dates": structuring_dates
        },
        "shell_company_layering": {
            "alert_id": f"ALT-{random.randint(100, 999)}",
            "target": layer_source,
            "chain": [layer_source, layer_mid_1, layer_mid_2, layer_dest]
        }
    }

    if seed is not None:
        random.seed()

    return accounts, transactions, sanctions_list, ground_truth

if __name__ == "__main__":
    acc, tx, sanc, gt = generate_data()
    print("Data generated successfully in-memory.")