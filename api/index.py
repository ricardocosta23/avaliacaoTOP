
import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import app

# Vercel expects the app to be exported directly
handler = app

if __name__ == "__main__":
    app.run()
