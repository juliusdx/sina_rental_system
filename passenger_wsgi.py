import sys
import os

# cPanel/Passenger looks for 'application' object
from app import create_app

# Create the application instance
application = create_app()

# If running directly (useful for testing this file locally)
if __name__ == '__main__':
    application.run()
