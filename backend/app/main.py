from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.businesses import router as businesses_router
from app.api.dashboard import router as dashboard_router
from app.api.ingestion import router as ingestion_router
from app.config import settings

app = FastAPI(title="PlutusAI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(businesses_router)
app.include_router(ingestion_router)
app.include_router(dashboard_router)


@app.get("/health")
def health():
    return {"status": "ok"}
