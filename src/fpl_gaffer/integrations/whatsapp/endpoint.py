from fastapi import FastAPI
from fpl_gaffer.integrations.whatsapp.webhook import router

app = FastAPI()

@app.get("/")
async def home():
    return {"response": "App working, let's goooo!"}

app.include_router(router)
