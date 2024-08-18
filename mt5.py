import os
import shutil
import time
import signal
import psutil
import uuid
import subprocess
import MetaTrader5 as mt5
from pymongo import MongoClient


base_path = os.getcwd()

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")
db = client["mt5_database"]
accounts_collection = db["accounts"]
account_id = int(time.time())

print("=======", account_id)


def copy_contents_if_not_exists(source_dir, destination_dir):
    # Check if the source directory exists
    if not os.path.exists(source_dir):
        print(f"Source directory {source_dir} does not exist.")
        return

    # Check if the destination directory exists
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)
        print(f"Created destination directory {destination_dir}")
    else:
        return

    # List all files and subdirectories in the source directory
    for item in os.listdir(source_dir):
        source_item = os.path.join(source_dir, item)
        destination_item = os.path.join(destination_dir, item)

        # Check if the item already exists in the destination
        if not os.path.exists(destination_item):
            if os.path.isdir(source_item):
                shutil.copytree(source_item, destination_item)
                # print(f"Copied directory {source_item} to {destination_item}")
            else:
                shutil.copy2(source_item, destination_item)
                # print(f"Copied file {source_item} to {destination_item}")
        else:
            print(f"{destination_item} already exists. Skipping.")


def terminate_all_metatrader5():
    for proc in psutil.process_iter(["pid", "name", "exe"]):
        try:
            if proc.info["name"] == "terminal64.exe":
                os.kill(proc.info["pid"], signal.SIGTERM)
                print(f"MetaTrader 5 process {proc.info['pid']} terminated")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass


def shutdown_metatrader5_by_id(account_id):
    account_path = os.path.join(base_path, "accounts", str(account_id))
    account_path = os.path.join(account_path, "terminal64.exe")
    if not mt5.shutdown():
        error_code, error_message = mt5.last_error()
        print(
            f"initialize() failed, error code = {error_code}, message = {error_message}"
        )
    # else:
    #     print("MetaTrader 5 has been shut down successfully")

    for proc in psutil.process_iter(["pid", "name", "exe"]):
        try:
            if (
                proc.info["name"] == "terminal64.exe"
                and proc.info["exe"] == account_path
            ):
                os.kill(proc.info["pid"], signal.SIGTERM)
                print(f"MetaTrader 5 process at {account_path} terminated")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass


def remove_account(account_id):
    shutdown_metatrader5_by_id(account_id)
    account_path = os.path.join(base_path, "accounts", str(account_id))
    try:
        shutil.rmtree(account_path)
        print(f"Directory {account_path} and all its contents have been deleted.")
    except Exception as e:
        print(f"Error deleting directory {account_path}: {e}")


def remove_all_account():
    account_path = os.path.join(base_path, "accounts")
    try:
        shutil.rmtree(account_path)
        print(f"Directory {account_path} and all its contents have been deleted.")
    except Exception as e:
        print(f"Error deleting directory {account_path}: {e}")


def re_setup_account(account_id):
    remove_account(account_id)
    setup_account(account_id)


def setup_account():
    remove_account(account_id)
    account_path = os.path.join(base_path, "accounts", str(account_id))
    meta_trader = os.path.join(base_path, "meta-trader")
    copy_contents_if_not_exists(meta_trader, account_path)
    account_path = os.path.join(account_path, "terminal64.exe")
    subprocess.Popen([account_path, "/portable"])
    time.sleep(2)
    if not mt5.initialize(path=account_path, portable=True):
        error_code, error_message = mt5.last_error()
        print(
            f"initialize() failed, error code = {error_code}, message = {error_message}"
        )
        mt5.shutdown()
        quit()


def mt5_login_account(api_id, account_id, password, broker_name):
    # Initialize MetaTrader 5
    if not mt5.initialize():
        error_code, error_message = mt5.last_error()
        return {
            "success": False,
            "message": f"initialize() failed, error code = {error_code}, message = {error_message}",
        }

    login_result = mt5.login(login=account_id, password=password, server=broker_name)

    if login_result:
        random_unique_id = str(uuid.uuid4())

        # Insert or replace the record
        accounts_collection.update_one(
            {"id": api_id},
            {
                "$set": {
                    "token": random_unique_id,
                    "account_id": account_id,
                    "password": password,
                    "broker_name": broker_name,
                }
            },
            upsert=True,
        )

        return {
            "success": True,
            "message": "Connected to the account successfully",
            "data": {"token": random_unique_id},
        }
    else:
        error_code, error_message = mt5.last_error()
        return {
            "success": False,
            "message": f"Failed to connect to the account. Error code:  {error_code}, message = {error_message}",
        }


