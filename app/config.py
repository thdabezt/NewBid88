from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "postgresql+psycopg://newbid:newbid@db:5432/newbid"
    db_pool_size: int = 10
    db_max_overflow: int = 10

    jwt_secret: str
    jwt_expire_minutes: int = 60
    bcrypt_rounds: int = 12

    snipe_window_seconds: int = 60
    snipe_extension_seconds: int = 60

    min_auction_seconds: int = 60
    max_auction_days: int = 30

    settle_interval_seconds: int = 5
    settle_batch: int = 100

    fee_rate: Decimal = Decimal("0")


settings = Settings()
