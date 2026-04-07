import asyncio
import os
import json
import time
from openai import OpenAI
from models import AMLAction, ViolationCategory
from env import AMLEnv

API_KEY = os.getenv("HF_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.groq.com/openai/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")
TASK_NAME = os.getenv("AML_TASK", "false_positive_sanctions")

SYSTEM_PROMPT = """
You are a Lead AML Investigator. Your goal is to solve the alert efficiently.

### GETTING STARTED:
Look at the 'alert_trigger' to find the target Account ID. Do NOT query the alert_id itself.

### INVESTIGATION RULES:
1. STRUCTURING: Investigate transaction history for obvious evasion of currency reporting thresholds. Once confirmed, 'escalate_alert' with category 'STRUCTURING'. You MUST list the exact dates (YYYY-MM-DD) of the suspicious deposits in your 'rationale'.
2. LAYERING: Trace funds through the network. Follow large 'wire_transfer' transactions. When you find an account receiving a wire, you MUST `query_transactions` on that new account to see where they forward the money. Keep following the money. You have NOT finished the trace until you find a final destination account that receives a wire but does NOT send any wire transfers out. Do NOT escalate until you hit this dead end. 'escalate_alert' with category 'LAYERING' and list EVERY single account in the chain in 'complicit_account_ids'.
3. SANCTIONS ALERTS: For name-match alerts, 'query_account' to get the customer's full Name and DOB. Then 'search_sanctions' using that exact name. If it's a false positive, 'clear_alert' with 'FALSE_POSITIVE'. If it IS a match, 'escalate_alert' with 'SANCTIONS_MATCH'. You MUST populate the 'verified_dob' field with the account holder's DOB (YYYY-MM-DD).

IMPORTANT: Transactions are sorted chronologically by date. If a query returns multiple pages, you MUST use the 'page' parameter to scan through the history until you find the evidence. Stop and ESCALATE or CLEAR only when you have definitive proof.

### SCHEMA:
{
  "command": "query_account" | "query_transactions" | "search_sanctions" | "escalate_alert" | "clear_alert",
  "account_id": "string",
  "search_name": "string or null",
  "violation_category": "STRUCTURING" | "LAYERING" | "SANCTIONS_MATCH" | "FALSE_POSITIVE" | "NONE",
  "complicit_account_ids": ["string"],
  "verified_dob": "string (YYYY-MM-DD) or null",
  "rationale": "string",
  "page": "integer (default 1)"
}
"""

def log_start(t, e, m): 
    print(f"[START] task={t} env={e} model={m}", flush=True)

def log_step(s, a_str, r, d, e): 
    print(f"[STEP] step={s} action={a_str} reward={r:.2f} done={str(d).lower()} error={e or 'null'}", flush=True)

def log_end(s, st, sc, r): 
    print(f"[END] success={str(s).lower()} steps={st} score={sc:.3f} rewards={','.join(f'{x:.2f}' for x in r)}", flush=True)

def get_model_action(client, step, last_obs, history) -> AMLAction:
    h_str = "\n".join(history[-15:]) if history else "Start"
    prompt = f"Step {step}/15\n[HISTORY (Past Findings)]\n{h_str}\n\n[CURRENT OBSERVATION]\n{last_obs}\n\nJSON:"
    
    last_error = ""
    for attempt in range(3):
        try:
            res = client.chat.completions.create(
                model=MODEL_NAME, 
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT}, 
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1, 
                response_format={"type": "json_object"}
            )
            
            content = res.choices[0].message.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
                
            data = json.loads(content.strip())
            
            if not data.get("violation_category") or str(data.get("violation_category")).lower() == "null":
                data["violation_category"] = "NONE"
            else:
                data["violation_category"] = str(data["violation_category"]).upper()
                
            if data.get("complicit_account_ids") is None:
                data["complicit_account_ids"] = []
            if data.get("page") is None:
                data["page"] = 1
            if data.get("rationale") is None:
                data["rationale"] = "No rationale provided"
                
            return AMLAction(**data)
        except Exception as e:
            last_error = str(e).replace('\n', ' ')
            if "429" in last_error or "rate limit" in last_error.lower() or "too many" in last_error.lower():
                time.sleep(15)
            else:
                time.sleep(2)
            continue
            
    return AMLAction(
        command="query_account", 
        account_id="ERROR", 
        rationale=f"Exception: {last_error[:200]}", 
        violation_category=ViolationCategory.NONE, 
        page=1
    )

async def main():
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    env = AMLEnv()
    history, rewards = [], []
    steps = 0
    final_task_score = 0.0
    
    log_start(TASK_NAME, "aml_fincrime_investigator", MODEL_NAME)
    
    try:
        obs = env.reset(task_name=TASK_NAME)
        for step in range(1, 16):
            action = get_model_action(client, step, obs.model_dump_json(), history)
            obs, reward, done, info = env.step(action)
            
            if "task_score" in info and info["task_score"] > 0:
                final_task_score = info["task_score"]
                
            rewards.append(reward)
            steps = step

            target_str = action.account_id or action.search_name or "null"
            action_log_str = f"{action.command}('{target_str}')"
            
            err_msg = action.rationale if action.account_id == "ERROR" else None
            log_step(step, action_log_str, reward, done, err_msg)
            
            db_snippet = obs.database_response.replace('\n', ' | ')[:150]
            target = action.account_id or action.search_name
            history.append(f"Step {step}: {action.command} on {target} (Page {action.page}) -> Found: {db_snippet}")
            
            if done:
                break
    finally:
        is_success = final_task_score >= 0.1
        log_end(is_success, steps, final_task_score, rewards)

if __name__ == "__main__":
    asyncio.run(main())
