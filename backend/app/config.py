from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Reads each field from an environment variable of the same name."""

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/payments"
    weight_cost: float = 0.3
    weight_latency: float = 0.2
    weight_reliability: float = 0.5
    explore_rate: float = 0.1
    gateway_timeout_s: float = 2.0
    max_attempts: int = 3
    history_size: int = 50


settings = Settings()
