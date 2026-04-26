import uvicorn
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openenv.core.env_server import create_fastapi_app
from models import AMLAction, AMLObservation
from env import AMLEnv

app = create_fastapi_app(
    AMLEnv, 
    AMLAction, 
    AMLObservation, 
    max_concurrent_envs=1
)

def main():
    """Entry point for openenv-core validator."""
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
