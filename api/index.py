
import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import app

# This is required for Vercel - the app itself is the handler
def handler(environ, start_response):
    return app(environ, start_response)

# For backwards compatibility
application = app

if __name__ == "__main__":
    app.run()
