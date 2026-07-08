from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fpl_gaffer.settings import settings
from contextlib import asynccontextmanager
from fpl_gaffer.integrations.api.app.routes.user import router as user_router
from fpl_gaffer.integrations.api.app.routes.chat import router as chat_router
from fpl_gaffer.integrations.api.app.routes.metrics import router as metrics_router
from fpl_gaffer.integrations.api.app.routes.whatsapp import router as whatsapp_router
from fpl_gaffer.integrations.api.app.routes.onboarding import router as onboarding_router

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     from fpl_gaffer.integrations.api.app.db import engine, Base
#
#     # Ensure all tables exist at startup
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)
#
#     yield

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    # lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handler for HTTP exceptions
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code
        },
    )

@app.get("/")
def home():
    return {
        "response": "App is running!"
    }

# Routers
app.include_router(user_router)
app.include_router(chat_router)
app.include_router(metrics_router)
app.include_router(whatsapp_router)
app.include_router(onboarding_router)
