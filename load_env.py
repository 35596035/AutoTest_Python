import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values, load_dotenv


ENV_FIELDS = {
    "BASE_URL": "BASE_URL",
    "TEST_USERNAME": "TEST_USERNAME",
    "TEST_PASSWORD": "TEST_PWD",
    "TEST_CHANGE_PASSWORD": "TEST_CH_PWD",
}


@dataclass(frozen=True)
class Config:
    BASE_URL: str
    TEST_USERNAME: str
    TEST_PWD: str = field(repr=False)
    TEST_CH_PWD: str = field(repr=False)

def env_path() -> Path:
    return Path(__file__).resolve().parent / os.getenv("ENV_FILE", ".env")


def env_defaults() -> dict[str, str]:
    values = dotenv_values(env_path())
    return {key: os.environ.get(key, values.get(key) or "") for key in ENV_FIELDS}


def load_config() -> Config:
    load_dotenv(dotenv_path=env_path())
    return Config(**{name: os.environ[key] for key, name in ENV_FIELDS.items()})
