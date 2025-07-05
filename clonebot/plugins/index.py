# Copyright (C) 2024 @jithumon
#
# This file is part of clonebot.

import asyncio
from datetime import datetime
from typing import AsyncGenerator, Union

import pytz
from pyrogram import filters, types
from pyrogram.enums import ChatMemberStatus, MessageMediaType
from pyrogram.errors import (
    ChannelInvalid,
    ChannelPrivate,
    FloodWait,
    PeerIdInvalid,
)
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from __main__ import bot, user
from clonebot import ADMINS, LOGGER, SESSION

from clonebot.db.clone_sql import save_data_batch
from clonebot.utils.file_support import unpack_new_file_id

lock = asyncio.Lock()
limit_no = ""
skip_no = ""
index_task = None
IST = pytz.timezone("Asia/Kolkata")


@bot.on_message(filters.private & filters.command(["index"]) & filters.user(ADMINS))
async def index_files(bot, message):
    if lock.locked():
        await message.reply("Wait until the previous process completes.")
        return
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
        await id_mess.edit_text(
            "Error!!\n\nRequest timed out.\nRestart by using /index",
        )
        return

    channel_id = chat.text

    if not channel_id.startswith("-100"):
        await chat.reply_text(
            "Wrong Channel ID, kindly check again and retry with /index"
        )
        return

    try:
        get_user = await bot.get_chat_member(int(channel_id), "me")
        if (
            get_user.status == ChatMemberStatus.ADMINISTRATOR
            or get_user.status == ChatMemberStatus.OWNER
        ):
            worker = "bot"
    except (ChannelInvalid, ChannelPrivate, PeerIdInvalid):
        if SESSION:
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
                await bot_err.edit_text(
                    "I cannot access this channel, please try again"
                )
                return
        else:
            await chat.reply_text(
                "I'm unable to access this chat as a bot. Kindly check if I'm admin there or add user session if can't make me admin"
            )
            return

    MSG_STR_BTN = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "From Starting", callback_data=f"frm_1_{worker}_{channel_id}"
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
        text=f"{indx_ms}\n\nNow, please confirm the message id from where do you want to start forwarding.",
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
            "Send the ID of message from where you want to start forwarding."
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
                        "Start From Specific Message ID",
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
                # InlineKeyboardButton(
                #     "Till End", callback_data=f"till_0_{worker}_{frm_cnl_id}_{skip_no}"
                # ),
                InlineKeyboardButton(
                    "Till Message ID",
                    callback_data=f"till_spc_{worker}_{frm_cnl_id}_{skip_no}",
                ),
            ]
        ]
    )
    fd_ms = "Please confirm till where you want to forward."
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
            "Send the Message ID till where you want to forward."
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
                        "Till Message ID",
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
                    "Documents & Videos",
                    callback_data=f"cat_docvid_{worker}_{frm_cnl_id}_{skip_no}_{limit_no}",
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
    skip_no = int(data[4])
    limit_no = int(data[5])
    global index_task
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Cancel", callback_data="cancel_index"),
            ]
        ]
    )

    mess = query.message
    indx_strt = await mess.edit(
        "Indexing Started...\nCount will be updated after every 250 files.",
        reply_markup=kb,
    )

    index_task = asyncio.create_task(
        index_handler(
            bot, query, frm_cnl_id, worker, indx_strt, cat, skip_no, limit_no
        )
    )


