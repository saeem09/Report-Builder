from fastapi import FastAPI

app = FastAPI(title="Progress Report API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
