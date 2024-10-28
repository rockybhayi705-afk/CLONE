# Copyright (C) 2024 @jithumon
#
# This file is part of clonebot.

import asyncio
import os
import shutil
import sys
import time

from psutil import cpu_percent, disk_usage, virtual_memory
from pyrogram import Client, filters
from pyrogram.types import LinkPreviewOptions

from __main__ import bot
from clonebot import ADMINS, LOGGER
from clonebot.utils.constants import (
    ABT_MSG,
    HELP_KB,
    HELP_RET_KB,
    HELPMSG,
    START_KB,
    STARTMSG,
    DISCL_TXT,
    STRT_RET_KB
)
from clonebot.utils.util_support import humanbytes


@bot.on_callback_query(filters.regex(r"^start_cb$"))
@bot.on_message(filters.command(["start"]))
async def start(bot, update):
    user_id = update.from_user.id
    name = update.from_user.first_name if update.from_user.first_name else " "

    if isinstance(update, filters.CallbackQuery):
        await update.message.edit_text(
            text=STARTMSG.format(name, user_id), reply_markup=START_KB
        )
    else:
        await bot.send_message(
            chat_id=update.chat.id,
            message_effect_id=5046509860389126442,
            text=STARTMSG.format(name, user_id),
            reply_to_message_id=update.reply_to_message_id,
            reply_markup=START_KB,
            # web_page_preview=False,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )


@bot.on_callback_query(filters.regex(r"^help_cb$"))
@bot.on_message(filters.command(["help"]))
async def help_m(bot, message):
    if isinstance(message, filters.CallbackQuery):
        await message.message.edit_text(text=HELPMSG, reply_markup=HELP_KB)
    else:
        await bot.send_message(
            chat_id=message.chat.id,
            text=HELPMSG,
            reply_to_message_id=message.reply_to_message_id,
            reply_markup=HELP_KB,
            # web_page_preview=False,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )


@bot.on_callback_query(filters.regex(r"^about$"))
async def about_cb(bot, query):
    await query.message.edit_text(
        ABT_MSG,
        reply_markup=HELP_RET_KB,
        # web_page_preview=False,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )

@bot.on_callback_query(filters.regex("^disc_"))
async def disclaimer_sb(bot, query):
    data = query.data.split("_", 1)
    menu = data[1]
    if menu == "str":
        kb = STRT_RET_KB
    else:
        kb = HELP_RET_KB
    await query.message.edit_text(
        DISCL_TXT,
        reply_markup=kb,
        # web_page_preview=False,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )

@bot.on_message(filters.command(["restart"]) & filters.user(ADMINS))
async def restart(bot, update):
    LOGGER.warning("Restarting bot using /restart command")
    msg = await update.reply_text(text="__Restarting.....__", quote=True)
    await asyncio.sleep(5)
    try:
        shutil.rmtree("clonebot/.downloads/")
    except Exception as e:
        LOGGER.exception(e)
    await msg.edit("__Bot restarted !__")
    os.execv(sys.executable, ["python3", "-m", "clonebot"] + sys.argv)


@bot.on_message(filters.command(["logs"]) & filters.user(ADMINS))
async def log_file(bot, update):
    logs_msg = await update.reply("__Sending logs, please wait...__", quote=True)
    try:
        await update.reply_document("logs.txt")
    except Exception as e:
        await update.reply(str(e))
    await logs_msg.delete()


@bot.on_message(filters.command(["server"]) & filters.user(ADMINS))
async def server_stats(bot, update):
    sts = await update.reply_text("__Calculating, please wait...__", quote=True)
    total, used, free = shutil.disk_usage(".")
    ram = virtual_memory()
    start_t = time.time()
    end_t = time.time()
    time_taken_s = (end_t - start_t) * 1000

    ping = f"{time_taken_s:.3f} ms"
    total = humanbytes(total)
    used = humanbytes(used)
    free = humanbytes(free)
    t_ram = humanbytes(ram.total)
    u_ram = humanbytes(ram.used)
    f_ram = humanbytes(ram.available)
    cpu_usage = cpu_percent()
    ram_usage = virtual_memory().percent
    used_disk = disk_usage("/").percent
    db_size = "SQLite"

    stats_msg = f"--**BOT STATS**--\n`Ping: {ping}`\n\n--**SERVER DETAILS**--\n`Disk Total/Used/Free: {total}/{used}/{free}\nDisk usage: {used_disk}%\nRAM Total/Used/Free: {t_ram}/{u_ram}/{f_ram}\nRAM Usage: {ram_usage}%\nCPU Usage: {cpu_usage}%`\n\n--**DATABASE DETAILS**--\n`{db_size}`"
    try:
        await sts.edit(stats_msg)
    except Exception as e:
        await update.reply_text(str(e), quote=True)
