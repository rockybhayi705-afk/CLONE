# Copyright (C) 2024 @jithumon
#
# This file is part of clonebot.

import asyncio
from datetime import datetime

import pytz
from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus, MessagesFilter
from pyrogram.errors import (
    ChannelInvalid,
    ChannelPrivate,
    FloodWait,
    PeerIdInvalid,
)
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyropatch import listen

from __main__ import bot, user
from clonebot import ADMINS, LOGGER

from clonebot.db.clone_sql import save_data
from clonebot.utils.file_support import unpack_new_file_id

limit_no = ""
skip_no = ""
caption = ""
IST = pytz.timezone("Asia/Kolkata")


@bot.on_message(filters.private & filters.command(["index"]) & filters.user(ADMINS))
async def index_files(bot, message):
    user_id = message.from_user.id
    id_mess = await message.reply_text(
        "Send me ID of the channel you want to index.",
        quote=True,
    )
    try:
        chat = await bot.listen_message(
            chat_id=user_id, filters=filters.text, timeout=300
        )
    except TimeoutError:
        await chat.edit_text(
            "Error!!\n\nRequest timed out.\nRestart by using /index",
        )
        return

    channel_id = chat.text

    if not channel_id.startswith("-100"):
        await chat.reply_text("Wrong Channel ID")
        return

    try:
        get_user = await bot.get_chat_member(int(channel_id), "me")
        if (
            get_user.status == ChatMemberStatus.ADMINISTRATOR
            or get_user.status == ChatMemberStatus.OWNER
        ):
            worker = "bot"
    except (ChannelInvalid, ChannelPrivate, PeerIdInvalid):
        bot_err = await chat.reply_text(
            "Unable to access chat with bot, trying to access with USER..."
        )
        get_user = await user.get_chat_member(int(channel_id), "me")
        if (
            get_user.status == ChatMemberStatus.ADMINISTRATOR
            or get_user.status == ChatMemberStatus.OWNER
            or get_user.status == ChatMemberStatus.MEMBER
        ):
            worker = "user"
        else:
            await bot_err.edit_text("I cannot access this channel, please try again")
            return

    MSG_STR_BTN = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "From Starting", callback_data=f"frm_0_{worker}_{channel_id}"
                ),
                InlineKeyboardButton(
                    "From Specific Message",
                    callback_data=f"frm_spc_{worker}_{channel_id}",
                ),
            ]
        ]
    )
    if worker == "bot":
        indx_ms = "Got access to chat with Bot. Indexing will be done with **Bot** & cloning will be faster than with User."
    elif worker == "user":
        indx_ms = "Got access to chat with User. Indexing will be done with **User** & **cloning will be much slower than with Bot.**"

    await chat.reply(
        text=f"{indx_ms}\n\nNow, please confirm from where do you want to start forwarding.",
        quote=True,
        reply_markup=MSG_STR_BTN,
    )
    await id_mess.delete()


@bot.on_callback_query(filters.regex("^frm_"))
async def clone_from_handler(bot, query):
    user_id = query.from_user.id
    data = query.data.split("_", 3)
    start = data[1]
    worker = data[2]
    frm_cnl_id = data[3]

    skip = None
    if start == "spc":
        mid_mss = await query.message.reply_text(
            "Send the count of message from where you want to start forwarding."
        )
        mess = mid_mss
        await query.message.delete()
        try:
            skip = await bot.listen_message(
                chat_id=user_id, filters=filters.text, timeout=300
            )
            skip_no = skip.text
        except TimeoutError:
            await mid_mss.edit_text(
                "Error!!\n\nRequest timed out.\nRestart by using /index",
            )
            return
    else:
        skip_no = 0
        mess = query.message

    try:
        skip_no = int(skip_no)
    except Exception:
        STR_BTN = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Start From Specific Message",
                        callback_data=f"frm_spc_{worker}_{frm_cnl_id}",
                    ),
                ]
            ]
        )
        if skip:
            await skip.reply(
                text="Thats an invalid ID, It should be an integer.\nTry again.",
                reply_markup=STR_BTN,
            )
        else:
            await mess.reply_text("Some error occured.")
            LOGGER.error(
                "Some error occured while setting start message count during indexing"
            )
        return

    MSG_END_BTN = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Till End", callback_data=f"till_0_{worker}_{frm_cnl_id}_{skip_no}"
                ),
                InlineKeyboardButton(
                    "Specific Count",
                    callback_data=f"till_spc_{worker}_{frm_cnl_id}_{skip_no}",
                ),
            ]
        ]
    )
    fd_ms = "Please confirm how many messages you want to forward."
    if start == "spc":
        await mess.reply(
            text=fd_ms,
            reply_markup=MSG_END_BTN,
        )
        await mess.delete()
    else:
        await mess.edit(
            text=fd_ms,
            reply_markup=MSG_END_BTN,
        )


