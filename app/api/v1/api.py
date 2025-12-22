from fastapi import FastAPI
from app.api.v1.route import fetchData
app = FastAPI()

app.include_router(fetchData.router)