def get_account_by_token(token):
    try:
        account = accounts_collection.find_one({"token": token})

        if account:
            return {
                "api_id": account["id"],
                "account_id": account["account_id"],
                "password": account["password"],
                "broker_name": account["broker_name"],
            }
        else:
            return None

    except Exception as e:
        return {"success": False, "message": f"Database error: {e}"}


def get_mt5_positions(symbol=None, order_type=None):
    # Initialize MetaTrader 5
    if not mt5.initialize():
        error_code, error_message = mt5.last_error()
        return {
            "success": False,
            "message": f"initialize() failed, error code = {error_code}, message = {error_message}",
        }

    # Fetch positions
    if symbol:
        positions = mt5.positions_get(symbol=symbol)
    else:
        positions = mt5.positions_get()

    # Handle the case where no positions are found
    if positions is None or len(positions) == 0:
        return {"success": False, "message": "No positions found."}

    # Filter positions by order type if provided
    if order_type:
        order_type = order_type.capitalize()
        if order_type not in ["Buy", "Sell"]:
            return {
                "success": False,
                "message": "Invalid order type. Must be 'Buy' or 'Sell'.",
            }

        mt5_order_type = (
            mt5.ORDER_TYPE_BUY if order_type == "Buy" else mt5.ORDER_TYPE_SELL
        )
        positions = [pos for pos in positions if pos.type == mt5_order_type]

    # Display each position's details
    positions_list = []
    for position in positions:
        pos_dict = {
            "ticket": position.ticket,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": "Buy" if position.type == mt5.ORDER_TYPE_BUY else "Sell",
            "price_open": position.price_open,
            "price_current": position.price_current,
            "profit": position.profit,
            "sl": position.sl,
            "tp": position.tp,
            "comment": position.comment,
        }
        positions_list.append(pos_dict)

    return {
        "success": True,
        "message": "Positions retrieved successfully.",
        "data": {
            "positions": positions_list,
        },
    }


def place_mt5_order(
    action,
    magic,
    order=None,
    symbol=None,
    volume=None,
    price=None,
    stoplimit=None,
    sl=None,
    tp=None,
    deviation=20,
    order_type=None,
    type_filling=None,
    type_time=None,
    expiration=None,
    comment="",
    position=None,
    position_by=None,
):
    # Required fields check
    if action is None:
        return {"success": False, "message": "Error: 'action' is a required field."}
    if magic is None:
        return {"success": False, "message": "Error: 'magic' is a required field."}
    if (
        symbol is None
        and action != mt5.TRADE_ACTION_MODIFY
        and action != mt5.TRADE_ACTION_REMOVE
    ):
        return {
            "success": False,
            "message": "Error: 'symbol' is a required field when placing or closing orders.",
        }
    if volume is None and action == mt5.TRADE_ACTION_DEAL:
        return {
            "success": False,
            "message": "Error: 'volume' is a required field when placing a deal.",
        }
    if price is None and action == mt5.TRADE_ACTION_PENDING:
        return {
            "success": False,
            "message": "Error: 'price' is a required field when placing a pending order.",
        }
    if order_type is None:
        return {
            "success": False,
            "message": "Error: 'order_type' is a required field.",
        }
    if type_filling is None:
        return {
            "success": False,
            "message": "Error: 'type_filling' is a required field.",
        }
    if type_time is None:
        return {"success": False, "message": "Error: 'type_time' is a required field."}

    # Initialize MetaTrader 5
    if not mt5.initialize():
        error_code, error_message = mt5.last_error()
        return {
            "success": False,
            "message": f"initialize() failed, error code = {error_code}, message = {error_message}",
        }

    # If a symbol is provided, ensure it is available in MarketWatch
    if symbol and not mt5.symbol_select(symbol, True):
        error_code, error_message = mt5.last_error()
        return {
            "success": False,
            "message": f"Failed to select {symbol}, error code = {error_code}, message = {error_message}",
        }

    # Create the order request dictionary
    request = {
        "action": action,
        "magic": magic,
        "order": order,
        "symbol": symbol,
        "volume": volume,
        "price": price,
        "stoplimit": stoplimit,
        "sl": sl,
        "tp": tp,
        "deviation": deviation,
        "type": order_type,
        "type_filling": type_filling,
        "type_time": type_time,
        "expiration": expiration,
        "comment": comment,
        "position": position,
        "position_by": position_by,
    }

    # Filter out None values (these are optional parameters)
    request = {k: v for k, v in request.items() if v is not None}

    # Send the order
    result = mt5.order_send(request)

    if result is None:
        error_code, error_message = mt5.last_error()
        return {
            "success": False,
            "message": "Order send failed: error code = {error_code}, message = {error_message}",
        }

    # Check result
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return {
            "success": False,
            "message": f"Order failed, retcode={result.retcode}, message={result.comment}",
        }

    return {
        "success": True,
        "message": f"Order placed successfully! Return code: {result.retcode}",
    }


