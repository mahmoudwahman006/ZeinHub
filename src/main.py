from fastapi import FastAPI
from routes import base, files
from dotenv import load_dotenv

load_dotenv(".env")
app = FastAPI()

app.include_router(base.base_router)
app.include_router(files.files_router) 