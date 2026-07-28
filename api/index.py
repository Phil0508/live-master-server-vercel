import os
import sys

# Add root directory to python path for importing server
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import app

# Export Flask app as Vercel WSGI handler
app = app
