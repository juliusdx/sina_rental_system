import threading
import time
import requests
import sys
from app import create_app

def run_server():
    app = create_app()
    # Disable reloader to prevent creating a child process in this script context
    try:
        app.run(port=5000, use_reloader=False)
    except Exception as e:
        print(f"Server crash: {e}")

def check_connection():
    print("Attempting to connect to http://127.0.0.1:5000/ ...")
    retries = 5
    for i in range(retries):
        try:
            response = requests.get('http://127.0.0.1:5000/dashboard')
            # 302 is expected because of login_required -> redirect to /login
            # 200 is expected if we land on login page (via follow redirects? no requests doesn't follow by default)
            print(f"Response Code: {response.status_code}")
            print("SUCCESS: Server is up and reachable.")
            return
        except requests.exceptions.ConnectionError:
            print(f"Retry {i+1}: Connection Refused...")
            time.sleep(2)
        except Exception as e:
            print(f"Error: {e}")
            return
    print("FAILURE: Could not connect after retries.")
    sys.exit(1)

if __name__ == "__main__":
    # Start server in separate thread
    print("Starting server thread...")
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    
    # Give it a moment to bind
    time.sleep(3)
    
    check_connection()
    print("Exiting check script.")
    sys.exit(0)
