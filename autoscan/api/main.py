from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import existing routers
from autoscan.api.routes.dashboard import router as dashboard_router
from autoscan.api.routes.companies import router as companies_router
from autoscan.api.routes.system import router as system_router

# Import orchestration routers
from autoscan.orchestration.health import router as health_router

app = FastAPI(
    title="AutoScan Revenue Engine API",
    description="Internal management API for the AutoScan B2B CRM and pipeline",
    version="1.0.0"
)

# CORS configuration for the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to actual frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(dashboard_router)
app.include_router(companies_router)
app.include_router(system_router)
app.include_router(health_router)

@app.get("/")
def read_root():
    return {"message": "AutoScan API is running. Check /health for status."}
