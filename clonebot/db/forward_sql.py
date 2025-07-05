# Copyright (C) 2024 @jithumon
#
# This file is part of clonebot.

import asyncio
from contextlib import asynccontextmanager

import aiosqlite

from clonebot import LOGGER

FORWARD_DB = "forward.db"


@asynccontextmanager
async def get_db_connection():
    conn = await aiosqlite.connect(FORWARD_DB)
    try:
        yield conn
        await conn.commit()
    finally:
        await conn.close()


async def init_db():
    async with get_db_connection() as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_channel INTEGER NOT NULL,
                destination_channel INTEGER NOT NULL
            )
            """
        )


async def add_chats(source, destination):
    async with get_db_connection() as db:
        existing_chat = await db.execute(
            "SELECT 1 FROM chats WHERE source_channel = ? AND destination_channel = ?",
            (source, destination),
        )
        if await existing_chat.fetchone() is not None:
            LOGGER.info("Duplicate entry found, skipping addition.")
            return "exists"
        await db.execute(
            "INSERT INTO chats (source_channel, destination_channel) VALUES (?, ?)",
            (source, destination),
        )
        LOGGER.info(f"Added chat from {source} to {destination}")
        return True


async def remove_chats(source, destination):
    async with get_db_connection() as db:
        existing_chat = await db.execute(
            "SELECT 1 FROM chats WHERE source_channel = ? AND destination_channel = ?",
            (source, destination),
        )
        if await existing_chat.fetchone() is None:
            LOGGER.info("No chat found to remove.")
            return "not found"
        await db.execute(
            "DELETE FROM chats WHERE source_channel = ? AND destination_channel = ?",
            (source, destination),
        )
        LOGGER.info(f"Removed chat from {source} to {destination}")
        return True


async def get_chats(source):
    async with get_db_connection() as db:
        async with db.execute(
            "SELECT destination_channel FROM chats WHERE source_channel = ?", (source,)
        ) as cursor:
            return [int(row[0]) for row in await cursor.fetchall()]


async def get_all_chats():
    async with get_db_connection() as db:
        async with db.execute(
            "SELECT source_channel, destination_channel FROM chats"
        ) as cursor:
            return await cursor.fetchall()


async def get_source_channels():
    async with get_db_connection() as db:
        async with db.execute("SELECT source_channel FROM chats") as cursor:
            source_channels = await cursor.fetchall()
            return [int(row[0]) for row in source_channels]


async def get_dest_by_source(source):
    async with get_db_connection() as db:
        async with db.execute(
            "SELECT destination_channel FROM chats WHERE source_channel = ?",
            (source,),
        ) as cursor:
            destination_channels = await cursor.fetchall()
            return [int(row[0]) for row in destination_channels]


def init_database():
    try:
        asyncio.get_running_loop()
        asyncio.create_task(init_db())
    except RuntimeError:
        asyncio.run(init_db())


init_database()
