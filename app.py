import time
from app import create_app
from dotenv import dotenv_values
from mt5 import setup_account, terminate_all_metatrader5, remove_all_account

config = dotenv_values(".env")

if __name__ == "__main__":
    remove_all_account()
    time.sleep(2)
    terminate_all_metatrader5()
    setup_account()
    APP_ENV = config.get("APP_ENV") or "default"
    app = create_app(APP_ENV)
    app.run(host="0.0.0.0", port=app.config.get("PORT"))