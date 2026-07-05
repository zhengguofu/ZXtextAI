from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "ZXtextAI PyTools"
    enable_easyocr: bool = True
    easyocr_languages: str = "ch_sim,en"
    easyocr_gpu: bool = False
    max_image_bytes: int = 5 * 1024 * 1024

    model_config = SettingsConfigDict(
        env_prefix="PYTOOLS_",
        env_file=".env",
        extra="ignore",
    )

    @property
    def languages(self) -> list[str]:
        return [item.strip() for item in self.easyocr_languages.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
