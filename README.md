# AML FinCrime Investigator
## OpenEnv Hackathon (India 2026) Submission

> **TL;DR:** Financial Crime Investigation requires deep, multi-step orchestration across fragmented enterprise applications with high penalties for failure. We built an **OpenEnv compliant simulation** featuring a **Live Adversarial Launderer LLM** that dynamically generates obfuscated crime topologies. Using **PPO (Reinforcement Learning)**, we trained a small **Llama-3-8B** model to completely outperform a zero-shot **Llama-3.3-70B** model, proving that targeted RL environments can distill complex, long-horizon professional workflows into edge-deployable models.

---

## Alignment with Hackathon Themes

Our submission is highly ambitious and purposefully spans four of the core OpenEnv Hackathon themes. We designed this environment to be a comprehensive testing ground for advanced agentic behavior.

### **Theme 1: Multi-Agent Interactions**
The environment is not a static dataset. It features a **Live Adversarial Launderer Agent**. During the "Shell Company Layering" task, the investigator agent must trace illicit funds across multiple accounts. If the investigator takes too long, the environment triggers the Launderer LLM, which actively generates a new shell company and wires the funds to a new node mid-investigation. The investigator must model the adversary's evasion strategy (theory of mind) and realize that the state of the world has changed. This drives emergent strategic behavior, forcing the investigator to continuously query the latest transactions rather than relying on stale data.

### **Theme 2: Long-Horizon Planning and Instruction Following**
Investigating a layering scheme is the definition of a deep, multi-step trajectory with delayed, sparse rewards. The agent must parse the initial alert, open the core banking application, read heavily paginated transaction logs, recursively follow receiver IDs, save critical findings to an internal scratchpad, and finally escalate the alert in an HR portal. A single mistake, such as forgetting the original suspect's ID or querying the wrong app, disrupts the chain. The environment pushes the agent beyond shallow next-token prediction by forcing it to build durable internal representations of the financial network over 15 to 20 steps before receiving a final completion reward.

### **Theme 3.1: World Modeling (Professional Tasks)**
We built a professional, partially observable enterprise ecosystem. The agent interacts with three distinct tools: **Core Banking, Global Sanctions, and an HR Portal**. The model is expected to do the hard work of matching database records instead of exploiting shortcuts. For example, in the sanctions task, the agent cannot simply escalate an alert based on a name match. It must maintain a consistent internal state, open the core banking app to retrieve the suspect's Date of Birth, open the sanctions app to find the target's Date of Birth, and apply causal reasoning to compare them before clearing or escalating the alert.

### **Theme 4: Self-Improvement**
We implemented an adaptive curriculum driven by recursive self-improvement. The data generator leverages an LLM to build the financial ledgers. When generating a new episode, the environment passes the investigator's previous task score back to the Launderer LLM as feedback. If the investigator easily solved the previous alert (e.g., scoring 0.99), the Launderer is prompted to escalate the difficulty by adding heavier baseline noise and more complex transaction obfuscation. Rather than optimizing a fixed task, the environment dynamically evolves to continuously amplify the investigator's skills.

---

## The Problem: The FinCrime Capability Gap

Money laundering costs the global economy an estimated **2 Trillion Dollars** annually. To combat this, Anti-Money Laundering (AML) investigators must navigate a fragmented, noisy, and highly adversarial digital ecosystem. They do not look at a single CSV file. They jump between mainframes, external databases, and internal escalation portals.

Current state of the art Large Language Models fail at this task for several reasons:
* **Context Collapse:** Context windows get overwhelmed with irrelevant ledger noise.
* **Logical Rigor:** Strict causal logic is required; you cannot freeze an account without definitive, documented proof. LLMs tend to jump to conclusions.
* **Tool Hallucination:** Models frequently attempt to query banking transactions inside an HR portal or vice versa.

The AML FinCrime Investigator environment exists to teach an LLM a capability it currently lacks: **durable, structured, multi-app investigation with delayed sparse rewards.**

---

## The Data Dilemma: National Security vs. AI

A major roadblock in training AI for Financial Crime is the absolute lack of open-source datasets. Releasing the exact topological structures of active money laundering syndicates poses a severe **National Security Risk**. Such data is heavily protected under the Bank Secrecy Act (BSA) and international privacy laws, because releasing it would actively instruct cartels and sanctioned states on how current banking algorithms operate.

### **The Shortcomings of Simulated Data**
Because we cannot use real SWIFT network dumps, we are forced to rely on simulated data. This comes with inherent shortcomings:
* **Chaos vs. Structure:** Real bank data is chaotic (misspellings, timezone issues, currency fluctuations). Our simulation is necessarily cleaner.
* **Interface Complexity:** Real investigators use complex SQL or Graph databases; we simplified this into a rigid JSON API for the Gym-style environment.
* **Trajectory Scale:** Real layering might span years and dozens of banks; our environment limits episodes to twenty steps for training stability.

### **Our Solution: The Adaptive Launderer Agent**
To counteract the sterility of simulated data, we introduced the **Launderer LLM**. By using a secondary LLM to generate the ledger data and actively evade the investigator during the episode, we reintroduce the chaotic entropy and adversarial nature of real-world financial crime that static simulated datasets lack.

---

## The Environment Mechanics

Built entirely on the **OpenEnv framework**, the environment requires the agent to act as a Lead AML Investigator.

