import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any
from fastapi import FastAPI
import parser_body

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(parser_body.parser_worker(15))
    yield
    print('SHUT DOWN')



app = FastAPI(lifespan=lifespan)



@app.post("/webhook/add_course/")
async def webhook(payload: Dict[Any, Any]):
    print(payload)
    await parser_body.add_course(payload['data'])

    return 200