def close_positions_by_ticket_id(
    position_ticket, volume=None, deviation=20, comment="Python close position"
):
    # Initialize MetaTrader 5
    if not mt5.initialize():
        error_code, error_message = mt5.last_error()
        return {
            "success": False,
            "message": f"initialize() failed, error code = {error_code}, message = {error_message}",
        }

    # Get the position details
    position = mt5.positions_get(ticket=position_ticket)

    if position is None or len(position) == 0:
        return {
            "success": False,
            "message": f"Position with ticket {position_ticket} not found.",
        }

    position = position[
        0
    ]  # Get the first position (should be the only one with the ticket)

    # Determine the action (buy or sell) to close the position
    action = mt5.TRADE_ACTION_DEAL
    if position.type == mt5.ORDER_TYPE_BUY:
        order_type = mt5.ORDER_TYPE_SELL
    elif position.type == mt5.ORDER_TYPE_SELL:
        order_type = mt5.ORDER_TYPE_BUY
    else:
        return {
            "success": False,
            "message": f"Unsupported position type: {position.type}",
        }

    # Use the full volume if not specified
    if volume is None:
        volume = position.volume

    # Create the close order request
    request = {
        "action": action,
        "symbol": position.symbol,
        "volume": volume,
        "type": order_type,
        "position": position_ticket,  # Specify the position to close
        "deviation": deviation,
        "comment": comment,
        "type_filling": mt5.ORDER_FILLING_FOK,  # Fill or Kill
        "type_time": mt5.ORDER_TIME_GTC,  # Good Till Cancelled
    }

    # Send the order to close the position
    result = mt5.order_send(request)

    # Check the result
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return {
            "success": False,
            "message": f"Failed to close position, retcode={result.retcode}, message={result.comment}",
        }

    return {
        "success": True,
        "message": f"Position closed successfully! Return code: {result.retcode}",
    }


def get_subscribed_symbols():
    # Initialize MetaTrader 5
    if not mt5.initialize():
        error_code, error_message = mt5.last_error()
        return {
            "success": False,
            "message": f"initialize() failed, error code = {error_code}, message = {error_message}",
        }

    # Fetch subscribed symbols
    symbols = mt5.symbols_get()

    # Handle the case where no symbols are found
    if symbols is None or len(symbols) == 0:
        return {"success": False, "message": "No subscribed symbols found."}

    # Create a list of symbol names
    subscribed_symbols = [symbol.name for symbol in symbols]

    return {
        "success": True,
        "message": "Subscribed symbols retrieved successfully.",
        "data": {
            "symbols": subscribed_symbols,
        },
    }


def get_mt5_symbol_info(symbol=None):
    # Initialize MetaTrader 5
    if not mt5.initialize():
        error_code, error_message = mt5.last_error()
        return {
            "success": False,
            "message": f"initialize() failed, error code = {error_code}, message = {error_message}",
        }

    if not mt5.symbol_select(symbol, True):
        error_code, error_message = mt5.last_error()
        return {
            "success": False,
            "message": f"Failed to select {symbol}, error code = {error_code}, message = {error_message}",
        }
    time.sleep(0.2)
    # Fetch subscribed symbols
    symbol_info = mt5.symbol_info(symbol)

    if symbol_info is None:
        return {
            "success": False,
            "message": f"Symbol '{symbol}' not found or not subscribed.",
        }

    # symbol_info_dict = {}
    # for attr in dir(symbol_info):
    #     if not attr.startswith('__') and not callable(getattr(symbol_info, attr)):
    #         symbol_info_dict[attr] = getattr(symbol_info, attr)
    # print(symbol_info_dict)

    if symbol_info.bid and symbol_info.last:
        daily_change = (symbol_info.last - symbol_info.bid) / symbol_info.bid * 100
    else:
        daily_change = None

    return {
        "success": True,
        "message": "Subscribed symbols retrieved successfully.",
        "data": {
            "symbols": {
                "symbol": symbol_info.name,
                "bid": symbol_info.bid,
                "ask": symbol_info.ask,
                "daily_change": daily_change,
            }
        },
    }


def get_mt5_account_info():
    # Initialize MetaTrader 5
    if not mt5.initialize():
        error_code, error_message = mt5.last_error()
        return {
            "success": False,
            "message": f"initialize() failed, error code = {error_code}, message = {error_message}",
        }

    # Fetch subscribed symbols
    account_info = mt5.account_info()

    info = {}
    for attr in dir(account_info):
        if not attr.startswith("__") and not callable(getattr(account_info, attr)):
            info[attr] = getattr(account_info, attr)

    return {
        "success": True,
        "message": "Account info",
        "data": {"symbols": info},
    }
