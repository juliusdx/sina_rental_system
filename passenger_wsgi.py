import sys
import os
import traceback

# cPanel/Passenger looks for 'application' object
try:
    from app import create_app
    application = create_app()
except Exception as e:
    # CRASH LOGGING
    # If the app fails to start, write the error to a file we can read via FTP/File Manager
    with open('passenger_crash.log', 'w') as f:
        f.write(traceback.format_exc())
    
    # Still raise it so Passenger knows it failed, but now we have a log
    raise e

if __name__ == '__main__':
    application.run()
