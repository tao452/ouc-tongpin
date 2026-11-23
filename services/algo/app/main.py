from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.body_limit import BodyLimitMiddleware
from app.routers.moderation import router
from app.routers.scoring import router as scoring_router

app = FastAPI(title="OUC同频内容安全服务", version="0.1.0")
app.add_middleware(BodyLimitMiddleware)
app.include_router(router)
app.include_router(scoring_router)


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, exc: RequestValidationError):
    # Pydantic's default response echoes submitted values, which can contain PII.
    status = 400 if request.url.path == "/score" else 422
    return JSONResponse(status_code=status, content={"detail": "Invalid request"})


@app.get("/health")
def health():
    return {"status": "ok"}
