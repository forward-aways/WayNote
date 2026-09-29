from fastapi import FastAPI
from sqlalchemy import text


from app.core.config import settings
from app.db.session import engine
from app.api.v1 import auth, trips, trip_days, places



app = FastAPI(title=settings.app_name)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(trips.router, prefix="/api/v1")
app.include_router(trip_days.router, prefix="/api/v1")
app.include_router(places.router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "Waynote API is running"}

@app.get("/api/v1/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}

