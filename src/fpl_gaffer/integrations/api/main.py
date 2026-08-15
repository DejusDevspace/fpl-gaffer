from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from fpl_gaffer.graph.graph import close_graph, get_compiled_graph
from fpl_gaffer.integrations.api.app.routes.chat import router as chat_router
from fpl_gaffer.integrations.api.app.routes.metrics import router as metrics_router
from fpl_gaffer.integrations.api.app.routes.onboarding import router as onboarding_router
from fpl_gaffer.integrations.api.app.routes.user import router as user_router
from fpl_gaffer.integrations.api.app.routes.whatsapp import router as whatsapp_router
from fpl_gaffer.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_compiled_graph()  # opens the Postgres checkpoint pool once, at startup
    yield
    await close_graph()


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
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
        content={"error": True, "message": exc.detail, "status_code": exc.status_code},
    )


@app.get("/")
def home():
    return {"response": "App is running!"}


# Routers
app.include_router(user_router)
app.include_router(chat_router)
app.include_router(metrics_router)
app.include_router(whatsapp_router)
app.include_router(onboarding_router)
