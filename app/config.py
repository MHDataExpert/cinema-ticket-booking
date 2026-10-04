from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://ticket:ticket@localhost:5432/ticketmaster"
    demo_user_id: str = "demo-user-1"
    reservation_ttl_minutes: int = 10
    sweep_interval_seconds: int = 60

    class Config:
        env_file = ".env"


settings = Settings()
