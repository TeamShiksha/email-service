"""
Start of the Application
"""


import uvicorn
from dotenv import load_dotenv

load_dotenv()

from app.config import config
from app.main import app

if __name__ == "__main__":
    # uvicorn.run("app.main:app", port=config.PORT, reload=True)
    # --> run locally with auto reload on change
    uvicorn.run(app, port=config.PORT) # to run on vercel
