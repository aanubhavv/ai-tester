from fastapi import FastAPI

app = FastAPI(
    title="QAForge API",
    version="1.0.0"
)

@app.get("/")
def root():
    return {
        "message": "Welcome to QAForge API"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }