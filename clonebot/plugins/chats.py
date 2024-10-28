# Copyright (C) 2024 @jithumon
#
# This file is part of clonebot.

from pyrogram import Client, filters

from __main__ import bot
from clonebot import ADMINS
from clonebot.db.forward_sql import add_chats, get_all_chats, remove_chats


@bot.on_message(filters.command("addchat") & filters.user(ADMINS))
async def add_chat_handler(bot, message):
    try:
        source_chat_id = int(message.command[1])
        dest_chat_id = int(message.command[2])
        add = await add_chats(source_chat_id, dest_chat_id)
        if add:
            if add == "exists":
                await message.reply_text(
                    f"Chat already exists: `{source_chat_id}` with destination: `{dest_chat_id}`"
                )
                return
            await message.reply_text(
                f"Chat Added: Source: `{source_chat_id}` - Destination: `{dest_chat_id}`"
            )
        else:
            message.reply_text("Some error occured while adding chat")
    except (IndexError, ValueError):
        await message.reply_text("Usage: /addchat SOURCE_CHAT_ID DEST_CHAT_ID")


@bot.on_message(filters.command("delchat") & filters.user(ADMINS))
async def delete_chat_handler(bot, message):
    try:
        source_chat_id = int(message.command[1])
        dest_chat_id = int(message.command[2])
        rem = await remove_chats(source_chat_id, dest_chat_id)
        if rem:
            if rem == "not found":
                await message.reply_text(
                    f"Source: `{source_chat_id}` with destination: `{dest_chat_id}` not found."
                )
                return
            await message.reply_text(
                f"Chat Deleted: Source: `{source_chat_id}` - Destination: `{dest_chat_id}`"
            )
        else:
            message.reply_text("Some error occured while removing chat")
    except (IndexError, ValueError):
        await message.reply_text("Usage: /delchat SOURCE_CHAT_ID DEST_CHAT_ID")


@bot.on_message(filters.command("listchats") & filters.user(ADMINS))
async def get_all_chats_handler(bot, message):
    try:
        chats = await get_all_chats()
        if not chats:
            await message.reply("No chats found.")
            return

        response = "**Active Chats:**\n"
        for source, destination in chats:
            response += f"**Source:** `{source}` - **Destination:** `{destination}`\n"
        await message.reply(response)
    except Exception as e:
        await message.reply(f"An error occurred: {str(e)}")