async def index_handler(
    bot, query, frm_cnl_id, worker, indx_strt, cat, skip_no, limit_no
):
    current = skip_no
    msg_count = 0
    saved = 0
    skipped = 0
    from_chat = int(frm_cnl_id)

    batch_size = 100
    batch_data = []
    media_groups = {}
    processed_groups = set()

    async with lock:
        try:
            if worker == "bot":
                robot = bot
            elif worker == "user":
                robot = user
            else:
                LOGGER.error("Something went wrong while indexing")
                await indx_strt.edit(
                    text="Something went wrong, restart by using /index"
                )
                return

            async for msg in iter_messages(robot, from_chat, limit_no, current):
                if msg.empty or msg.service:
                    continue

                file_name = ""
                msg_caption = msg.caption

                media_types = {
                    "document": MessageMediaType.DOCUMENT,
                    "photo": MessageMediaType.PHOTO,
                    "video": MessageMediaType.VIDEO,
                    "audio": MessageMediaType.AUDIO,
                }
                media_types_2 = {
                    "document": MessageMediaType.DOCUMENT,
                    "video": MessageMediaType.VIDEO,
                }

                file_id = None
                file_type = None
                file_name = None

                if msg.media_group_id:
                    if msg.media_group_id not in media_groups:
                        media_groups[msg.media_group_id] = []
                    media_groups[msg.media_group_id].append(msg)
                    
                    msg_count += 1
                    current += 1
                    continue

                if cat in ("document", "photo", "video", "audio"):
                    if msg.media and msg.media.value == cat:
                        file_id, file_type, file_name = await get_file_det(msg, worker)
                elif cat == "docvid":
                    if msg.media and msg.media.value in ["document", "video"]:
                        file_id, file_type, file_name = await get_file_det(msg, worker)
                elif cat == "empty":
                    if msg.media:
                        file_id, file_type, file_name = await get_file_det(msg, worker)
                    else:
                        file_id = f"{from_chat}_{msg.id}"
                        file_type = "messages"
                        file_name = f"message_{from_chat}_{msg.id}"

                if file_name:
                    batch_data.append(
                        {
                            "file_name": file_name,
                            "file_id": file_id,
                            "from_channel": str(from_chat),
                            "file_type": file_type,
                            "message_id": msg.id,
                            "use": "clone",
                            "worker": worker,
                            "caption": msg_caption,
                        }
                    )

                    msg_count += 1
                    current += 1

                    if len(batch_data) >= batch_size:
                        try:
                            batch_saved, batch_skipped = await save_data_batch(
                                batch_data
                            )
                            saved += batch_saved
                            skipped += batch_skipped
                            batch_data = []
                        except Exception as e:
                            LOGGER.error(f"Batch processing error: {e}")
                            await indx_strt.reply(f"Batch Error:\n{e}")
                            return

                    if msg_count % 250 == 0:
                        kb = InlineKeyboardMarkup(
                            [
                                [
                                    InlineKeyboardButton(
                                        "Cancel", callback_data="cancel_index"
                                    ),
                                ]
                            ]
                        )
                        try:
                            datetime_ist = datetime.now(IST)
                            ISTIME = datetime_ist.strftime("%I:%M:%S %p - %d %B %Y")
                            await indx_strt.edit(
                                text=f"Total Indexed : `{msg_count}`\nSaved:`{saved}`\nSkipped:`{skipped}`\nLast edited at `{ISTIME}`",
                                reply_markup=kb,
                            )
                        except FloodWait as e:
                            LOGGER.warning(
                                "Floodwait while indexing, sleeping for %s", e.value
                            )
                            await asyncio.sleep(e.value)
                        except ValueError as e:
                            LOGGER.error(e)
                            await indx_strt.reply(f"Error:\n{e}")
                            return

            for media_group_id, group_messages in media_groups.items():
                if media_group_id in processed_groups:
                    continue
                
                group_messages.sort(key=lambda x: x.id)
                
                combined_caption = ""
                captions = []
                for group_msg in group_messages:
                    if group_msg.caption:
                        captions.append(group_msg.caption)
                
                if captions:
                    combined_caption = "\n\n".join(captions)
                
                for idx, group_msg in enumerate(group_messages):
                    file_id = None
                    file_type = None
                    file_name = None
                    
                    if cat in ("document", "photo", "video", "audio"):
                        if group_msg.media and group_msg.media.value == cat:
                            file_id, file_type, file_name = await get_file_det(group_msg, worker)
                    elif cat == "docvid":
                        if group_msg.media and group_msg.media.value in ["document", "video"]:
                            file_id, file_type, file_name = await get_file_det(group_msg, worker)
                    elif cat == "empty":
                        if group_msg.media:
                            file_id, file_type, file_name = await get_file_det(group_msg, worker)
                    
                    if file_name:
                        caption_to_use = combined_caption if idx == 0 else group_msg.caption
                        
                        batch_data.append(
                            {
                                "file_name": f"{file_name}_group_{idx+1}",
                                "file_id": file_id,
                                "from_channel": str(from_chat),
                                "file_type": file_type,
                                "message_id": group_msg.id,
                                "use": "clone",
                                "worker": worker,
                                "caption": caption_to_use,
                            }
                        )
                
                processed_groups.add(media_group_id)

            if batch_data:
                try:
                    batch_saved, batch_skipped = await save_data_batch(batch_data)
                    saved += batch_saved
                    skipped += batch_skipped
                except Exception as e:
                    LOGGER.error(f"Final batch processing error: {e}")

            await indx_strt.edit(
                f"Successfully Indexed `{msg_count}` messages.\nSaved: `{saved}`\nDuplicate/Skipped: `{skipped}`"
            )
            LOGGER.info(
                "Successfully Indexed %s messages. Saved: %s, Skipped: %s",
                msg_count,
                saved,
                skipped,
            )

        except FloodWait as e:
            LOGGER.warning("Floodwait while indexing, sleeping for %s", e.value)
            await asyncio.sleep(e.value)
            await indx_strt.edit("Continuing indexing after Floodwait...")
            await index_handler(bot, query, skip_no=current)
        except Exception as e:
            LOGGER.error(f"Error during indexing: {e}")
            await indx_strt.edit_text(f"Error:\n{e}")


async def get_file_det(msg, worker):
    media = getattr(msg, msg.media.value, None)
    if media is not None:
        if worker == "bot":
            file_id, file_ref = unpack_new_file_id(media.file_id)
        elif worker == "user":
            file_id = media.file_id
        file_type = msg.media.value

        if file_type == "photo":
            file_name = file_id
        else:
            file_name = getattr(media, "file_name", None)
            if file_name is None:
                file_name = file_id
    return file_id, file_type, file_name


async def iter_messages(
    bot,
    chat_id: Union[int, str],
    limit: int,
    offset: int = 0,
) -> AsyncGenerator["types.Message", None]:
    current = offset
    while current < offset + limit:
        new_diff = min(200, offset + limit - current)
        if new_diff <= 0:
            return
        try:
            messages = await bot.get_messages(
                chat_id=chat_id,
                message_ids=list(range(current, current + new_diff + 1)),
            )
            for message in messages:
                yield message
                current += 1
        except Exception as e:
            LOGGER.error(f"Error fetching messages: {e}")
            return


@bot.on_callback_query(filters.regex(r"^cancel_index"))
async def cancel_indexing(bot, query):
    global index_task
    user_id = query.from_user.id
    if index_task and not index_task.done():
        index_task.cancel()
        await query.message.edit("Indexing cancelled.")
        LOGGER.info("User requested cancellation of indexing.. : %s", user_id)
    else:
        await query.message.edit("No active indexing process to cancel.")
