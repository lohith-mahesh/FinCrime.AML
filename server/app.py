import uvicorn
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openenv.core.env_server import create_fastapi_app
from models import AMLAction, AMLObservation, AMLReward
from env import AMLEnv

TASKS = [
    {
        "id": "false_positive_sanctions",
        "name": "Sanctions Resolution",
        "difficulty": "easy"
    },
    {
        "id": "detect_structuring",
        "name": "Structuring Detection",
        "difficulty": "medium"
    },
    {
        "id": "shell_company_layering",
        "name": "Shell Company Layering",
        "difficulty": "hard"
    }
]

app = create_fastapi_app(
    AMLEnv, 
    AMLAction, 
    AMLObservation, 
    max_concurrent_envs=1,
    tasks=TASKS
)

def main():
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
