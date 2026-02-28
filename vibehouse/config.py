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
    ALLOWED_ORIGINS: str = "*"

    # Trello
    TRELLO_API_KEY: str = "mock_trello_key"
    TRELLO_API_SECRET: str = "mock_trello_secret"

    # SendGrid
    SENDGRID_API_KEY: str = "mock_sendgrid_key"
    FROM_EMAIL: str = "no-reply@vibehouse.app"

    # Twilio
    TWILIO_ACCOUNT_SID: str = "mock_twilio_sid"
    TWILIO_AUTH_TOKEN: str = "mock_twilio_token"
    TWILIO_FROM_NUMBER: str = "+15555555555"

    # AI Provider (OpenAI-compatible)
    AI_API_KEY: str = "mock_ai_key"
    AI_BASE_URL: str = "https://api.openai.com/v1"
    AI_MODEL: str = "gpt-4o"

    # Google Maps
    MAPS_API_KEY: str = "mock_maps_key"

    # Stripe
    STRIPE_SECRET_KEY: str = "mock_stripe_key"
    STRIPE_PUBLISHABLE_KEY: str = "mock_stripe_pub_key"
    STRIPE_WEBHOOK_SECRET: str = ""

    # Storage
    STORAGE_BACKEND: str = "local"
    STORAGE_LOCAL_PATH: str = "/app/storage"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    S3_BUCKET: str = "vibehouse-uploads"

    # App
    APP_ENV: str = "development"
    APP_URL: str = "http://localhost:8000"
    LOG_LEVEL: str = "INFO"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
