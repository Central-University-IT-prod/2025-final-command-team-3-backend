import os


class Settings:
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
    MINIO_PUBLIC_URL = os.getenv("MINIO_PUBLIC_URL", "https://prod-team-3-uad8jq68.REDACTED:8005")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME", "movies")
    MINIO_SECURE = os.getenv("MINIO_SECURE", "False").lower() == "true"
    PROXY = os.getenv("PROXY", "'REDACTED'")
    PUBLIC_URL = os.getenv("PUBLIC_URL", "https://prod-team-3-uad8jq68.REDACTED")

settings = Settings()