# The Ghost in the Ledger: Training an 8B AI Detective to Hunt Adversarial Launderers

Two trillion dollars. Every single year, that’s the staggering amount of illicit capital that vanishes into the global financial system. It doesn’t just evaporate. It shatters into thousands of micro-transactions, bleeds through a labyrinth of international shell companies, and layers itself across borders until it looks entirely legitimate. 

The human analysts tasked with tracking this money—Anti-Money Laundering (AML) investigators—are fighting an asymmetric war. They don't get to stare at a clean, structured CSV file. Instead, they spend their days jumping between fragmented, archaic enterprise systems: core banking mainframes, global sanctions databases, and clunky HR escalation portals. It is a grueling, high-stakes game of connect-the-dots with delayed rewards. Miss one paginated transaction, and a sanctioned entity gets paid. 

When we entered the **OpenEnv Hackathon (India 2026)**, we set out to build an AI agent that could actually survive in this trench. We didn't want a shallow next-token predictor that just summarized text; we needed an autonomous detective capable of deep, multi-step orchestration across a simulated enterprise. 

But the moment we began architecture design, we crashed into an impenetrable wall: The Bank Secrecy Act. 

### The Data Dilemma and the Architect’s Shield

To train a Large Language Model to investigate financial crime, you need data. But the exact topological structures of active money laundering syndicates are highly classified. Releasing real-world SWIFT network dumps is a severe national security risk. If you publish exactly how the cartels and rogue states move money, you simultaneously publish the exact blueprints for how banking algorithms detect them. 

We had to rely on simulated data. But standard simulated datasets are inherently sterile. They lack the chaotic entropy, the misspelled aliases, and the active evasion tactics of real-world financial crime. To build a brilliant AI detective, we realized we first had to build a brilliant AI villain.

Inside our OpenEnv-compliant FastAPI server (`app.py`), we didn't just hardcode static ledgers. We engineered a multi-agent nightmare by injecting a **Live Adversarial Launderer LLM** (`data_generator.py`). 

Imagine our AI investigator booting up to tackle a "Shell Company Layering" task—the hardest of our three curriculum tiers. The investigator receives its `Observation Space`: an alert ID, an evidence log, and an empty scratchpad. It fires a `query_account` JSON command to the Core Banking API, finds a shell company, and begins recursively following the money. 

But the environment is watching. If our investigator takes too long paging through the logs, the environment triggers the Launderer LLM. Realizing the heat is on, the villain dynamically spins up a *new* shell company and wires the funds mid-investigation. 

Suddenly, our investigator is forced to employ Theory of Mind. It has to realize the state of the simulated world has changed, abandon its stale context window, and hunt down the fresh transactions. To make matters worse, we wired the environment for self-improvement. If our detective solved an alert too easily (scoring a 0.99), we passed that score back to the Launderer LLM. The villain would then escalate the baseline noise and obfuscation for the next episode.

### The Overconfident Goliath

To establish a baseline in this hellish environment, we brought in the heavy artillery: an untrained, zero-shot **Llama-3.3-70B-Instruct**. We dropped it into the environment, gave it a strict JSON API mapping to the three enterprise apps, and let it rip. 

It failed spectacularly. 

Despite 70 billion parameters of sheer reasoning power, it averaged a miserable sparse final reward of 0.25 on the Layering task and a flat 0.05 on the Structuring task. Watching the 70B model navigate the logs was like watching a genius with zero short-term memory. 

It suffered from massive context collapse. It would successfully track the first shell company, but by the tenth step of issuing `query_transactions` to paginate through the ledgers, the context window filled with irrelevant ledger noise. It completely forgot the original suspect’s ID. We had explicitly given it a `save_to_notes` API command to act as a scratchpad, but the 70B ignored it entirely. 

Worse, it was incredibly impatient. On the "Detect Structuring" task—which requires finding multiple cash deposits just below the $10,000 threshold over consecutive days—the 70B would call `escalate_alert` to the HR Portal the second it saw a single weird transaction. It refused to paginate to find the temporal proof. It even suffered from severe tool hallucination, attempting to run `search_sanctions` while still tightly coupled to the Core Banking API.

Raw parameter count simply couldn't solve a problem that demanded durable, long-horizon planning with delayed, sparse rewards.

### David's Crucible

We benched the 70B model. Instead of going bigger and more expensive, we went brutal. We took a much smaller model, **Meta-Llama-3-8B-Instruct**, loaded it with LoRA adapters, and threw it into a grueling training montage using Hugging Face TRL and Proximal Policy Optimization (PPO) over 200 epochs (`train.ipynb`).

We engineered a ruthless, anti-gaming reward pipeline (`env.py`) to mathematically beat the bad habits out of it. We fed it dense progress signals to keep it moving: +0.15 for discovering a valid complicit account in a layering chain, and +0.10 for a valid sanctions cross-reference. 

But the penalties were where the real learning happened. Every time the 8B model panicked and issued duplicate queries, we slapped it with a -0.15 penalty to force forward momentum. If it hallucinated an app—trying to escalate to HR while looking at the sanctions DB—it ate a -0.10 penalty. We even applied a -0.05 base step penalty to encourage maximum investigative efficiency. 

To achieve the ultimate +1.0 sparse final reward, the 8B model couldn't just guess. It had to perfectly format its Pydantic rationale (`models.py`), mathematically arraying all nodes of the money laundering network into a strict `complicit account IDs` JSON list.

For the first 60 epochs, it floundered. The Launderer LLM ran circles around it. The 8B model drowned in the paginated transaction logs, burning up its step counts and getting terminated by the environment.

Then, something incredible happened. The 8B model woke up. 

### The Master Detective Emerges

Right around Epoch 60, the PPO gradient updates aligned, and the 8B model developed emergent, long-horizon strategic behaviors that its 70B predecessor never grasped. 

Recognizing its own limited context window, it suddenly started aggressively calling the `save_to_notes` command. Whenever it found a suspicious receiver ID, it stashed it in the scratchpad. This allowed the tiny 8B model to survive massive, 20-step investigation trajectories without suffering context collapse. 

The harsh environment taught it patience. It stopped guessing blindly and learned to sequentially issue page requests, enduring the delayed gratification until it unearthed the exact consecutive dates required to prove a structuring crime. The tool hallucinations vanished. It seamlessly disconnected from the banking API, jumped into the sanctions database, executed a flawless search, and only escalated the alert when its causal reasoning matched. 

By the end of the 200-epoch training loop, our tiny 8B detective was pulling a rolling average score of 0.90+ on the hardest Layering tasks, completely outclassing the zero-shot 70B Goliath. 

We didn't just build a hackathon project. We proved a fundamental concept for the future of enterprise AI. You don't need a massive, hyper-expensive, cloud-based behemoth to orchestrate complex, multi-application professional workflows. By trapping a small model in an adversarial, specialized RL environment, you can force a shallow next-token predictor to evolve into a highly structured planner. 

The regulatory data privacy walls still stand. We may never get to train AI on the real financial ledgers of the criminal underworld. But with a clever OpenEnv server and a ruthless AI villain pushing the boundaries, the digital ghosts hiding in those ledgers just got a lot easier to catch.

***
*Developers and judges can reproduce the environment, boot the FastAPI server, and run the PPO training logs themselves. Spin up the repository, load the weights, and watch the detective work.*
