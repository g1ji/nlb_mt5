import MetaTrader5 as mt5
from flask import Blueprint, request, jsonify, g
from threading import Lock
import datetime

account_routes_bp = Blueprint("account_routes", __name__)
from mt5 import (
    mt5_login_account,
    get_account_by_token,
    place_mt5_order,
    get_mt5_positions,
    get_subscribed_symbols,
    get_mt5_symbol_info,
    get_mt5_account_info,
    close_positions_by_ticket_id,
)


# Create a global lock
global_lock = Lock()


@account_routes_bp.before_request
def before_request():
    # Record the time when the request starts waiting
    g.wait_start_time = datetime.datetime.now()
    global_lock.acquire()
    # Record the time when the request starts processing
    g.process_start_time = datetime.datetime.now()


@account_routes_bp.after_request
def after_request(response):
    # Calculate the wait time
    wait_time = (g.process_start_time - g.wait_start_time).total_seconds()
    # Add the wait time to the response JSON
    response_json = response.get_json()
    response_json["wait_time"] = wait_time
    response.set_data(jsonify(response_json).get_data())

    # Release the lock
    global_lock.release()
    return response


@account_routes_bp.route("")
@account_routes_bp.route("/")
def index():
    return jsonify({"success": "API running"}), 200


@account_routes_bp.route("/login_account", methods=["POST"])
def login_account():
    data = request.get_json()
    api_id = data.get("api_id")
    account_id = data.get("account_id")
    account_id = int(account_id)
    password = data.get("password")
    broker_name = data.get("broker_name")

    if not api_id or not account_id or not password or not broker_name:
        return (
            jsonify(
                {
                    "error": "Missing required fields: api_id, account_id, password OR broker_name"
                }
            ),
            200,
        )
    response = mt5_login_account(api_id, account_id, password, broker_name)
    return jsonify(response), 200


@account_routes_bp.route("/get_account", methods=["GET"])
def get_account():
    # data = request.get_json()
    # token = data.get("token")
    token = request.headers.get("Authorization")

    if not token:
        return (
            jsonify({"error": "Invalid token: need to re-login"}),
            400,
        )

    response = get_account_by_token(token)
    return jsonify(response), 200


@account_routes_bp.route("/get_account_info", methods=["GET"])
def get_account_info():
    token = request.headers.get("Authorization")

    if not token:
        return (
            jsonify({"error": "Missing required fields: token"}),
            400,
        )
    toke_info = get_account_by_token(token)
    if not toke_info:
        return (
            jsonify({"error": "Invalid token: need to re-login"}),
            400,
        )
    api_id = toke_info.get("api_id")
    account_id = toke_info.get("account_id")
    password = toke_info.get("password")
    broker_name = toke_info.get("broker_name")
    if not mt5.login(login=account_id, password=password, server=broker_name):
        error_code, error_message = mt5.last_error()
        return {
            "success": False,
            "message": f"Login failed, error code = {error_code}, message = {error_message}",
        }
    response = get_mt5_account_info()
    return jsonify(response), 200


@account_routes_bp.route("/place_order", methods=["POST"])
def place_order():
    token = request.headers.get("Authorization")

    if not token:
        return (
            jsonify({"error": "Missing required fields: token"}),
            400,
        )
    toke_info = get_account_by_token(token)
    if not toke_info:
        return (
            jsonify({"error": "Invalid token: need to re-login"}),
            400,
        )
    api_id = toke_info.get("api_id")
    account_id = toke_info.get("account_id")
    password = toke_info.get("password")
    broker_name = toke_info.get("broker_name")

    data = request.get_json()
    action = data.get("action", None)
    magic = data.get("magic", None)
    order = data.get("order", None)
    symbol = data.get("symbol", None)
    volume = data.get("volume", None)
    price = data.get("price", None)
    stoplimit = data.get("stoplimit", None)
    sl = data.get("sl", None)
    tp = data.get("tp", None)
    deviation = data.get("deviation", None)
    order_type = data.get("order_type", None)
    type_filling = data.get("type_filling", None)
    type_time = data.get("type_time", None)
    expiration = data.get("expiration", None)
    comment = data.get("comment", f"api_id = {api_id} BY Nextlevelbot")
    position = data.get("position", None)
    position_by = data.get("position_by", None)

    if action is not None:
        action = getattr(mt5, action)

    if order_type is not None:
        order_type = getattr(mt5, order_type)

    if type_filling is not None:
        type_filling = getattr(mt5, type_filling)

    if type_time is not None:
        type_time = getattr(mt5, type_time)

    if not mt5.login(login=account_id, password=password, server=broker_name):
        error_code, error_message = mt5.last_error()
        return {
            "success": False,
            "message": f"Login failed, error code = {error_code}, message = {error_message}",
        }
    response = place_mt5_order(
        action,
        magic,
        order,
        symbol,
        volume,
        price,
        stoplimit,
        sl,
        tp,
        deviation,
        order_type,
        type_filling,
        type_time,
        expiration,
        comment,
        position,
        position_by,
    )
    return jsonify(response), 200