@bot.on_callback_query(filters.regex("^till_"))
async def clone_till_handler(bot, query):
    user_id = query.from_user.id
    data = query.data.split("_", 4)
    end = data[1]
    worker = data[2]
    frm_cnl_id = data[3]
    skip_no = data[4]

    limit = None
    if end == "spc":
        mid_mss = await query.message.reply_text(
            "Send the no. of messages you want to forward.\nThis no. of messages will be counted from the start count given earlier."
        )
        mess = mid_mss
        await query.message.delete()
        try:
            limit = await bot.listen_message(
                chat_id=user_id, filters=filters.text, timeout=300
            )
            limit_no = limit.text
        except TimeoutError:
            await mid_mss.edit_text(
                "Error!!\n\nRequest timed out.\nRestart by using /index",
            )
            return
    else:
        limit_no = 0
        mess = query.message

    try:
        limit_no = int(limit_no)
    except Exception:
        END_BTN = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Till Specific Message",
                        callback_data=f"till_spc_{worker}_{frm_cnl_id}_{skip_no}",
                    ),
                ]
            ]
        )
        if limit:
            await limit.reply(
                text="Thats an invalid ID, It should be an integer.\nTry again.",
                reply_markup=END_BTN,
            )
        else:
            await mess.reply_text("Some error occured.")
            LOGGER.error(
                "Some error occured while setting end message count during indexing"
            )
        return

    CAT_BTN = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "All Messages",
                    callback_data=f"cat_empty_{worker}_{frm_cnl_id}_{skip_no}_{limit_no}",
                )
            ],
            [
                InlineKeyboardButton(
                    "Document",
                    callback_data=f"cat_document_{worker}_{frm_cnl_id}_{skip_no}_{limit_no}",
                ),
                InlineKeyboardButton(
                    "Photos",
                    callback_data=f"cat_photo_{worker}_{frm_cnl_id}_{skip_no}_{limit_no}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "Videos",
                    callback_data=f"cat_video_{worker}_{frm_cnl_id}_{skip_no}_{limit_no}",
                ),
                InlineKeyboardButton(
                    "Audios",
                    callback_data=f"cat_audio_{worker}_{frm_cnl_id}_{skip_no}_{limit_no}",
                ),
            ],
        ]
    )
    fd_ms = "Now choose what type of messages you want to forward."
    if end == "spc":
        await mess.reply(
            text=fd_ms,
            reply_markup=CAT_BTN,
        )
        await mess.delete()
    else:
        await mess.edit(
            text=fd_ms,
            reply_markup=CAT_BTN,
        )


@bot.on_callback_query(filters.regex("^cat_"))
async def category_handler(bot, query):
    data = query.data.split("_", 5)
    cat = data[1]
    worker = data[2]
    frm_cnl_id = data[3]
    skip_no = data[4]
    limit_no = data[5]

    CAP_BTN = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "No Custom Caption",
                    callback_data=f"cap_0_{worker}_{frm_cnl_id}_{skip_no}_{limit_no}_{cat}",
                ),
                InlineKeyboardButton(
                    "Custom Caption Required",
                    callback_data=f"cap_spc_{worker}_{frm_cnl_id}_{skip_no}_{limit_no}_{cat}",
                ),
            ]
        ]
    )
    await query.message.edit(
        text="Please confirm you want to put a custom caption for the files or not.",
        reply_markup=CAP_BTN,
    )


