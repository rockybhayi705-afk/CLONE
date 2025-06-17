# Copyright (C) 2024 @jithumon
#
# This file is part of clonebot.

import asyncio
from collections import namedtuple
from contextlib import asynccontextmanager

import aiosqlite
from marshmallow import Schema, ValidationError, fields

from clonebot import LOGGER

CLONE_DB = "clone.db"


class Data(Schema):
    file_name = fields.Str()
    file_id = fields.Str(required=True)
    from_channel = fields.Str()
    file_type = fields.Str()
    message_id = fields.Int()
    use = fields.Str(load_default="clone")
    worker = fields.Str()
    caption = fields.Str()


@asynccontextmanager
async def get_db_connection():
    conn = await aiosqlite.connect(CLONE_DB)
    try:
        yield conn
        await conn.commit()
    finally:
        await conn.close()


async def init_db():
    async with get_db_connection() as db:
        await db.execute(
            """CREATE TABLE IF NOT EXISTS Files (
                                file_name TEXT UNIQUE,
                                file_id TEXT PRIMARY KEY,
                                from_channel TEXT,
                                file_type TEXT,
                                message_id INTEGER,
                                use TEXT DEFAULT 'clone',
                                worker TEXT,
                                caption TEXT
                            )"""
        )


async def save_data(
    file_name, file_id, from_channel, message_id, worker, caption, file_type
):
    data_schema = Data()
    try:
        data_schema.load(
            {
                "file_name": file_name,
                "file_id": file_id,
                "from_channel": from_channel,
                "file_type": file_type,
                "message_id": message_id,
                "use": "clone",
                "worker": worker,
                "caption": caption,
            }
        )
    except ValidationError as e:
        LOGGER.error(
            "Validation error occurred while saving file in Database. Error: %s", e
        )
        return False

    try:
        async with get_db_connection() as db:
            await db.execute(
                """INSERT INTO Files (file_name, file_id, from_channel, file_type, message_id, use, worker, caption)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    file_name,
                    file_id,
                    from_channel,
                    file_type,
                    message_id,
                    "clone",
                    worker,
                    caption,
                ),
            )
            LOGGER.info("File/Message saved to Database: %s", file_name)
            return True
    except aiosqlite.IntegrityError:
        LOGGER.info("File/Message is already saved in Database: %s", file_name)
        return False


async def get_search_results():
    FileRecord = namedtuple(
        "FileRecord",
        [
            "file_name",
            "file_id",
            "from_channel",
            "file_type",
            "message_id",
            "use",
            "worker",
            "caption",
        ],
    )
    async with get_db_connection() as db:
        async with db.execute("SELECT * FROM Files") as cursor:
            rows = await cursor.fetchall()
            messages = [FileRecord(*row) for row in rows]
            return messages


async def count_documents():
    async with get_db_connection() as db:
        async with db.execute("SELECT COUNT(*) FROM Files") as cursor:
            result = await cursor.fetchone()
            total = result[0] if result else 0
    return total


async def delete_files():
    async with get_db_connection() as db:
        try:
            await db.execute("DELETE FROM Files")
            await db.commit()
            return True
        except Exception as e:
            LOGGER.error(f"Error deleting files: {e}")
            return False


async def delete_data(file_id, from_channel, message_id):
    async with get_db_connection() as db:
        try:
            result = await db.execute(
                """DELETE FROM Files 
                   WHERE file_id = ? AND from_channel = ? AND message_id = ?""",
                (file_id, from_channel, message_id),
            )
            await db.commit()

            if result.rowcount > 0:
                LOGGER.info("File/Message deleted from Database: %s", file_id)
                return True
            else:
                LOGGER.info(
                    "No file/message found to delete with file_id: %s, from_channel: %s, message_id: %s",
                    file_id,
                    from_channel,
                    message_id,
                )
                return False
        except Exception as e:
            LOGGER.error(f"Error deleting data from the database: {e}")
            return False


def init_database():
    try:
        asyncio.get_running_loop()
        asyncio.create_task(init_db())
    except RuntimeError:
        asyncio.run(init_db())


init_database()
