from app import create_app
from dotenv import dotenv_values

config = dotenv_values(".env")

if __name__ == "__main__":
    APP_ENV = config.get("APP_ENV") or "default"
    app = create_app(APP_ENV)
    app.run(host="0.0.0.0", port=app.config.get("PORT"))