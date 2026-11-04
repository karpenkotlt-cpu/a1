from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="APP_"
    )

    app_name: str = "Smart Quote & CAM-Costing System"
    debug: bool = False
    secret_key: str = "dev-insecure-secret-key-change-me"
    access_token_expire_minutes: int = 480
    cors_origins: list[str] = ["http://localhost:3000"]
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/quote_costing"
    )

    # OpenSCAD: kill-switch + автопоиск бинарника (env -> backend/vendor -> PATH
    # -> Program Files). См. backend/scripts/download_openscad.ps1.
    openscad_bin: str = ""
    # Manifold-снапшот справляется с реальными деталями за секунды, поэтому
    # щедрый таймаут безопасен; CGAL 2021.01 мог рендерить минуты.
    openscad_timeout_s: int = 60
    openscad_enabled: bool = True
    scad_max_code_bytes: int = 100_000
    # Предохранитель от аномальных сеток: 50 МБ ≈ 1 млн треугольников
    # (three.js тянет; >20 МБ дают только $fn>~500 или избыточные операции)
    scad_max_stl_mb: int = 50
    # Запрет include/use/import/surface — изоляция ФС сервера от кода пользователя
    scad_block_file_io: bool = True


settings = Settings()
