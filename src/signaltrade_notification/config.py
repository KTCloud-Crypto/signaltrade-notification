from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    environment: str = "development"
    log_level: str = "INFO"
    aws_region: str = "ap-northeast-2"
    sqs_endpoint_url: str = ""
    sqs_notification_queue_name: str = "signaltrade-notifications"
    sqs_notification_visibility_timeout_seconds: int = 120
    redis_url: str = "redis://localhost:6379/0"
    notification_processing_ttl_seconds: int = 120
    notification_dedup_ttl_seconds: int = 604800
    telegram_bot_token: str = ""
    telegram_api_base_url: str = "https://api.telegram.org"
    telegram_api_timeout_seconds: float = 5.0
    metrics_enabled: bool = True
    notification_metrics_port: int = 9104
    identity_service_url: str = "http://identity-api:8000"
    strategy_service_url: str = "http://strategy-api:8000"
    trading_service_url: str = "http://trading-api:8000"
    portfolio_service_url: str = "http://portfolio-api:8000"
    internal_service_token: str = ""
    service_timeout_seconds: float = 5.0


settings = Settings()
