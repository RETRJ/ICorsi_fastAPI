from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import BackgroundTasks
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):

    yield



app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


async def check_and_parse_data(data: str, interval: int = 5):
    while True:
        result = await parse_data(data)  # Simulates checking and parsing data
        print(result)  # Replace with actual logging or processing
        await asyncio.sleep(interval)


@app.on_event("startup")
async def start_parsing(data: str, background_tasks: BackgroundTasks, interval: int = 5):
    background_tasks.add_task(check_and_parse_data, data, interval)
    return {"message": "Background parsing started"}
