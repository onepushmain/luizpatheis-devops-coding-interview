from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    mongo_uri: str
    mongo_db_name: str

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings():
    """
    cached settings getter

    it can be overriden for fastapi testing,
    ref: https://fastapi.tiangolo.com/advanced/settings/#settings-and-testing
    """

    return Settings()
