# FinCrime AML Investigator: A Reinforcement Learning Benchmark

## Overview
The FinCrime Anti-Money Laundering (AML) Investigator is a highly rigorous, multi-step Reinforcement Learning (RL) benchmark designed to evaluate the deductive reasoning, context-window management, and tool-use capabilities of frontier Large Language Models (LLMs). 

Unlike standard QA benchmarks, this environment simulates a dynamic, adversarial financial database. Agents must navigate realistic transactional ledgers, isolate illicit financial behavior obfuscated by high-volume baseline noise, and escalate alerts using a strictly typed JSON schema. The environment actively punishes reward-farming, blind guessing, and hallucinated queries.

## Environment Architecture

The environment operates on a standard RL continuous loop (`reset`, `step`) and is strictly deterministic for baseline reproducibility while supporting dynamic generation across concurrent sessions.

### State Generation (In-Memory)
To prevent Docker file I/O concurrency crashes during parallelized evaluation, the environment relies on dynamic, in-memory graph generation. Upon calling `env.reset()`, the system generates a synthesized financial network of 200 nodes (accounts) and thousands of transactions. The topology is controlled via a task-specific seed hash to ensure deterministic evaluation by automated judges.

### Action Space
Agents interact with the environment by outputting strictly formatted JSON objects matching the following schema:
* `command` (str): The specific tool to invoke (`query_account`, `query_transactions`, `search_sanctions`, `escalate_alert`, `clear_alert`).
* `account_id` (str, optional): The target ID for ledger or profile queries.
* `search_name` (str, optional): The target name for database string-matching.
* `violation_category` (str): The final classification (`STRUCTURING`, `LAYERING`, `SANCTIONS_MATCH`, `FALSE_POSITIVE`, `NONE`).
* `complicit_account_ids` (List[str]): Downstream nodes involved in network-based crimes.
* `verified_dob` (str, optional): Extracted proof for identity verification tasks.
* `rationale` (str): The investigative proof and reasoning.
* `page` (int): Pagination control for iterating through high-volume ledgers.

### Observation Space
At each step, the agent receives an observation mapping containing:
* `alert_trigger`: The initial breadcrumb (e.g., "Alert: ACC-1030 High-Value Wires").
* `database_response`: The simulated terminal output of the query (paginated ledger rows, JSON profiles, or match lists).
* `documented_evidence`: An internal working-memory array of successfully queried nodes.
* `reward`: The step-specific continuous reward signal.
* `done`: Boolean termination flag.

## Task Definitions and Grading Mechanics

The benchmark evaluates models across three distinct financial crime typologies. Each task utilizes a specialized grader designed to neutralize common LLM exploitation strategies.

### 1. Detect Structuring (Smurfing)
* **Objective:** Identify multiple cash deposits designed to evade regulatory reporting thresholds.
* **Challenge:** Illicit transactions are chronologically buried inside a high-volume "haystack" of overlapping baseline noise (payroll, utility payments). The agent must actively utilize the `page` parameter to traverse the timeline.
* **Strict Grading:** It is insufficient to merely identify the account. The agent must explicitly extract the exact dates of the structuring deposits and include them in the `rationale` string. Failure to provide explicit date proof results in a 50% score penalty, preventing blind guessing.

### 2. Shell Company Layering
* **Objective:** Trace illicit funds moving from a source account through multiple mid-layer shell entities to a final destination.
* **Challenge:** The agent must differentiate between routine `vendor_payment` noise and illicit `wire_transfer` movements, sequentially querying the downstream nodes to map the full graph.
* **Fractional Intersection Grading:** The task utilizes a mathematically rigorous intersection-over-union metric. The agent is scored based on the precise subset of the network it correctly identifies. To prevent array-spamming (reward hacking), the grader applies a strict penalty (`-0.10`) for every incorrect or hallucinated account ID included in the submission.

### 3. False Positive Sanctions Resolution
* **Objective:** Differentiate between true sanctions matches and false positives based on secondary identity markers (Date of Birth / Country).
* **Challenge:** The agent must cross-reference account profile data against the sanctions registry. 
* **Type-Safe Grading:** The grader bypasses brittle string-matching on the rationale and instead demands the agent autonomously populate a dedicated `verified_dob` Pydantic field with the extracted `YYYY-MM-DD` string, testing the model's ability to map unstructured data to strict schema requirements.

## Adversarial Safeguards

This benchmark is hardened against common RL optimization exploits:

1. **Positive Circuit Mitigation (Anti-Farming):** Breadcrumb rewards (`+0.10` / `+0.15`) are strictly locked to the critical path. Agents cannot artificially inflate their score by indiscriminately querying unrelated nodes in the database.
2. **Chronological Obfuscation:** Unlike naive ledgers that sort by transaction amount (which inadvertently pins evidence to Page 1), this environment sorts transactions chronologically descending. Illicit activity is mathematically guaranteed to be surrounded by overlapping benign transactions, enforcing genuine context-window utilization.
3. **Amnesia Penalties:** Duplicate queries to the same node invoke a softened penalty (`-0.15`). This prevents fatal score wipes from minor LLM amnesia while still effectively discouraging infinite looping behavior.
4. **Pydantic Null-Catching:** The environment interface includes sanitization layers to catch and convert explicit `null` outputs into safe default strings, preventing strict JSON parsers from triggering false-negative container crashes.

## Installation and Execution

Ensure Docker and Python 3.10+ are installed. 

### Local Baseline Evaluation
To run the evaluation script locally using the optimized baseline agent:
```bash
pip install -r requirements.txt
export HF_TOKEN="your_api_key"
export AML_TASK="shell_company_layering" # Options: detect_structuring, false_positive_sanctions
python3 inference.py
```
### Automated Submission Validation

To test container compatibility and parser compliance prior to final evaluation:
```bash
chmod +x validate-submission.sh
./validate-submission.sh https://<YOUR-SPACE-NAME>.hf.space .
```
### Logging and Parsing Compatibility

Standard output logging adheres strictly to benchmark parser expectations. Action strings are converted from JSON to safe functional formats (e.g., query_transactions('ACC-1030')), and final scores are consistently formatted to three decimal places (score=1.000) to ensure 100% compatibility with regex-based automated judges.

## Baseline Evaluation Scores
Using the `llama-3.3-70b-versatile` model as our baseline agent, the environment yielded the following reproducible scores:
* **Task 1 (Detect Structuring):** 1.000 (Success in 15 steps)
* **Task 2 (Shell Company Layering):** 0.750 (Partial success in 8 steps)
* **Task 3 (False Positive Sanctions):** 1.000 (Success in 3 steps)
