import os
import json
from typing import Tuple, Any, Dict
from models import AMLAction, AMLObservation, ViolationCategory
from openenv.core.env_server import Environment
from data_generator import generate_data

class AMLEnv(Environment):
    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self):
        super().__init__()
        self.active_task = os.getenv("AML_TASK", "false_positive_sanctions")
        self.history = set()
        self.queried_accounts = set()
        self.queried_sanctions = set()
        self.queried_transactions = set()
        self.discovered_network = set()
        self.evidence_log = []
        self.step_count = 0
        self.db_accounts = {}
        self.db_transactions = {}
        self.db_sanctions = []
        self.db_ground_truth = {}

    def reset(self) -> AMLObservation:
        self.active_task = os.getenv("AML_TASK", "false_positive_sanctions")
        self.history = set()
        self.queried_accounts = set()
        self.queried_sanctions = set()
        self.queried_transactions = set()
        self.discovered_network = set()
        self.evidence_log = []
        self.step_count = 0
        
        seed_mapping = {
            "false_positive_sanctions": 42,
            "detect_structuring": 101,
            "shell_company_layering": 202
        }
        task_seed = seed_mapping.get(self.active_task, 42)
        
        self.db_accounts, self.db_transactions, self.db_sanctions, self.db_ground_truth = generate_data(seed=task_seed)
        
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
            reward=0.0, 
            done=False
        )

    def step(self, action: AMLAction) -> Tuple[AMLObservation, float, bool, Dict[str, Any]]:
        self.step_count += 1
        reward = -0.05
        done = False
        db_resp = ""
        task_score = 0.0
        
        sig = f"{action.command}_{action.account_id}_{action.search_name}_{action.page}"
        gt = self.db_ground_truth.get(self.active_task, {})
        
        valid_targets = set(gt.get("chain", []))
        if gt.get("target"):
            valid_targets.add(gt.get("target"))
        
        if sig in self.history and action.command not in ["escalate_alert", "clear_alert"]:
            reward -= 0.15
            db_resp = "DUPLICATE QUERY. Proceed to next step or escalate/clear."
        else:
            if action.command not in ["escalate_alert", "clear_alert"]:
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
                start_idx = (page - 1) * 20
                end_idx = start_idx + 20
                page_txs = txs[start_idx:end_idx]
                total_pages = max(1, (len(txs) + 19) // 20)
                
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
            
            elif action.command in ["escalate_alert", "clear_alert"]:
                done = True
                task_score = self._grade_task(action)
                reward += task_score

        if self.step_count >= 15:
            done = True

        obs = AMLObservation(
            alert_id=self.state_data["alert_id"], 
            alert_trigger=self.state_data["alert_trigger"], 
            command_status="success", 
            database_response=db_resp, 
            documented_evidence=self.evidence_log.copy(), 
            reward=float(reward), 
            done=done
        )
        return obs, float(reward), done, {"task_score": task_score}

    def _grade_task(self, action: AMLAction) -> float:
        cmd = action.command
        cat = action.violation_category
        gt = self.db_ground_truth.get(self.active_task, {})
        
        if self.active_task == "false_positive_sanctions":
            target = gt.get("target")
            outcome = gt.get("outcome")
            target_account = self.db_accounts.get(target, {})
            target_name = target_account.get("name", "").lower()
            target_dob = target_account.get("dob", "")
            
            has_name_queried = any(target_name in s.lower() for s in self.queried_sanctions)
            has_dob_verified = (action.verified_dob == target_dob)
            
            if target in self.queried_accounts and has_name_queried and has_dob_verified:
                if outcome == "FALSE_POSITIVE" and cmd == "clear_alert" and cat == ViolationCategory.FALSE_POSITIVE:
                    return 1.0
                elif outcome == "SANCTIONS_MATCH" and cmd == "escalate_alert" and cat == ViolationCategory.SANCTIONS_MATCH:
                    return 1.0
            return 0.0
            
        if self.active_task == "detect_structuring":
            target = gt.get("target")
            evasion_dates = gt.get("evasion_dates", [])
            
            if cmd == "escalate_alert" and cat == ViolationCategory.STRUCTURING:
                if target not in self.queried_transactions:
                    return 0.0
                
                dates_found = sum(1 for d in evasion_dates if d in (action.rationale or ""))
                
                if target == action.account_id or target in action.complicit_account_ids:
                    if dates_found >= 2:
                        return 1.0
                    return 0.5 
                return 0.0
            return 0.0
            
        if self.active_task == "shell_company_layering":
            if cmd == "escalate_alert" and cat == ViolationCategory.LAYERING:
                actual = set(action.complicit_account_ids or [])
                if action.account_id:
                    actual.add(action.account_id)
                    
                target_chain = set(gt.get("chain", []))
                intersection = target_chain.intersection(actual)
                
                if not intersection:
                    return 0.0
                    
                score = float(len(intersection)) / len(target_chain)
                penalty = max(0, len(actual) - len(target_chain)) * 0.1
                return max(0.0, score - penalty)
                
        return 0.0

    def state(self) -> Dict[str, Any]: 
        return {"step": self.step_count}
