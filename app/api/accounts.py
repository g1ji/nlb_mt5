
from flask import Blueprint, request, jsonify
account_routes_bp = Blueprint("account_routes", __name__)
from mt5 import mt5_login_account


@account_routes_bp.route("")
@account_routes_bp.route("/")
def index():
    return "<h1> Account Routs</h1>"


@account_routes_bp.route('/login_account', methods=['POST'])
def login_account():
    data = request.get_json()
    # api_id = data.get('api_id')
    account_id = data.get('account_id')
    account_id = int(account_id)
    password = data.get('password')
    broker_name = data.get('broker_name')

    if not account_id or not password or not broker_name:
        return jsonify({'error': 'Missing required fields: account_id, password OR broker_name'}), 400

    response = mt5_login_account(account_id, password, broker_name)
    return jsonify(response), 200