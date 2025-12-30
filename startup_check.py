import sys
import os
import traceback

# Set log file
log_file = os.path.join(os.path.dirname(__file__), 'startup_debug.log')

def log(msg):
    with open(log_file, 'a') as f:
        f.write(msg + '\n')
    print(msg)

try:
    log("--- Starting Check ---")
    log(f"Python: {sys.version}")
    log(f"CWD: {os.getcwd()}")
    
    # 1. Check Imports
    log("Attempting imports...")
    try:
        import flask
        log("Flask imported successfully.")
    except ImportError as e:
        log(f"FAIL: Flask missing. {e}")

    try:
        from routes import properties
        log("routes.properties imported.")
    except Exception as e:
        log(f"FAIL: routes.properties error. {traceback.format_exc()}")

    try:
        from routes import tenants
        log("routes.tenants imported.")
    except Exception as e:
        log(f"FAIL: routes.tenants error. {traceback.format_exc()}")
        
    try:
        from routes import billing
        log("routes.billing imported.")
    except Exception as e:
        log(f"FAIL: routes.billing error. {traceback.format_exc()}")
        
    # 2. Check Database
    log("Checking DB file...")
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'rental.db')
    if os.path.exists(db_path):
        log(f"DB exists at {db_path}")
        # Check permissions
        is_writable = os.access(db_path, os.W_OK)
        log(f"DB Writable: {is_writable}")
    else:
        # Check old path
        db_path_old = 'rental.db'
        if os.path.exists(db_path_old):
             log(f"DB exists at root {db_path_old}")
        else:
             log("FAIL: rental.db NOT FOUND in expected locations.")

    # 3. Check App Creation
    log("Attempting create_app()...")
    try:
        from app import create_app
        app = create_app()
        log("create_app() successful.")
    except Exception as e:
        log(f"FAIL: create_app() crashed. {traceback.format_exc()}")

    log("--- Check Complete ---")

except Exception as e:
    log(f"CRITICAL SCRIPT ERROR: {traceback.format_exc()}")
