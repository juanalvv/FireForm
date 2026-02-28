from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from api.routes import templates, forms

app = FastAPI(
    title="FireForm API",
    description="API for the FireForm project.",
    version="1.0"
)

app.include_router(templates.router)
app.include_router(forms.router)

@app.get("/", include_in_schema=False)
def read_root():
    """Redirect to the swagger interface."""
    return RedirectResponse(url="/docs")

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return {}