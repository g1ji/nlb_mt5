import os

from dotenv import dotenv_values

config = dotenv_values(".env")


class Config:
    MYSQL_HOST = config.get("MYSQL_HOST") or "localhost"
    MYSQL_USER = config.get("MYSQL_USER") or "root"
    MYSQL_PASSWORD = config.get("MYSQL_PASSWORD") or ""
    MYSQL_DB = config.get("MYSQL_DB") or "video"

    SECRET_KEY = config.get("SECRET_KEY") or "r4jd3v1d3oed170rcr34t3eby61ji7ec"

    JSON_MODAL_PATH = os.path.join(os.path.dirname(__file__), "modal.json")
    BASE_DIR = os.getcwd()
    JOBS_DIR = config.get("JOBS_DIR") or os.path.join( "jobs")
    VIDEO_UPLOAD_DIR = config.get("VIDEO_UPLOAD_DIR") or os.path.join(
        os.path.join(BASE_DIR, "upload"), "video"
    )
    VIDEO_MERGED_DIR = config.get("VIDEO_MERGED_DIR") or os.path.join(
        os.path.join(BASE_DIR, "upload"), "merged"
    )
    ALLOWED_EXTENSIONS = {"mp4", "avi"}
    VIDEO_MAX_SIZE_MB = int(config.get("VIDEO_MAX_SIZE_MB") or 2)
    VIDEO_MAX_SIZE_BYTES = VIDEO_MAX_SIZE_MB * 1024 * 1024

    PORT = config.get("PORT") or 5000


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
