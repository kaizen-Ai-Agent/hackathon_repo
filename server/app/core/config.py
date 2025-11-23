from pydantic import BaseSettings, AnyUrl

class Settings(BaseSettings):
    ENV: str = "production"
    DATABASE_URL: AnyUrl
    REDIS_URL: str
    WATSONX_APIKEY: str
    WATSONX_URL: str
    ORCHESTRATE_APIKEY: str
    GOOGLE_CREDS_PATH: str
    PGBOUNCER_URL: str | None = None
    SCHEDULER_TIMEZONE: str = "UTC"

class Config:
    env_file = ".env"

settings = Settings()