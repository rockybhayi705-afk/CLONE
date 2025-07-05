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
                                file_name TEXT,
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

    await init_db()
    
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


async def save_data_batch(data_list):
    if not data_list:
        return 0, 0
    

    await init_db()
    
    data_schema = Data()
    valid_data = []
    validation_errors = 0
    
    for data in data_list:
        try:
            data_schema.load(data)
            valid_data.append((
                data["file_name"],
                data["file_id"], 
                data["from_channel"],
                data["file_type"],
                data["message_id"],
                "clone",
                data["worker"],
                data["caption"]
            ))
        except ValidationError as e:
            LOGGER.error(
                "Validation error occurred while saving file in Database. Error: %s", e
            )
            validation_errors += 1
    
    if not valid_data:
        return 0, len(data_list)
    
    saved_count = 0
    skipped_count = validation_errors
    
    try:
        async with get_db_connection() as db:
            cursor = await db.execute("SELECT COUNT(*) FROM Files")
            result = await cursor.fetchone()
            count_before = result[0] if result else 0
            
            await db.executemany(
                """INSERT OR IGNORE INTO Files (file_name, file_id, from_channel, file_type, message_id, use, worker, caption)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                valid_data
            )
            
            cursor = await db.execute("SELECT COUNT(*) FROM Files")
            result = await cursor.fetchone()
            count_after = result[0] if result else 0
            
            saved_count = count_after - count_before
            skipped_count += len(valid_data) - saved_count
            
            LOGGER.info(f"Batch saved {saved_count} files/messages to Database, skipped {skipped_count}")
            return saved_count, skipped_count
            
    except Exception as e:
        LOGGER.error(f"Error during batch save: {e}")
        return 0, len(data_list)


async def get_search_results():

    await init_db()
    
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

    await init_db()
    
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
