from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "User Info"
    ENV: str = "development"
    DEBUG: bool = 0

    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    FRONTEND_URL: str
    USER_POOL_ID: str
    COGNITO_DOMAIN: str
    CLIENT_ID: str
    CLIENT_SECRET: str
    IDENTITY_POOL_ID: str
    AWS_REGION_NAME: str
    S3_BUCKET_NAME: str
    JWKS_TTL: int = 3600

    ALLOWED_ORIGINS: str

    @property
    def database_url(self) -> str:
        """Assemble full database URL from parts."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
