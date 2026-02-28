from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://vibehouse:vibehouse_dev@db:5432/vibehouse"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Security
    SECRET_KEY: str = "dev-secret-key-not-for-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Trello
    TRELLO_API_KEY: str = "mock_trello_key"
    TRELLO_API_SECRET: str = "mock_trello_secret"

    # SendGrid
    SENDGRID_API_KEY: str = "mock_sendgrid_key"

    # Twilio
    TWILIO_ACCOUNT_SID: str = "mock_twilio_sid"
    TWILIO_AUTH_TOKEN: str = "mock_twilio_token"
    TWILIO_FROM_NUMBER: str = "+15555555555"

    # AI Provider
    AI_API_KEY: str = "mock_ai_key"

    # Google Maps
    MAPS_API_KEY: str = "mock_maps_key"

    # Storage
    STORAGE_BACKEND: str = "local"
    STORAGE_LOCAL_PATH: str = "/app/storage"

    # App
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
