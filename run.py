"""
Start of the Application
"""


import uvicorn
from dotenv import load_dotenv
from app.config import config

load_dotenv()

if __name__ == "__main__":
    uvicorn.run("app.main:app", port=config.PORT, reload=True)
