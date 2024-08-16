import os
import shutil
import time
import signal
import psutil
import sqlite3
import uuid
import MetaTrader5 as mt5

# import MetaTrader5 as mt5

# Set the path to the MetaTrader 5 terminal executable
# mt5_path = r"C:\Path\To\MetaTrader 5\terminal64.exe"  # Update this path

# Initialize MetaTrader 5 with the specific terminal location
# if not mt5.initialize(mt5_path):
#     print("initialize() failed, error code =", mt5.last_error())
#     quit()
db_path = "login_data.db"
base_path = os.getcwd()
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS accounts (
        id TEXT PRIMARY KEY,
        token TEXT NOT NULL,
        account_id INTEGER NOT NULL,
        password TEXT NOT NULL,
        broker_name TEXT NOT NULL
    )
"""
)


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
    # subprocess.Popen([account_path, '/portable'])
    # time.sleep(5)
    if not mt5.initialize(path=account_path, portable=True):
        print("initialize() failed, error code =", mt5.last_error())
        quit()


def mt5_login_account(api_id, account_id, password, broker_name):
    login_result = mt5.login(login=account_id, password=password, server=broker_name)
    
    if login_result:
        random_unique_id = str(uuid.uuid4())
        
        # Insert or replace the record
        cursor.execute(
            """
            INSERT OR REPLACE INTO accounts (id, token, account_id, password, broker_name)
            VALUES (?, ?, ?, ?, ?)
            """,
            (api_id, random_unique_id, account_id, password, broker_name),
        )
        conn.commit()
        
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
        cursor.execute(
            """
            SELECT account_id, password, broker_name
            FROM accounts
            WHERE id = ?
        """,
            (token,),
        )

        # Fetch the result
        account = cursor.fetchone()

        if account:
            account_id, password, broker_name = account
            return {
                "account_id": account_id,
                "password": password,
                "broker_name": broker_name,
            }

        else:
            return None

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None


def get_positions(symbol=None):
    # Initialize MetaTrader 5
    if not mt5.initialize():
        print("Failed to initialize MetaTrader 5, error code =", mt5.last_error())
        return None

    # Fetch positions
    if symbol:
        positions = mt5.positions_get(symbol=symbol)
    else:
        positions = mt5.positions_get()

    if positions is None or len(positions) == 0:
        print("No positions found.")
        mt5.shutdown()
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

    mt5.shutdown()
    return positions_list


def place_order(
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
        print("Error: 'action' is a required field.")
        return False
    if magic is None:
        print("Error: 'magic' is a required field.")
        return False
    if (
        symbol is None
        and action != mt5.TRADE_ACTION_MODIFY
        and action != mt5.TRADE_ACTION_REMOVE
    ):
        print("Error: 'symbol' is a required field when placing or closing orders.")
        return False
    if volume is None and action == mt5.TRADE_ACTION_DEAL:
        print("Error: 'volume' is a required field when placing a deal.")
        return False
    if price is None and action == mt5.TRADE_ACTION_PENDING:
        print("Error: 'price' is a required field when placing a pending order.")
        return False
    if order_type is None:
        print("Error: 'order_type' is a required field.")
        return False
    if type_filling is None:
        print("Error: 'type_filling' is a required field.")
        return False
    if type_time is None:
        print("Error: 'type_time' is a required field.")
        return False

    # Initialize MetaTrader 5
    if not mt5.initialize():
        print("initialize() failed, error code =", mt5.last_error())
        return False

    # If a symbol is provided, ensure it is available in MarketWatch
    if symbol and not mt5.symbol_select(symbol, True):
        print(f"Failed to select {symbol}, error code =", mt5.last_error())
        mt5.shutdown()
        return False

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
    mt5.shutdown()

    # Check result
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Order failed, retcode={result.retcode}, message={result.comment}")
        return False

    print(f"Order placed successfully! Return code: {result.retcode}")
    return True


def close_position(
    position_ticket, symbol, volume=None, deviation=20, comment="Python close position"
):
    # Initialize MetaTrader 5
    if not mt5.initialize():
        print("Failed to initialize MetaTrader 5, error code =", mt5.last_error())
        return False

    # Get the position details
    position = mt5.positions_get(ticket=position_ticket)
    if position is None or len(position) == 0:
        print(f"Position with ticket {position_ticket} not found.")
        mt5.shutdown()
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
        mt5.shutdown()
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
    mt5.shutdown()

    # Check the result
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(
            f"Failed to close position, retcode={result.retcode}, message={result.comment}"
        )
        return False

    print(f"Position closed successfully! Return code: {result.retcode}")
    return True
