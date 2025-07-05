# Copyright (C) 2024 @jithumon
#
# This file is part of clonebot.

import asyncio
import random
from datetime import datetime

import pytz
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.errors.exceptions.bad_request_400 import (
    FileReferenceEmpty,
    FileReferenceExpired,
    MediaEmpty,
)

from __main__ import bot, user
from clonebot import ADMINS, LOGGER, OWNER_ID
from clonebot.db.clone_sql import (
    count_documents,
    delete_data,
    delete_files,
    get_search_results,
)

IST = pytz.timezone("Asia/Kolkata")
MessageCount = 0
BOT_STATUS = "0"
status = set(int(x) for x in (BOT_STATUS).split())


@bot.on_message(filters.command("status") & filters.user(ADMINS))
async def count(bot, message):
    if 1 in status:
        await message.reply_text("Currently Bot is forwarding messages.")
    if 2 in status:
        await message.reply_text("Now Bot is Sleeping")
    if 1 not in status and 2 not in status:
        await message.reply_text("Bot is Idle now, You can start a task.")


@bot.on_message(filters.command("total") & filters.user(ADMINS))
async def total(bot, message):
    msg = await message.reply("Counting total messages in DB...", quote=True)
    try:
        total = await count_documents()
        await msg.edit(f"Total Files/Messages: {total}")
    except Exception as e:
        LOGGER.error(e)
        await msg.edit(f"Error: {e}")


@bot.on_message(filters.command("cleardb") & filters.user(OWNER_ID))
async def clrdb(bot, message):
    msg = await message.reply("Clearing files from DB...", quote=True)
    try:
        drop = await delete_files()
        if drop:
            LOGGER.info("Cleared DB")
            await msg.edit("Cleared DB")
        else:
            LOGGER.error("Error clearing DB")
            await msg.edit("Error clearing DB")
    except Exception as e:
        LOGGER.error(e)
        await msg.edit(f"Error: {e}")


