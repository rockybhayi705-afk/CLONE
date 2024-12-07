# Copyright (C) 2024 @jithumon
#
# This file is part of clonebot.

import asyncio
from sqlite3 import OperationalError

from pyrogram import filters
from pyrogram.errors import FloodWait

from __main__ import bot
from clonebot.db.forward_sql import (
    get_dest_by_source,
    get_source_channels,
    init_database,
)

SOURCE_CHATS = []
file_groups = []


async def get_source():
    global SOURCE_CHATS
    while True:
        try:
            SOURCE_CHATS = await get_source_channels()
        except OperationalError:
            init_database()
        await asyncio.sleep(60)


@bot.on_message((filters.group | filters.channel), group=1)
async def file_copier(bot, message):
    curr_chat = message.chat.id
    if curr_chat in SOURCE_CHATS:
        dest_chats = await get_dest_by_source(curr_chat)
        for chat in dest_chats:
            if message.media_group_id:
                if message.media_group_id in file_groups:
                    return
                file_groups.append(message.media_group_id)
                messages = await message.get_media_group()
                for mess in messages:
                    await copy_message(mess, chat)
            else:
                await copy_message(message, chat)


async def copy_message(message, chat_id):
    try:
        await message.copy(chat_id)
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
        await copy_message(message, chat_id)


loop = asyncio.get_event_loop()
loop.create_task(get_source())
