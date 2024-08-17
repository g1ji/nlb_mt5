import os
import shutil
import time
import signal
import psutil
import uuid
import subprocess
import MetaTrader5 as mt5
from pymongo import MongoClient


# import MetaTrader5 as mt5

# Set the path to the MetaTrader 5 terminal executable
# mt5_path = r"C:\Path\To\MetaTrader 5\terminal64.exe"  # Update this path

# Initialize MetaTrader 5 with the specific terminal location
# if not mt5.initialize(mt5_path):
#     print("initialize() failed, error code =", mt5.last_error())
#     quit()
base_path = os.getcwd()

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")
db = client["mt5_database"]
accounts_collection = db["accounts"]


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
        print("shutdown() failed, error code =", mt5.last_error())
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


def setup_account(account_id):
    remove_account(account_id)
    account_path = os.path.join(base_path, "accounts", str(account_id))
    meta_trader = os.path.join(base_path, "meta-trader")
    copy_contents_if_not_exists(meta_trader, account_path)
    account_path = os.path.join(account_path, "terminal64.exe")
    subprocess.Popen([account_path, '/portable'])
    time.sleep(2)
    if not mt5.initialize(path=account_path, portable=True):
        print("initialize() failed, error code =", mt5.last_error())
        mt5.shutdown()
        quit()


def mt5_login_account(api_id, account_id, password, broker_name):
    # Initialize MetaTrader 5
    if not mt5.initialize():
        return {
            "success": False,
            "message": "initialize() failed, error code =" + mt5.last_error(),
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
        return {
            "success": False,
            "message": f"Failed to connect to the account. Error code: {mt5.last_error()}",
        }


def get_account_by_token(token):
    try:
        account = accounts_collection.find_one({"token": token})

        if account:
            return {
                "success": True,
                "api_id": account["id"],
                "account_id": account["account_id"],
                "password": account["password"],
                "broker_name": account["broker_name"],
            }
        else:
            return None

    except Exception as e:
        return {"success": False, "message": f"Database error: {e}"}


def get_mt5_positions(symbol=None):
    # Initialize MetaTrader 5
    if not mt5.initialize():
        return {
            "success": False,
            "message": "initialize() failed, error code =" + mt5.last_error(),
        }

    # Fetch positions
    if symbol:
        positions = mt5.positions_get(symbol=symbol)
    else:
        positions = mt5.positions_get()

    if positions is None or len(positions) == 0:
        print("No positions found.")
        return None

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
        print(
            f"Ticket: {position.ticket}, Symbol: {position.symbol}, "
            f"Volume: {position.volume}, Type: {pos_dict['type']}, "
            f"Open Price: {position.price_open}, Current Price: {position.price_current}, "
            f"Profit: {position.profit}, SL: {position.sl}, TP: {position.tp}, "
            f"Comment: {position.comment}"
        )
    return positions_list


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
        return {
            "success": False,
            "message": "initialize() failed, error code =" + mt5.last_error(),
        }

    # If a symbol is provided, ensure it is available in MarketWatch
    if symbol and not mt5.symbol_select(symbol, True):
        return {
            "success": False,
            "message": f"Failed to select {symbol}, error code =" + mt5.last_error(),
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

    print(request)
    # Send the order
    result = mt5.order_send(request)

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


def close_position(
    position_ticket, symbol, volume=None, deviation=20, comment="Python close position"
):
    # Initialize MetaTrader 5
    if not mt5.initialize():
        return {
            "success": False,
            "message": "initialize() failed, error code =" + mt5.last_error(),
        }

    # Get the position details
    position = mt5.positions_get(ticket=position_ticket)
    if position is None or len(position) == 0:
        print(f"Position with ticket {position_ticket} not found.")
        return False

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
        print(f"Unsupported position type: {position.type}")
        return False

    # Use the full volume if not specified
    if volume is None:
        volume = position.volume

    # Create the close order request
    request = {
        "action": action,
        "symbol": symbol,
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
        print(
            f"Failed to close position, retcode={result.retcode}, message={result.comment}"
        )
        return False

    print(f"Position closed successfully! Return code: {result.retcode}")
    return True


print(mt5.TRADE_ACTION_DEAL)
