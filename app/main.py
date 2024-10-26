"""
Starting point of the app
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from configs import config, ORIGINS, DESCRIPTION
from controllers import emailRouter


app = FastAPI(
    title="EmailService",
    debug=1 if config.ENV == "development" else 0,
    version="0.0.1",
    description=DESCRIPTION,
    license_info={
        "name": "MIT License",
        "url": "https://github.com/TeamShiksha/email-service/blob/main/LICENSE",
    },
    openapi_url="/openapi.json" if config.ENV == "development" else None,
    docs_url="/docs" if config.ENV == "development" else None,
    redoc_url="/redoc" if config.ENV == "development" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)

app.include_router(emailRouter)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT, reload=True)