### **The Observation Space**
The agent receives an observation containing:
1.  The alert ID and trigger.
2.  The database response from the last API call.
3.  A documented evidence log of queried records.
4.  A **scratchpad** for tracking state over extended trajectories.

### **The Action Space**
The agent must specify the correct target app and command:
* **Core Banking:** `query_account`, `query_transactions`, `freeze_account`, `save_to_notes`, `read_notes`.
* **Global Sanctions:** `search_sanctions`.
* **HR Portal:** `escalate_alert`, `clear_alert`.

### **The Three Core Tasks**
1.  **False Positive Sanctions (Easy):** Cross-reference a flagged account's DOB with the Sanctions database. If they do not match, clear the alert.
2.  **Detect Structuring (Medium):** Scan paginated transactions for multiple cash deposits just below the $10,000 reporting threshold over consecutive days.
3.  **Shell Company Layering (Hard):** Recursively follow large wire transfers from account to account until hitting a dead-end shell company.

---

## Reward and Training Pipeline

We designed a highly coherent, anti-gaming reward signal. A naive LLM that randomly outputs an escalate command gets heavily penalized.

### **Dense Progress Signals**
* **+0.15** for discovering and querying a new, valid complicit account in a layering chain.
* **+0.10** for a valid sanctions search.

### **Penalties**
* **-0.15** for duplicate queries (forces forward momentum).
* **-0.10** for using a command in the wrong enterprise app.
* **-0.05** base step penalty (encourages efficiency).

### **Sparse Final Rubric**
To achieve the maximum **+1.0 Task Score**:
* **Structuring:** Agent must include the exact evasion dates in its rationale field.
* **Layering:** Agent must array all nodes of the network in the complicit account IDs list.
* *Partial chains receive a heavily discounted score.*

---

## Extensive Results and Analysis: 8B David vs. 70B Goliath

To prove the efficacy of our environment, we evaluated a zero-shot, untrained **Llama-3.3-70B-Instruct** against a PPO-trained **Llama-3-8B-Instruct**.

### **The Baseline: Why the Untrained 70B Failed**

![Baseline Evaluation](untrained_reward_curve.jpeg)

Despite its massive parameter count, the 70B model averaged a reward of barely **0.25** on the Layering task and **0.05** on the Structuring task.

**Failure Modes of the 70B Model:**
1.  **Context Collapse:** It would find the first shell company but forget the original suspect's ID by step ten. It failed to utilize the scratchpad, relying on a rolling context that filled with irrelevant ledger noise.
2.  **Impatience:** It exhibited a bias toward immediate resolution, escalating for "Structuring" after seeing a single transaction rather than paginating to find consecutive dates.
3.  **App Hallucination:** It frequently tried to execute sanctions searches while connected to the banking app.

### **The Triumph: How PPO Shaped the 8B Model**

![Reward Curve](training_reward_curves.png)

We trained **Llama-3-8B-Instruct** using Hugging Face TRL and **Proximal Policy Optimization (PPO)** over 200 epochs.

**How the 8B Model Dominated:**
1.  **Emergent Tool Use:** Around Epoch 60, the 8B model began actively using the `save-to-notes` command to store shell company IDs, allowing it to survive long sessions.
2.  **Mastering Pagination:** PPO taught the model to endure delayed rewards, learning to sequentially issue page requests rather than guessing blindly.
3.  **Precision Formatting:** The model learned to consistently populate the verified DOB and complicit account IDs JSON fields, pushing its Layering score to a rolling average of **0.90+**.

---

## Conclusion

The environment successfully forced a shallow next-token predictor to evolve into a structured planner. The 8B model achieved a significantly higher success rate than a model nearly ten times its size, proving that specialized RL environments are highly effective for teaching complex enterprise workflows.

---

## Quick Start and Reproduction

Judges can reproduce the environment and the training loop using the provided Colab Notebook. Ensure you have **Python 3.12** installed.

### **1. Run the Environment Server**
Install requirements and start the OpenEnv FastAPI server:
```bash
pip install -r requirements.txt
export OPENAI_API_KEY="your_api_key_here"
python app.py
```
### 2.View the Training Notebook

Open train.ipynb in Google Colab. The notebook uses the TRL PPOTrainer, loads Meta-Llama-3-8B-Instruct with LoRA adapters, and runs 300 epochs across all tasks.

### 3. Run Inference

To test a model without training:
```bash
python inference.py
```

### Repository Structure

    server/app.py: FastAPI server entrypoint (OpenEnv compliant)

    env.py: Core AMLEnv logic, reward mechanics, and grading rubrics

    models.py: Pydantic schemas for AMLAction and AMLObservation

    data_generator.py: The Launderer LLM dynamic data generation script

    llm_judge.py: Multi-persona LLM judge for evaluating Rationale

    inference.py: Evaluation script for running episodes

    train.ipynb: Hugging Face TRL and PPO Training Pipeline

    openenv.yaml: Hugging Face Space OpenEnv manifest

    reward_curve.png: Training evidence showing PPO improvement

    baseline_eval.png: Training evidence showing 70B zero-shot failure

### Final Note

The AML FinCrime Investigator goes beyond standard grid-world paradigms. By introducing a dynamic adversarial LLM into a multi-application professional workflow, we have created an environment that tests the absolute limits of LLM instruction following, tool use, and theory of mind reasoning. It proves that while data privacy restricts our access to real-world financial topologies, clever environment engineering can still create robust, highly capable AI investigators.
