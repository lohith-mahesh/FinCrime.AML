import os
import json
import random
from typing import Tuple, Any, Dict
from openai import OpenAI
from models import AMLAction, AMLObservation, ViolationCategory, EnterpriseApp
from openenv.core.env_server import Environment
from data_generator import generate_data

class AMLEnv(Environment):
    SUPPORTS_CONCURRENT_SESSIONS = False

    def __init__(self):
        super().__init__()
        self.history = set()
        self.queried_accounts = set()
        self.queried_sanctions = set()
        self.queried_transactions = set()
        self.discovered_network = set()
        self.evidence_log = []
        self.scratchpad = []
        self.step_count = 0
        self.db_accounts = {}
        self.db_transactions = {}
        self.db_sanctions = []
        self.db_ground_truth = {}
        self.active_task = os.getenv("AML_TASK", "false_positive_sanctions")
        self.last_score = None
        self.last_task = None
        self.live_adversary = False

    def reset(self, **kwargs) -> AMLObservation:
        self.active_task = kwargs.get("task_id", os.getenv("AML_TASK", "false_positive_sanctions"))
        self.live_adversary = kwargs.get("live_adversary", False)
        
        feedback = None
        if self.last_score is not None and self.last_task == self.active_task:
            if self.last_score >= 0.9:
                feedback = f"Investigator easily solved the alert (Score {self.last_score:.2f}). Make the obfuscation significantly harder. Add more baseline noise."
            elif self.last_score >= 0.5:
                feedback = f"Investigator partially solved the alert (Score {self.last_score:.2f}). Make the evidence slightly harder to find."
            else:
                feedback = f"Investigator failed (Score {self.last_score:.2f}). Keep the difficulty similar but change the pattern."

        self.history = set()
        self.queried_accounts = set()
        self.queried_sanctions = set()
        self.queried_transactions = set()
        self.discovered_network = set()
        self.evidence_log = []
        self.scratchpad = []
        self.step_count = 0
        
        seed_mapping = {
            "false_positive_sanctions": 42,
            "detect_structuring": 101,
            "shell_company_layering": 202
        }
        task_seed = seed_mapping.get(self.active_task, 42)
        
        self.db_accounts, self.db_transactions, self.db_sanctions, self.db_ground_truth = generate_data(
            seed=task_seed, 
            feedback=feedback, 
            task_id=self.active_task
        )
        
        gt = self.db_ground_truth.get(self.active_task, {})
        alert_id = gt.get("alert_id", "ALT-000")
        target = gt.get("target", "UNKNOWN")
        
        triggers = {
            "false_positive_sanctions": f"Alert: {target} Sanctions Match",
            "detect_structuring": f"Alert: {target} Cash Velocity",
            "shell_company_layering": f"Alert: {target} High-Value Wires"
        }
        
        trigger = triggers.get(self.active_task, f"Alert: {target}")
        self.state_data = {"alert_id": alert_id, "alert_trigger": trigger}
        self.discovered_network.add(target)
            
        return AMLObservation(
            alert_id=alert_id, 
            alert_trigger=trigger, 
            command_status="init", 
            database_response=f"START: {trigger}", 
            documented_evidence=self.evidence_log.copy(), 
            scratchpad=self.scratchpad.copy(),
            reward=0.0, 
            done=False
        )

    def _trigger_live_adversary(self):
        if self.active_task != "shell_company_layering":
            return
            
        gt = self.db_ground_truth.get(self.active_task, {})
        chain = gt.get("chain", [])
        if not chain:
            return
            
        last_node = chain[-1]
        
        api_key = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")
        base_url = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
        model = os.getenv("LAUNDERER_MODEL") or os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"

        if not api_key:
            return

        client = OpenAI(base_url=base_url, api_key=api_key)
        
        prompt = f"""You are the Launderer. The investigator is tracing your funds.
The current chain ends at {last_node}.
Create a new shell company account and wire the funds there to evade detection.
Output strictly JSON:
{{
  "new_account_id": "ACC-XXXX",
  "name": "Entity_New",
  "country": "Panama",
  "account_type": "corporate",
  "kyc_status": "APPROVED",
  "occupation": "Consulting",
  "amount": 7000,
  "date": "2026-04-08"
}}"""

        try:
            res = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            content = res.choices[0].message.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            data = json.loads(content.strip())
            
            new_acc = data.get("new_account_id")
            if not new_acc or new_acc in self.db_accounts:
                new_acc = f"ACC-{random.randint(2000, 9999)}"
                
            self.db_accounts[new_acc] = {
                "name": data.get("name", "Unknown Shell"),
                "country": data.get("country", "Panama"),
                "account_type": data.get("account_type", "corporate"),
                "kyc_status": data.get("kyc_status", "APPROVED"),
                "occupation": data.get("occupation", "Consulting"),
                "risk_score": 99,
                "dob": "1980-01-01",
                "balance": data.get("amount", 7000)
            }
            
            if new_acc not in self.db_transactions:
                self.db_transactions[new_acc] = []
                
            import uuid
            self.db_transactions[last_node].append({
                "transaction_id": f"TXN-{uuid.uuid4().hex[:12].upper()}",
                "date": data.get("date", "2026-04-08"),
                "amount": data.get("amount", 7000),
                "currency": "USD",
                "type": "wire_transfer",
                "sender_id": last_node,
                "receiver_id": new_acc,
                "status": "COMPLETED"
            })
            
            self.db_ground_truth[self.active_task]["chain"].append(new_acc)
        except Exception:
            pass

    def step(self, action: AMLAction) -> Tuple[AMLObservation, float, bool, Dict[str, Any]]:
        self.step_count += 1
        reward = -0.05
        done = False
        db_resp = ""
        task_score = 0.01 
        
        if random.random() < 0.05:
            db_resp = f"503 Service Unavailable: {action.target_app.value} is temporarily down. Please retry."
            obs = AMLObservation(
                alert_id=self.state_data["alert_id"], 
                alert_trigger=self.state_data["alert_trigger"], 
                command_status="failed", 
                database_response=db_resp, 
                documented_evidence=self.evidence_log.copy(), 
                scratchpad=self.scratchpad.copy(),
                reward=float(reward), 
                done=False
            )
            return obs, float(reward), False, {"task_score": task_score}

        app_command_map = {
            "query_account": EnterpriseApp.CORE_BANKING,
            "query_transactions": EnterpriseApp.CORE_BANKING,
            "search_sanctions": EnterpriseApp.GLOBAL_SANCTIONS,
            "escalate_alert": EnterpriseApp.HR_PORTAL,
            "clear_alert": EnterpriseApp.HR_PORTAL,
            "freeze_account": EnterpriseApp.CORE_BANKING
        }

        if action.command not in ["save_to_notes", "read_notes"]:
            expected_app = app_command_map.get(action.command)
            if action.target_app != expected_app:
                reward -= 0.10
                db_resp = f"ACCESS DENIED: Command '{action.command}' cannot be executed in {action.target_app.value}. Use {expected_app.value if expected_app else 'the correct app'}."
                obs = AMLObservation(
                    alert_id=self.state_data["alert_id"], 
                    alert_trigger=self.state_data["alert_trigger"], 
                    command_status="failed", 
                    database_response=db_resp, 
                    documented_evidence=self.evidence_log.copy(), 
                    scratchpad=self.scratchpad.copy(),
                    reward=float(reward), 
                    done=False
                )
                return obs, float(reward), False, {"task_score": task_score}

        sig = f"{action.target_app}_{action.command}_{action.account_id}_{action.search_name}_{action.page}"
        gt = self.db_ground_truth.get(self.active_task, {})
        
        valid_targets = set(gt.get("chain", []))
        if gt.get("target"):
            valid_targets.add(gt.get("target"))
        
        if sig in self.history and action.command not in ["escalate_alert", "clear_alert", "freeze_account", "save_to_notes", "read_notes"]:
            reward -= 0.15
            db_resp = "DUPLICATE QUERY. Proceed to next step or escalate/clear."
        else:
            if action.command not in ["escalate_alert", "clear_alert", "freeze_account", "save_to_notes", "read_notes"]:
                self.history.add(sig)
                
            if action.command in ["query_account", "query_transactions"]:
                if action.account_id in valid_targets:
                    if action.command == "query_transactions" and action.account_id not in self.queried_transactions:
                        reward += 0.15
                    elif action.command == "query_account" and action.account_id not in self.queried_accounts:
                        reward += 0.10

            if action.command == "query_transactions":
                if action.account_id and action.account_id not in self.queried_transactions:
                    self.queried_transactions.add(action.account_id)
                    self.evidence_log.append(f"TX_RECORD:{action.account_id}")
                        
                txs = self.db_transactions.get(action.account_id, [])
                txs.sort(key=lambda x: x['date'], reverse=True)
                
                for t in txs:
                    if t['receiver_id'] != action.account_id:
                        self.discovered_network.add(t['receiver_id'])
                
                page = max(1, action.page)
                start_idx = (page - 1) * 10
                end_idx = start_idx + 10
                page_txs = txs[start_idx:end_idx]
                total_pages = max(1, (len(txs) + 9) // 10)
                
                if not page_txs:
                    db_resp = f"No transactions found on page {page}."
                else:
                    lines = [f"DATE: {t['date']} | TYPE: {t['type']} | AMT: ${t['amount']} | TO: {t['receiver_id']}" for t in page_txs]
                    db_resp = f"[Page {page}/{total_pages}]\n" + "\n".join(lines)
            
            elif action.command == "query_account":
                if action.account_id and action.account_id not in self.queried_accounts:
                    self.queried_accounts.add(action.account_id)
                    self.evidence_log.append(f"ACC_RECORD:{action.account_id}")
                        
                res = self.db_accounts.get(action.account_id)
                db_resp = json.dumps(res) if res else "Not found"
            
            elif action.command == "search_sanctions":
                query_val = action.search_name or action.account_id or "unknown"
                is_new_query = query_val not in self.queried_sanctions
                
                if is_new_query:
                    self.queried_sanctions.add(query_val)
                    self.evidence_log.append(f"SANCTION_RECORD:{query_val}")
                        
                m = [s for s in self.db_sanctions if action.search_name and action.search_name.lower() in s["name"].lower()]
                
                if m and is_new_query:
                    reward += 0.10
                db_resp = json.dumps(m) if m else "No match"
                
            elif action.command == "save_to_notes":
                if action.note_content:
                    self.scratchpad.append(action.note_content)
                    db_resp = "Note successfully saved to scratchpad."
                else:
                    db_resp = "No content provided to save."
            
            elif action.command == "read_notes":
                if self.scratchpad:
                    db_resp = "CURRENT NOTES:\n" + "\n".join(f"- {n}" for n in self.scratchpad)
                else:
                    db_resp = "Scratchpad is empty."
            
            elif action.command in ["escalate_alert", "clear_alert", "freeze_account"]:
                done = True
                task_score = self._grade_task(action)
                reward += task_score

        if self.live_adversary and self.step_count % 3 == 0 and not done:
            self._trigger_live_adversary()

        if self.step_count >= 15:
            done = True

        if done:
            self.last_score = task_score
            self.last_task = self.active_task

        obs = AMLObservation(
            alert_id=self.state_data["alert_id"], 
            alert_trigger=self.state_data["alert_trigger"], 
            command_status="success" if db_resp else "unknown", 
            database_response=db_resp, 
            documented_evidence=self.evidence_log.copy(), 
            scratchpad=self.scratchpad.copy(),
            reward=float(reward), 
            done=done
        )
        return obs, float(reward), done, {"task_score": task_score}

    def _grade_task(self, action: AMLAction) -> float:
        cmd = action.command
        cat = action.violation_category
        gt = self.db_ground_truth.get(self.active_task, {})
        
        base_score = 0.01 
        
        if self.active_task == "false_positive_sanctions":
            target = gt.get("target")
            outcome = gt.get("outcome")
            target_account = self.db_accounts.get(target, {})
            target_name = target_account.get("name", "").lower()
            target_dob = target_account.get("dob", "")
            
            has_name_queried = any(target_name in s.lower() for s in self.queried_sanctions)
            has_dob_verified = (action.verified_dob == target_dob)
            
            if cmd == "freeze_account":
                if outcome == "FALSE_POSITIVE":
                    return -2.0
                elif outcome == "SANCTIONS_MATCH":
                    if target in self.queried_accounts and has_name_queried and has_dob_verified:
                        return 1.0
                    elif target in self.queried_accounts and has_name_queried:
                        return 0.5
                return -2.0
            
            if outcome == "FALSE_POSITIVE" and cmd == "clear_alert" and cat == ViolationCategory.FALSE_POSITIVE:
                if target in self.queried_accounts and has_name_queried:
                    base_score = 0.50
                    if has_dob_verified:
                        base_score = 0.99
            elif outcome == "SANCTIONS_MATCH" and cmd == "escalate_alert" and cat == ViolationCategory.SANCTIONS_MATCH:
                if target in self.queried_accounts and has_name_queried:
                    base_score = 0.50
                    if has_dob_verified:
                        base_score = 0.99
            
        elif self.active_task == "detect_structuring":
            target = gt.get("target")
            evasion_dates = gt.get("evasion_dates", [])
            
            if cmd == "freeze_account":
                if action.account_id == target or action.account_id in action.complicit_account_ids:
                    dates_found = sum(1 for d in evasion_dates if d in (action.rationale or ""))
                    if target in self.queried_transactions:
                        if dates_found >= 2:
                            return 1.0
                        return 0.5
                    return -0.5
                return -2.0

            if cmd == "escalate_alert" and cat == ViolationCategory.STRUCTURING:
                if target in self.queried_transactions:
                    dates_found = sum(1 for d in evasion_dates if d in (action.rationale or ""))
                    if target == action.account_id or target in action.complicit_account_ids:
                        if dates_found >= 2:
                            base_score = 0.99
                        else:
                            base_score = 0.50
            
        elif self.active_task == "shell_company_layering":
            target_chain = set(gt.get("chain", []))
            actual = set(action.complicit_account_ids or [])
            if action.account_id:
                actual.add(action.account_id)

            if cmd == "freeze_account":
                intersection = target_chain.intersection(actual)
                if intersection and len(intersection) == len(target_chain) and len(actual) == len(target_chain):
                    return 1.0
                elif intersection:
                    return 0.5
                return -2.0

            if cmd == "escalate_alert" and cat == ViolationCategory.LAYERING:
                intersection = target_chain.intersection(actual)
                if intersection:
                    raw_score = float(len(intersection)) / len(target_chain)
                    penalty = len(actual.difference(target_chain)) * 0.3
                    base_score = max(0.01, min(0.99, raw_score - penalty))
                
        return base_score

    def state(self) -> Dict[str, Any]: 
        return {"step": self.step_count}
