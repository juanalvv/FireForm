from fastapi import FastAPI
from api.routes import templates, forms
from src.config import validate_config

validate_config()

app = FastAPI()

app.include_router(templates.router)
app.include_router(forms.router)