@bot.on_callback_query(filters.regex("^cap_"))
async def caption_handler(bot, query):
    user_id = query.from_user.id
    data = query.data.split("_", 6)
    cap = data[1]
    worker = data[2]
    frm_cnl_id = data[3]
    skip_no = int(data[4])
    limit_no = int(data[5])
    cat = data[6]

    if cat == "document":
        fil = MessagesFilter.DOCUMENT
    elif cat == "empty":
        fil = MessagesFilter.EMPTY
    elif cat == "photo":
        fil = MessagesFilter.PHOTO
    elif cat == "video":
        fil = MessagesFilter.VIDEO
    elif cat == "audio":
        fil = MessagesFilter.AUDIO
    else:
        await query.message.reply("Something went wrong, restart by using /index")
        LOGGER.error("Something went wrong")
        return

    get_caption = None
    if cap == "spc":
        mid_mss = await query.message.reply_text(
            "Send the custom caption you want to set."
        )
        mess = mid_mss
        await query.message.delete()
        try:
            get_caption = await bot.listen_message(
                chat_id=user_id, filters=filters.text, timeout=300
            )
            caption = get_caption.text
        except TimeoutError:
            await mid_mss.edit_text(
                "Error!!\n\nRequest timed out.\nRestart by using /index",
            )
            return
        indx_strt = await mess.reply("Indexing Started...")
        await mess.delete()
    else:
        caption = None
        mess = query.message
        indx_strt = await mess.edit("Indexing Started...")

    msg_count = 0
    mcount = 0
    saved = 0
    skipped = 0
    from_chat = int(frm_cnl_id)
    try:
        print(skip_no)
        print(limit_no)
        async for msg in user.search_messages(
            chat_id=from_chat, offset=skip_no, limit=limit_no, filter=fil
        ):
            if worker == "bot":
                msg = await bot.get_messages(from_chat, msg.id)
            elif worker == "user":
                msg = await user.get_messages(from_chat, msg.id)
            else:
                LOGGER.error("Something went wrong while indexing")
                await indx_strt.edit(
                    text="Something went wrong, restart by using /index"
                )
                return
            msg_caption = ""
            if caption is not None:
                msg_caption = caption
            elif msg.caption:
                msg_caption = msg.caption
            if cat in ("document", "photo", "video", "audio"):
                for file_type in ("document", "photo", "video", "audio"):
                    media = getattr(msg, file_type, None)
                    if media is not None:
                        if worker == "bot":
                            file_id, file_ref = unpack_new_file_id(media.file_id)
                        elif worker == "user":
                            file_id = media.file_id
                        file_type = cat
                        file_name = media.file_name
                        break
            if cat == "empty":
                for file_type in ("document", "photo", "video", "audio"):
                    media = getattr(msg, str(file_type), None)
                    if media is not None:
                        if worker == "bot":
                            file_id, file_ref = unpack_new_file_id(media.file_id)
                        elif worker == "user":
                            file_id = media.file_id
                        file_type = file_type
                        file_name = media.file_name
                        break
                else:
                    file_id = f"{from_chat}_{msg.id}"
                    file_type = "messages"
                    file_name = f"message_{from_chat}_{msg.id}"
            message_id = msg.id
            try:
                save = await save_data(
                    file_name,
                    file_id,
                    str(from_chat),
                    message_id,
                    worker,
                    msg_caption,
                    file_type,
                )
                if save:
                    saved += 1
                else:
                    skipped += 1
            except Exception as e:
                LOGGER.error(e)
                await indx_strt.reply(f"Error:\n{e}")
                return
            msg_count += 1
            mcount += 1
            new_skip_no = str(skip_no + msg_count)
            if mcount == 100:
                try:
                    datetime_ist = datetime.now(IST)
                    ISTIME = datetime_ist.strftime("%I:%M:%S %p - %d %B %Y")
                    await indx_strt.edit(
                        text=f"Total Indexed : `{msg_count}`\nCurrent skip_no:`{new_skip_no}`\nLast edited at `{ISTIME}`"
                    )
                    mcount -= 100
                except FloodWait as e:
                    LOGGER.warning("Floodwait while indexing, sleeping for %s", e.value)
                    await asyncio.sleep(e.value)
                except Exception as e:
                    LOGGER.error(e)
                    await indx_strt.reply(f"Error:\n{e}")
                    return
        await indx_strt.edit(
            f"Succesfully Indexed `{msg_count}` messages.\nSaved: `{saved}`\nDuplicate/Skipped: `{skipped}`"
        )
        LOGGER.info("Succesfully Indexed %s messages", msg_count)
    except Exception as e:
        LOGGER.error(e)
        await indx_strt.edit_text(f"Error:\n{e}")
