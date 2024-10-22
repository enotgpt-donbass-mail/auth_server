import contextlib
import os
from typing import AsyncIterator

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

import orm
from orm import get_session
from src.models import Role
from src.router import router


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    load_dotenv()
    orm.db_manager.init(os.getenv("DATABASE_URL"))
    await orm.db_manager.init_db()
    await Role.create_or_ignore(1, "user")
    yield
    await orm.db_manager.close()


app = FastAPI(title="E-notGPT. Авторизация.", lifespan=lifespan)
app.include_router(router, prefix="/api")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def unicorn_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": False, "error": exc.detail},
    )

if __name__ == "__main__":
    load_dotenv()
    uvicorn.run(
        app,
        host=os.getenv("APP_HOST"),
        port=int(os.getenv("APP_PORT"))
    )