@account_routes_bp.route("/get_positions", methods=["GET"])
def get_positions():
    # Get the token from the request headers
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Missing required fields: token"}), 400

    # Retrieve account information using the token
    token_info = get_account_by_token(token)
    if not token_info:
        return jsonify({"error": "Invalid token: need to re-login"}), 400

    # Extract account details
    api_id = token_info.get("api_id")
    account_id = token_info.get("account_id")
    password = token_info.get("password")
    broker_name = token_info.get("broker_name")

    # Login to MetaTrader 5 using the provided credentials
    if not mt5.login(login=account_id, password=password, server=broker_name):
        error_code, error_message = mt5.last_error()
        return {
            "success": False,
            "message": f"Login failed, error code = {error_code}, message = {error_message}",
        }

    # Get query parameters for type and symbol
    order_type = request.args.get("type")
    symbol = request.args.get("symbol")

    # Fetch positions based on type and symbol
    positions = get_mt5_positions(symbol=symbol, order_type=order_type)

    # Return the positions as a JSON response
    return jsonify(positions), 200


@account_routes_bp.route("/get_subscribed_symbols", methods=["GET"])
def get_subscribed_symbols_route():
    # Get the token from the request headers
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Missing required fields: token"}), 400

    # Retrieve account information using the token
    token_info = get_account_by_token(token)
    if not token_info:
        return jsonify({"error": "Invalid token: need to re-login"}), 400

    # Extract account details
    api_id = token_info.get("api_id")
    account_id = token_info.get("account_id")
    password = token_info.get("password")
    broker_name = token_info.get("broker_name")

    # Login to MetaTrader 5 using the provided credentials
    if not mt5.login(login=account_id, password=password, server=broker_name):
        error_code, error_message = mt5.last_error()
        return {
            "success": False,
            "message": f"Login failed, error code = {error_code}, message = {error_message}",
        }

    # Get the subscribed symbols
    symbols_response = get_subscribed_symbols()

    return jsonify(symbols_response), 200


@account_routes_bp.route("/get_symbol_info", methods=["GET"])
def get_symbol_info():
    # Get the token from the request headers
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Missing required fields: token"}), 400

    # Retrieve account information using the token
    token_info = get_account_by_token(token)
    if not token_info:
        return jsonify({"error": "Invalid token: need to re-login"}), 400

    # Extract account details
    api_id = token_info.get("api_id")
    account_id = token_info.get("account_id")
    password = token_info.get("password")
    broker_name = token_info.get("broker_name")

    # Login to MetaTrader 5 using the provided credentials
    if not mt5.login(login=account_id, password=password, server=broker_name):
        error_code, error_message = mt5.last_error()
        return {
            "success": False,
            "message": f"Login failed, error code = {error_code}, message = {error_message}",
        }

    # Get query parameters for type and symbol
    symbol = request.args.get("symbol")

    # Fetch positions based on type and symbol
    positions = get_mt5_symbol_info(symbol=symbol)

    # Return the positions as a JSON response
    return jsonify(positions), 200


@account_routes_bp.route("/close_positions", methods=["POST"])
def close_positions():
    # Get the token from the request headers
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Missing required fields: token"}), 400

    # Retrieve account information using the token
    token_info = get_account_by_token(token)
    if not token_info:
        return jsonify({"error": "Invalid token: need to re-login"}), 400

    # Extract account details
    api_id = token_info.get("api_id")
    account_id = token_info.get("account_id")
    password = token_info.get("password")
    broker_name = token_info.get("broker_name")

    # Login to MetaTrader 5 using the provided credentials
    if not mt5.login(login=account_id, password=password, server=broker_name):
        error_code, error_message = mt5.last_error()
        return {
            "success": False,
            "message": f"Login failed, error code = {error_code}, message = {error_message}",
        }

    data = request.json
    ticket_id = data.get("ticket_id")
    ticket_id = int(ticket_id)
    volume = data.get("volume", None)
    deviation = data.get("deviation", 20)
    comment = data.get("comment", f"api_id = {api_id} BY Nextlevelbot")

    success = close_positions_by_ticket_id(
        ticket_id, volume=volume, deviation=deviation, comment=comment
    )

    return jsonify({"success": success})
