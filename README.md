# AML FinCrime Investigator: A Generative Adversarial RL Firing Range

## The Executive Summary
Anti-Money Laundering (AML) investigation is a high-stakes cat and mouse game where the "mouse" evolves in real-time. This project presents a specialized Reinforcement Learning (RL) environment designed to train Large Language Models (LLMs) to act as Lead AML Investigators. Unlike static benchmarks, this environment utilizes a Generative Adversarial Financial Data (GAFD) engine where a 72B parameter "Launderer" dynamically generates obfuscated transaction ledgers to evade the investigator.

## The National Security Mandate: Why We Simulate
Financial institutions operate under a paradox: they possess the data necessary to train world-class investigative AI, but national security protocols and privacy laws (BSA, GDPR, and FinCEN mandates) prevent the release of this data. Sharing real-world AML patterns could expose systemic vulnerabilities to state actors or criminal syndicates. 

This project solves the "Data Desert" by providing a high-fidelity synthetic firing range. By simulating the enterprise banking stack through a Pydantic-validated environment, we allow for the development of expert investigative weights without ever touching sensitive PII (Personally Identifiable Information) or institutional secrets.

---

## Technical Specifications

### 1. Environment Architecture (The Stack)
The agent operates across three distinct enterprise application mocks, accessible via a unified API:
* **Core Banking (CB):** Handles `query_account`, `query_transactions`, and `freeze_account`.
* **Global Sanctions (GS):** Provides `search_sanctions` for name-match verification.
* **HR Portal (HR):** The final endpoint for `escalate_alert` or `clear_alert`.
* **The Scratchpad:** A persistence layer allowing the agent to utilize `save_to_notes` and `read_notes` to bypass context window drift during long-chain investigations.

### 2. The Reward Function: Forensic Shaping
The reward signal is designed to discourage "hallucinatory investigative drift":
* **Goal Reward:** Up to +1.0 for perfect identification of shell company chains or structuring dates.
* **Efficiency Penalty:** -0.05 per step to encourage rapid resolution.
* **Logic Penalty:** -0.10 for attempting to use tools in the wrong application (e.g., searching sanctions in Core Banking).
* **The Loop Breaker:** -0.15 for duplicate queries, preventing the common LLM failure mode of infinite query loops.

---

## Comparative Analysis: 70B Zero-Shot vs. 8B Trained

### The Baseline: Llama-3.3-70B (Untrained)
During evaluation, the untrained 70B model exhibited "Zero-Shot Myopia." While it could interpret the `SYSTEM_PROMPT` effectively, it failed at the **state-machine logic** of a multi-step investigation. 
* **The Loop Trap:** The 70B model often became stuck in repetitive `query_transactions` loops, failing to recognize that it already possessed the necessary evidence.
* **Evidence Attrition:** Without the trained heuristic to use the **Scratchpad**, the 70B model would "forget" account IDs from Step 2 by the time it reached Step 8.

![Untrained Baseline Results](untrained_reward_curve.jpeg)

### The Improvement: Llama-3-8B (PPO-Tuned)
By applying Proximal Policy Optimization (PPO), the 8B model developed a specialized investigative heuristic. 
* **Heuristic Discovery:** The model learned that the highest reward density came from tracing wire transfers to their "dead end" rather than escalating at the first suspicious node.
* **Tool Fluency:** The 8B model achieved near-perfect compliance with the Enterprise App mapping, eliminating the "Access Denied" penalties that tanked the baseline scores.

![Trained PPO Progress](training_reward_curves.png)

---

## Practicality and Niche Value
This project is not just a hackathon entry: it is a blueprint for practical banking deployment. 
* **API-Ready:** The environment is designed to be implementable with any standard RESTful banking API. A financial institution could swap the `data_generator.py` for a real-world (anonymized) data stream to turn this into a production-grade investigator.
* **The "Launderer" Innovation:** By including a live adversary that adapts to the agent, we solve the "stale model" problem where AI becomes obsolete as soon as criminals change their patterns.

## Shortcomings and Real-World Constraints
* **Non-Deterministic Adversary:** Because the Launderer is a 72B LLM, the environment difficulty can vary slightly between episodes, introducing noise into the training signal.
* **Schema Constraints:** The current agent is restricted to JSON outputs, which limits its ability to provide the nuanced, prose-heavy "Narrative of Suspicious Activity" required by federal regulators.
* **Token Latency:** High-fidelity data generation introduces significant latency per step, making real-time training on consumer hardware difficult.

## Installation

```bash
# Clone the repository
git clone [https://github.com/user/aml-fincrime-investigator](https://github.com/user/aml-fincrime-investigator)

# Install enterprise dependencies
pip install -r requirements.txt

# Launch the investigation server
uvicorn server.app:app --host 0.0.0.0 --port 7860