@bot.on_message(filters.command("clone") & filters.user(ADMINS))
async def forward(bot, message):
    user_id = message.from_user.id
    await message.reply_text(
        "Send me ID of the channel you want to clone the files/messages to",
        quote=True,
    )
    try:
        chat = await bot.listen_message(
            chat_id=user_id, filters=filters.text, timeout=300
        )
    except TimeoutError:
        await chat.edit_text(
            "Error!!\n\nRequest timed out.\nRestart by using /clone",
        )
        return

    dest_chat_id = chat.text
    
    if 1 in status:
        await message.reply_text("A task is already running.")
        return
    if 2 in status:
        await message.reply_text("Sleeping the engine for avoiding ban.")
        return
    strt_fwd = await message.reply_text(text="Started Forwarding", quote=True)
    global MessageCount
    mcount = random.randint(10000, 15300)
    acount = random.randint(5000, 6000)
    bcount = random.randint(1500, 2000)
    ccount = random.randint(250, 300)
    while await count_documents() != 0:
        data = await get_search_results()
        for msg in data:
            channel = msg.from_channel
            file_id = msg.file_id
            message_id = int(msg.message_id)
            worker = msg.worker
            caption = msg.caption
            file_type = msg.file_type
            chat_id = int(dest_chat_id)
            if worker == "bot":
                try:
                    if file_type in ("document", "photo", "video", "audio"):
                        try:
                            mess = await bot.send_cached_media(
                                chat_id=chat_id, file_id=file_id, caption=caption
                            )
                            
                        except (
                            FileReferenceExpired,
                            FileReferenceEmpty,
                            MediaEmpty,
                            ValueError,
                        ) as e:
                            LOGGER.error(f"Invalid file_id {file_id}: {e}")
                            try:                          
                                mess = await bot.copy_message(
                                chat_id=chat_id,
                                from_chat_id=channel,
                                caption=caption,
                                message_id=message_id,
                            )
                            except Exception as e:
                                LOGGER.error(f"Error: {e}")
                        await delete_data(file_id, channel, message_id)
                    else:
                        await bot.copy_message(
                            chat_id=chat_id,
                            from_chat_id=channel,
                            caption=caption,
                            message_id=message_id,
                        )
                    await asyncio.sleep(1)
                    try:
                        status.add(1)
                    except Exception:
                        pass
                    try:
                        status.remove(2)
                    except Exception:
                        pass
                except FloodWait as e:
                    LOGGER.warning(f"Floodwait of {e} sec")
                    await asyncio.sleep(e.value)
                    if file_type in ("document", "photo", "video", "audio"):
                        try:
                            mess = await bot.send_cached_media(
                                chat_id=chat_id, file_id=file_id, caption=caption
                            )
                        except (
                            FileReferenceExpired,
                            FileReferenceEmpty,
                            MediaEmpty,
                            ValueError,
                        ) as e:
                            LOGGER.error(f"Invalid file_id {file_id} after FloodWait: {e}")
                            await delete_data(file_id, channel, message_id)
                            continue
                    else:
                        await bot.copy_message(
                            chat_id=chat_id,
                            from_chat_id=channel,
                            caption=caption,
                            message_id=message_id,
                        )
                    await asyncio.sleep(1)
                except Exception as e:
                    LOGGER.error(f"Unexpected error: {e}")
                await delete_data(file_id, channel, message_id)
                MessageCount += 1
                try:
                    datetime_ist = datetime.now(IST)
                    ISTIME = datetime_ist.strftime("%I:%M:%S %p - %d %B %Y")
                    if MessageCount % 100 == 0:
                        await strt_fwd.edit(
                            text=f"Total Forwarded : `{MessageCount}`\nForwarded Using: Bot\nLast Forwarded at {ISTIME}"
                        )
                    LOGGER.info(
                        "Total Forwarded : %s, Forwarded Using: Bot, Last Forwarded at %s",
                        MessageCount,
                        ISTIME,
                    )
                except Exception as e:
                    LOGGER.error(e)
                    await message.reply_text(f"Error:\n{e}")
            elif worker == "user":
                channel = int(channel)
                if mcount:
                    if acount:
                        if bcount:
                            if ccount:
                                if file_type in ("document", "photo", "video", "audio"):
                                    try:
                                        await user.send_cached_media(
                                            chat_id=chat_id,
                                            file_id=file_id,
                                            caption=caption,
                                        )
                                    except (
                                        FileReferenceExpired,
                                        FileReferenceEmpty,
                                        MediaEmpty,
                                    ):
                                        await send_user_message(
                                            message,
                                            channel,
                                            message_id,
                                            file_type,
                                            chat_id,
                                            caption,
                                            user_id,
                                        )
                                    except Exception as e:
                                        LOGGER.error(e)
                                        await message.reply_text(f"Error:\n{e}")
                                else:
                                    try:
                                        await user.copy_message(
                                            chat_id=chat_id,
                                            from_chat_id=channel,
                                            caption=caption,
                                            message_id=message_id,
                                        )
                                    except Exception as e:
                                        LOGGER.error(e)
                                        await message.reply_text(f"Error:\n{e}")
                                await delete_data(file_id, channel, message_id)
                                try:
                                    status.add(1)
                                except Exception:
                                    pass
                                try:
                                    status.remove(2)
                                except Exception:
                                    pass

                                mcount -= 1
                                ccount -= 1
                                acount -= 1
                                bcount -= 1
                                MessageCount += 1
                                mainsleep = random.randint(3, 8)
                                try:
                                    datetime_ist = datetime.now(IST)
                                    ISTIME = datetime_ist.strftime(
                                        "%I:%M:%S %p - %d %B %Y"
                                    )
                                    if MessageCount % 100 == 0:
                                        await strt_fwd.edit(
                                            text=f"Total Forwarded : `{MessageCount}`\nForwarded Using: User\nSleeping for `{mainsleep}` Seconds\nLast Forwarded at `{ISTIME}`"
                                        )
                                    LOGGER.info(
                                        "Total Forwarded : %s, Forwarded Using: User, Sleeping for %s Seconds, Last Forwarded at %s",
                                        MessageCount,
                                        mainsleep,
                                        ISTIME,
                                    )
                                except FloodWait as e:
                                    LOGGER.warning(f"Floodwait of {e} sec")
                                    await asyncio.sleep(e.value)
                                except Exception as e:
                                    LOGGER.error(e)
                                    await message.reply_text(f"Error:\n{e}")
                                await asyncio.sleep(mainsleep)
                            else:
                                try:
                                    status.add(2)
                                except Exception:
                                    pass
                                try:
                                    status.remove(1)
                                except Exception:
                                    pass
                                csleep = random.randint(250, 500)
                                try:
                                    datetime_ist = datetime.now(IST)
                                    ISTIME = datetime_ist.strftime(
                                        "%I:%M:%S %p - %d %B %Y"
                                    )
                                    await strt_fwd.edit(
                                        text=f"You have send {MessageCount} messages.\nWaiting for {csleep} Seconds.\nLast Forwarded at {ISTIME}"
                                    )
                                    LOGGER.info(
                                        "Total Forwarded : %s, Waiting for %s Seconds, Last Forwarded at %s",
                                        MessageCount,
                                        csleep,
                                        ISTIME,
                                    )
                                except Exception as e:
                                    LOGGER.error(e)
                                    await message.reply_text(f"Error:\n{e}")

                                await asyncio.sleep(csleep)
                                ccount = random.randint(250, 300)
                                await strt_fwd.edit(f"Starting after {csleep}")
                                LOGGER.info("Starting after %s minutes", csleep / 60)
                        else:
                            try:
                                status.add(2)
                            except Exception:
                                pass
                            try:
                                status.remove(1)
                            except Exception:
                                pass
                            bsl = random.randint(1000, 1200)
                            try:
                                datetime_ist = datetime.now(IST)
                                ISTIME = datetime_ist.strftime("%I:%M:%S %p - %d %B %Y")
                                await strt_fwd.edit(
                                    text=f"You have send {MessageCount} messages.\nWaiting for {bsl} seconds.\nLast Forwarded at {ISTIME}"
                                )
                                LOGGER.info(
                                    "Total Forwarded : %s, Waiting for %s Seconds, Last Forwarded at %s",
                                    MessageCount,
                                    bsl,
                                    ISTIME,
                                )
                            except Exception as e:
                                LOGGER.error(e)
                                await message.reply_text(f"Error:\n{e}")

                            await asyncio.sleep(bsl)
                            bcount = random.randint(1500, 2000)
                            await strt_fwd.edit(f"Starting after {bsl}")
                            LOGGER.info("Starting after %s minutes", bsl / 60)
                    else:
                        try:
                            status.add(2)
                        except Exception:
                            pass
                        try:
                            status.remove(1)
                        except Exception:
                            pass
                        asl = random.randint(1500, 2000)
                        try:
                            datetime_ist = datetime.now(IST)
                            ISTIME = datetime_ist.strftime("%I:%M:%S %p - %d %B %Y")
                            await strt_fwd.edit(
                                text=f"You have send {MessageCount} messages.\nWaiting for {asl} seconds.\nLast Forwarded at {ISTIME}"
                            )
                            LOGGER.info(
                                "Total Forwarded : %s, Waiting for %s Seconds, Last Forwarded at %s",
                                MessageCount,
                                asl,
                                ISTIME,
                            )
                        except Exception as e:
                            LOGGER.error(e)
                            await message.reply_text(f"Error:\n{e}")

                        await asyncio.sleep(asl)
                        acount = random.randint(5000, 6000)
                        await strt_fwd.edit(f"Starting after {asl}")
                        LOGGER.info("Starting after %s minutes", asl / 60)
                else:
                    try:
                        status.add(2)
                    except Exception:
                        pass
                    try:
                        status.remove(1)
                    except Exception:
                        pass
                    msl = random.randint(2000, 3000)
                    try:
                        datetime_ist = datetime.now(IST)
                        ISTIME = datetime_ist.strftime("%I:%M:%S %p - %d %B %Y")
                        await strt_fwd.edit(
                            text=f"You have send {MessageCount} messages.\nWaiting for {msl} seconds.\nLast Forwarded at {ISTIME}"
                        )
                        LOGGER.info(
                            "Total Forwarded : %s, Waiting for %s Seconds, Last Forwarded at %s",
                            MessageCount,
                            msl,
                            ISTIME,
                        )
                    except Exception as e:
                        LOGGER.error(e)
                        await message.reply_text(f"Error:\n{e}")

                    await asyncio.sleep(msl)
                    mcount = random.randint(10000, 15300)
                    await strt_fwd.edit(f"Starting after {msl}")
                    LOGGER.info("Starting after %s minutes", msl / 60)

    try:
        LOGGER.info("Finished: Total Forwarded : %s", MessageCount)
        await strt_fwd.edit(text=f"Succesfully Forwarded {MessageCount} messages")
    except Exception as e:
        LOGGER.error(e)
        await message.reply_text(f"Error:\n{e}")

    try:
        status.remove(1)
    except Exception:
        pass
    try:
        status.remove(2)
    except Exception:
        pass
    MessageCount = 0


async def send_user_message(
    message, channel, message_id, file_type, chat_id, caption, user_id
):
    try:
        fetch = await user.get_messages(channel, int(message_id))
        LOGGER.info("Fetching file from channel.")
        try:
            for file_type in ("document", "photo", "video", "audio"):
                media = getattr(fetch, file_type, None)
                if media is not None:
                    file_idn = media.file_id
                    break
            await user.send_cached_media(
                chat_id=chat_id, file_id=file_idn, caption=caption
            )
        except Exception as e:
            LOGGER.error(e)
            await message.reply_text(f"Error:\n{e}")
    except Exception as e:
        LOGGER.error(e)
        await message.reply_text(f"Error:\n{e}")
