import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

@dataclass(frozen=True)
class Config:
    BASE_URL: str
    TEST_USERNAME: str
    TEST_PWD: str
    TEST_CH_PWD: str

def load_config() -> Config:
    base_dir = Path(__file__).resolve().parent
    env_file = os.getenv("ENV_FILE", ".env")
    env_path = base_dir / env_file
    load_dotenv(dotenv_path=env_path)

    return Config(
        BASE_URL=os.environ["BASE_URL"],
        TEST_USERNAME=os.environ["TEST_USERNAME"],
        TEST_PWD=os.environ["TEST_PASSWORD"],
        TEST_CH_PWD=os.environ["TEST_CHANGE_PASSWORD"]
    )

config = load_config()