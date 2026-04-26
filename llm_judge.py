import os
import json
from openai import OpenAI

def evaluate_rationale(task_id: str, action: dict, ground_truth: dict) -> float:
    api_key = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")
    base_url = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
    model = os.getenv("JUDGE_MODEL") or os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"

    if not api_key or os.getenv("DISABLE_LLM_JUDGE", "false").lower() == "true":
        return 0.5

    client = OpenAI(base_url=base_url, api_key=api_key)

    prompt = f"""
    Evaluate the AML investigator's rationale for escalating or clearing an alert.
    Task: {task_id}
    Ground Truth Facts: {json.dumps(ground_truth)}
    Agent Action & Rationale: {json.dumps(action)}

    Evaluate strictly from three perspectives:
    1. Compliance Analyst: Did they capture the basic facts?
    2. AML Director: Does the narrative connect the nodes logically?
    3. Federal Regulator: Is the evidence legally definitive and bulletproof?

    Output strict JSON:
    {{
        "analyst_score": float (0.0 to 1.0),
        "director_score": float (0.0 to 1.0),
        "regulator_score": float (0.0 to 1.0),
        "final_score": float (0.0 to 1.0)
    }}
    """

    try:
        res = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a multi-persona AML evaluation judge. Output only JSON."},
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
        
        final_score = float(data.get("final_score", 0.0))
        return max(0.0, min(1.0, final_score))
        
    except Exception:
        return 0.5