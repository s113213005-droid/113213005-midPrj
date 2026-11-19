import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row

# 讀取 .env
load_dotenv()

# 從環境變數取得資料庫連線資訊
DATABASE_URL = os.getenv("DATABASE_URL")


# FastAPI 啟動與關閉時執行
@asynccontextmanager
async def lifespan(app: FastAPI):

    # 建立資料庫連線池
    app.state.pool = AsyncConnectionPool(
        conninfo=DATABASE_URL,
        kwargs={"autocommit": True, "row_factory": dict_row},
        open=False,
        min_size=1,
        max_size=10,
    )

    # 開啟連線池
    await app.state.pool.open()

    print("Connected to PostgreSQL")

    yield

    # 關閉連線池
    await app.state.pool.close()

    print("Disconnected from PostgreSQL")


# 提供資料庫連線給 API 使用
async def getDB(request: Request):
    async with request.app.state.pool.connection() as conn:
        yield conn

