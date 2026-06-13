from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    telegram_bot_token: str = ""
    public_base_url: str = "http://localhost:8000"
    app_scheme: str = "liverflapcheck"
    # Public redirect page that launches the app (hosted by the iOS teammate).
    # If set, the "Open app" button points here directly and our own /open
    # bridge (and ngrok) is not needed.
    app_open_url: str = ""
    api_key: str = ""
    patients_file: str = "patients.json"

    # Shared MongoDB (team cluster). If empty, falls back to the JSON file store.
    mongodb_uri: str = ""
    mongodb_db: str = "liverlink"

    @property
    def telegram_api_base(self) -> str:
        return f"https://api.telegram.org/bot{self.telegram_bot_token}"


settings = Settings()
