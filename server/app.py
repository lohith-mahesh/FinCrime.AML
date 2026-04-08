import uvicorn
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openenv.core.env_server import create_fastapi_app
from models import AMLAction, AMLObservation
from env import AMLEnv

# Explicitly define the tasks for the server to expose
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
    tasks=TASKS,  # <--- THIS WAS MISSING
    max_concurrent_envs=1
)

def main():
    """Entry point for openenv-core validator."""
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
