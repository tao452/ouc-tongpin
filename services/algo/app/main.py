from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.routers.moderation import router

app = FastAPI(title="OUC同频内容安全服务", version="0.1.0")
app.include_router(router)


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, exc: RequestValidationError):
    # Pydantic's default response echoes submitted values, which can contain PII.
    return JSONResponse(status_code=422, content={"detail": "Invalid request"})


@app.get("/health")
def health():
    return {"status": "ok"}
