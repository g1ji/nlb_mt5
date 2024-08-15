
from flask import Blueprint, request, jsonify
account_routes_bp = Blueprint("account_routes", __name__)



@account_routes_bp.route("")
@account_routes_bp.route("/")
def index():
    return "<h1> Account Routs</h1>"


