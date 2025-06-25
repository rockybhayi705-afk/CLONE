# Copyright (C) 2024 @jithumon
#
# This file is part of clonebot.

import asyncio
from sqlite3 import OperationalError

from pyrogram import filters
from pyrogram.errors import FloodWait
from pyrogram.types import LinkPreviewOptions

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
            await copy_message(message, chat)
        


async def copy_message(message, chat_id):
    mess = message
    mess.link_preview_options = LinkPreviewOptions(is_disabled=True)
    try:
        await mess.copy(chat_id)
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
        await copy_message(message, chat_id)
    await asyncio.sleep(1)


loop = asyncio.get_event_loop()
loop.create_task(get_source())
