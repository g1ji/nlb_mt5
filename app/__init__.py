from flask import Flask
from config import config
from .api import register_apis_routes


def create_app(app_env="default"):
    app = Flask(__name__)
    app.config.from_object(config[app_env])
    register_apis_routes(app)
    return app
