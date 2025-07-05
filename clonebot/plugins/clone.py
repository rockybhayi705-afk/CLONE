# Copyright (C) 2024 @jithumon
#
# This file is part of clonebot.

import asyncio
import random
from datetime import datetime

import pytz
from pyrogram import filters
from pyrogram.errors import (
    FileReferenceEmpty,
    FileReferenceExpired,
    MediaEmpty,
    ChannelInvalid,
    PeerIdInvalid,
    ChannelPrivate,
    UserNotParticipant,
    FloodWait
)
from __main__ import bot, user
from clonebot import ADMINS, LOGGER
from clonebot.db.clone_sql import (
    count_documents,
    delete_data,
    delete_files,
    get_search_results,
    save_channels,
    get_channels,
    update_channel_progress,
    get_channel_by_number,
    clear_channels,
    get_custom_caption,
)

IST = pytz.timezone("Asia/Kolkata")
MessageCount = 0
BOT_STATUS = "0"
status = set(int(x) for x in (BOT_STATUS).split())


async def get_caption(original_caption, file_name):
    custom_caption = await get_custom_caption()
    if custom_caption:
        if "{file_name}" in custom_caption:
            return custom_caption.replace("{file_name}", file_name)
        else:
            return custom_caption
    else:
        return original_caption


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


@bot.on_message(filters.command("channels") & filters.user(ADMINS))
async def channel_status(bot, message):
    msg = await message.reply("Checking channel status...", quote=True)
    try:
        channels = await get_channels()
        if channels:
            status_text = "📊 **Channel Status:**\n\n"
            for channel in channels:
                status_text += (
                    f"Channel {channel.channel_number} ({channel.channel_id}):\n"
                )
                status_text += f"  • Pending: {channel.pending_files:,}\n"
                status_text += f"  • Processed: {channel.processed_files:,}\n"
                status_text += f"  • Status: {channel.status}\n\n"
            await msg.edit(status_text)
        else:
            await msg.edit("No active channels found.")
    except Exception as e:
        LOGGER.error(e)
        await msg.edit(f"Error: {e}")


@bot.on_message(filters.command("cleardb") & filters.user(ADMINS))
async def clrdb(bot, message):
    msg = await message.reply("Clearing files from DB...", quote=True)
    try:
        drop = await delete_files()
        cdrop = await clear_channels()
        if drop and cdrop:
            LOGGER.info("Cleared DB")
            await msg.edit("Cleared DB")
        elif drop:
            LOGGER.error("Error clearing files DB")
            await msg.edit("Error clearing files DB")
        elif cdrop:
            LOGGER.error("Error clearing channels DB")
            await msg.edit("Error clearing channels DB")
        else:
            LOGGER.error("Error clearing files and channels DB")
            await msg.edit("Error clearing files and channels DB")
    except Exception as e:
        LOGGER.error(e)
        await msg.edit(f"Error: {e}")


@bot.on_message(filters.command("clone") & filters.user(ADMINS))
async def forward(bot, message):
    user_id = message.from_user.id

    existing_channels = await get_channels()
    if existing_channels:
        total_processed = sum(channel.processed_files for channel in existing_channels)
        total_pending = sum(channel.pending_files for channel in existing_channels)

        if total_pending > 0:
            pending_text = "⚠️ **Existing Clone Task Found!**\n\n"
            pending_text += "📊 **Task Status:**\n"
            pending_text += f"✅ Already processed: {total_processed:,} files\n"
            pending_text += f"⏳ Still pending: {total_pending:,} files\n\n"
            pending_text += "📋 **Channel Distribution:**\n\n"

            for channel in existing_channels:
                if channel.pending_files > 0:
                    pending_text += (
                        f"Channel {channel.channel_number} ({channel.channel_id}):\n"
                    )
                    pending_text += f"  • Processed: {channel.processed_files:,}\n"
                    pending_text += f"  • Pending: {channel.pending_files:,}\n\n"

            pending_text += "🔄 **Options:**\n"
            pending_text += "• Use `/reclone` to resume this task\n"
            pending_text += "• Use `/cleardb` to clear database and start fresh\n\n"
            pending_text += "❌ Cannot start new clone while existing task is pending!"

            await message.reply_text(pending_text, quote=True)
            return
        else:
            await clear_channels()
            LOGGER.info("Cleared completed clone task from database")

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

    total_files = await count_documents()
    files_per_channel = 980000
    total_channels_needed = (total_files + files_per_channel - 1) // files_per_channel

    await clear_channels()

    channel_data_list = []
    channel_ids = [chat.text]

    if total_channels_needed > 1:
        await message.reply_text(
            f"📊 Total files: {total_files:,}\n"
            f"📁 Files per channel: {files_per_channel:,}\n"
            f"📢 Total channels needed: {total_channels_needed}\n\n"
            f"You've provided Channel 1 ID: {chat.text}\n"
            f"Please send the remaining {total_channels_needed - 1} channel IDs one by one:",
            quote=True,
        )

        for i in range(2, total_channels_needed + 1):
            await message.reply_text(f"Send Channel {i} ID:", quote=True)
            try:
                chat_response = await bot.listen_message(
                    chat_id=user_id, filters=filters.text, timeout=300
                )
                channel_ids.append(chat_response.text)
                await message.reply_text(
                    f"✅ Channel {i} ID received: {chat_response.text}", quote=True
                )
            except TimeoutError:
                await message.reply_text(
                    "Error!!\n\nRequest timed out.\nRestart by using /clone",
                )
                return

        distribution_text = "📋 **Channel Distribution:**\n\n"
        for i, ch_id in enumerate(channel_ids, 1):
            start_file = (i - 1) * files_per_channel + 1
            end_file = min(i * files_per_channel, total_files)
            distribution_text += (
                f"Channel {i} ({ch_id}): Files {start_file:,} - {end_file:,}\n"
            )

        await message.reply_text(distribution_text, quote=True)

    for i, ch_id in enumerate(channel_ids, 1):
        pending_files = min(
            files_per_channel, total_files - (i - 1) * files_per_channel
        )
        if pending_files > 0:
            channel_data_list.append(
                {
                    "channel_id": ch_id,
                    "channel_number": i,
                    "pending_files": pending_files,
                    "processed_files": 0,
                    "status": "pending",
                }
            )

    await save_channels(channel_data_list)
    LOGGER.info(f"Saved {len(channel_data_list)} channels to database")

    await start_forwarding_process(bot, message, files_per_channel, user_id=user_id)


@bot.on_message(filters.command("reclone") & filters.user(ADMINS))
async def reclone(bot, message):
    user_id = message.from_user.id
    channels = await get_channels()
    if not channels:
        await message.reply_text(
            "❌ No saved channels found!\n\n"
            "Use /clone to start a new clone process or ensure channels are saved in database.",
            quote=True,
        )
        return

    total_files = await count_documents()
    if total_files == 0:
        await message.reply_text(
            "❌ No files found in database!\n\n"
            "Nothing to clone. Use /clone to start a new process.",
            quote=True,
        )
        return

    total_processed = sum(channel.processed_files for channel in channels)
    remaining_files = total_files - total_processed

    if remaining_files <= 0:
        await message.reply_text(
            "✅ All files have already been processed!\n\n"
            "Clone process appears to be complete. Use /clone to start a new process.",
            quote=True,
        )
        return

    resume_text = "🔄 **Resuming Clone Process**\n\n"
    resume_text += f"📊 Total files in DB: {total_files:,}\n"
    resume_text += f"✅ Already processed: {total_processed:,}\n"
    resume_text += f"⏳ Remaining files: {remaining_files:,}\n\n"
    resume_text += "📋 **Channel Status:**\n\n"

    for channel in channels:
        resume_text += f"Channel {channel.channel_number} ({channel.channel_id}):\n"
        resume_text += f"  • Processed: {channel.processed_files:,}\n"
        resume_text += f"  • Pending: {channel.pending_files:,}\n\n"

    await message.reply_text(resume_text, quote=True)

    files_per_channel = 980000

    await start_forwarding_process(
        bot,
        message,
        files_per_channel,
        resume=True,
        resume_count=total_processed,
        user_id=user_id,
    )


async def start_forwarding_process(
    bot, message, files_per_channel, resume=False, resume_count=0, user_id=None
):
    if user_id is None:
        user_id = message.from_user.id

    if 1 in status:
        await message.reply_text("A task is already running.")
        return
    if 2 in status:
        await message.reply_text("Sleeping the engine for avoiding ban.")
        return

    if resume:
        strt_fwd = await message.reply_text(
            text=f"🔄 Resuming Clone Process\nStarting from message {resume_count + 1:,}",
            quote=True,
        )
    else:
        strt_fwd = await message.reply_text(text="🚀 Started Clone Process", quote=True)

    global MessageCount
    if resume:
        MessageCount = resume_count

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
            original_caption = msg.caption
            file_type = msg.file_type
            file_name = msg.file_name
            
            caption = await get_caption(original_caption, file_name)

            current_channel_num = MessageCount // files_per_channel + 1
            current_channel = await get_channel_by_number(current_channel_num)
            if current_channel:
                try:
                    chat_id = int(current_channel.channel_id)
                except Exception as e:
                    LOGGER.error(f"Wrong channel ID: {e}")
                    await message.reply_text("❌ Wrong channel ID", quote=True)
                    return

                if MessageCount > 0 and MessageCount % files_per_channel == 0:
                    next_channel = await get_channel_by_number(current_channel_num + 1)
                    if next_channel:
                        await message.reply_text(
                            f"✅ Reached {MessageCount:,} messages!\nSwitching to Channel {next_channel.channel_number}: {next_channel.channel_id}",
                            quote=True,
                        )
            else:
                channels = await get_channels()
                if channels:
                    chat_id = int(channels[0].channel_id)
                else:
                    await message.reply_text(
                        "❌ No channels found in database!\nUse /clone to start a new process.",
                        quote=True,
                    )
                    return

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
                    else:
                        await bot.copy_message(
                            chat_id=chat_id,
                            from_chat_id=channel,
                            caption=caption,
                            message_id=message_id,
                        )
                except (
                    ChannelInvalid,
                    PeerIdInvalid,
                    ChannelPrivate,
                    UserNotParticipant,
                ) as e:
                    LOGGER.error(f"Channel access error for chat_id {chat_id}: {e}")
                    try:
                        status.remove(1)
                    except Exception:
                        pass
                    try:
                        status.remove(2)
                    except Exception:
                        pass
                    
                    current_channel_num = MessageCount // files_per_channel + 1
                    current_channel = await get_channel_by_number(current_channel_num)
                    channel_info = f"Channel {current_channel.channel_number} ({current_channel.channel_id})" if current_channel else f"Channel {chat_id}"
                    
                    error_text = "❌ **Channel Access Error!**\n\n"
                    error_text += f"🚫 Cannot access {channel_info}\n\n"
                    error_text += f"**Error: {e}**\n\n"
                    error_text += "📊 **Progress saved:**\n"
                    error_text += f"• Processed: {MessageCount:,} messages\n"
                    error_text += f"• Stopped at: {channel_info}\n\n"
                    error_text += "🔧 **To resume:**\n"
                    error_text += "1. Fix channel access issues\n"
                    error_text += "2. Use `/reclone` to continue from where stopped\n\n"
                    error_text += "⚠️ **Clone process stopped!**"
                    
                    await message.reply_text(error_text, quote=True)
                    await strt_fwd.edit(f"❌ Clone stopped due to channel access error: {channel_info}")
                    return
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
                            LOGGER.error(
                                f"Invalid file_id {file_id} after FloodWait: {e}"
                            )
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
                await asyncio.sleep(1)
                MessageCount += 1

                current_channel_num = (MessageCount - 1) // files_per_channel + 1
                current_channel = await get_channel_by_number(current_channel_num)
                if current_channel:
                    await update_channel_progress(current_channel.channel_id, 1)
                try:
                    datetime_ist = datetime.now(IST)
                    ISTIME = datetime_ist.strftime("%I:%M:%S %p - %d %B %Y")
                    if MessageCount % 100 == 0:
                        current_channel_num = MessageCount // files_per_channel + 1
                        current_channel = await get_channel_by_number(
                            current_channel_num
                        )
                        if current_channel:
                            channel_info = f"{current_channel.channel_number} ({current_channel.channel_id})"
                            pending_info = f"Pending: {current_channel.pending_files:,}"
                        else:
                            channel_info = "Unknown"
                            pending_info = "Pending: N/A"

                        await strt_fwd.edit(
                            text=f"Total Forwarded : `{MessageCount}`\nForwarded Using: Bot\nCurrent Channel: {channel_info}\n{pending_info}\nLast Forwarded at {ISTIME}"
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
                                try:
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
                                            try:
                                                await send_user_message(
                                                    message,
                                                    channel,
                                                    message_id,
                                                    file_type,
                                                    chat_id,
                                                    caption,
                                                    user_id,
                                                )
                                            except (
                                                ChannelInvalid,
                                                PeerIdInvalid,
                                                ChannelPrivate,
                                                UserNotParticipant,
                                            ) as e:
                                                raise e
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
                                except (
                                    ChannelInvalid,
                                    PeerIdInvalid,
                                    ChannelPrivate,
                                    UserNotParticipant,
                                ) as e:
                                    LOGGER.error(f"Channel access error for chat_id {chat_id}: {e}")
                                    try:
                                        status.remove(1)
                                    except Exception:
                                        pass
                                    try:
                                        status.remove(2)
                                    except Exception:
                                        pass
                                    
                                    current_channel_num = MessageCount // files_per_channel + 1
                                    current_channel = await get_channel_by_number(current_channel_num)
                                    channel_info = f"Channel {current_channel.channel_number} ({current_channel.channel_id})" if current_channel else f"Channel {chat_id}"
                                    
                                    error_text = "❌ **Channel Access Error!**\n\n"
                                    error_text += f"🚫 Cannot access {channel_info}\n\n"
                                    error_text += f"**Error: {e}**\n\n"
                                    error_text += "📊 **Progress saved:**\n"
                                    error_text += f"• Processed: {MessageCount:,} messages\n"
                                    error_text += f"• Stopped at: {channel_info}\n\n"
                                    error_text += "🔧 **To resume:**\n"
                                    error_text += "1. Fix channel access issues\n"
                                    error_text += "2. Use `/reclone` to continue from where stopped\n\n"
                                    error_text += "⚠️ **Clone process stopped!**"
                                    
                                    await message.reply_text(error_text, quote=True)
                                    await strt_fwd.edit(f"❌ Clone stopped due to channel access error: {channel_info}")
                                    return
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

                                current_channel_num = (
                                    MessageCount - 1
                                ) // files_per_channel + 1
                                current_channel = await get_channel_by_number(
                                    current_channel_num
                                )
                                if current_channel:
                                    await update_channel_progress(
                                        current_channel.channel_id, 1
                                    )
                                mainsleep = random.randint(3, 8)
                                try:
                                    datetime_ist = datetime.now(IST)
                                    ISTIME = datetime_ist.strftime(
                                        "%I:%M:%S %p - %d %B %Y"
                                    )
                                    if MessageCount % 100 == 0:
                                        current_channel_num = (
                                            MessageCount // files_per_channel + 1
                                        )
                                        current_channel = await get_channel_by_number(
                                            current_channel_num
                                        )
                                        if current_channel:
                                            channel_info = f"{current_channel.channel_number} ({current_channel.channel_id})"
                                            pending_info = f"Pending: {current_channel.pending_files:,}"
                                        else:
                                            channel_info = "Unknown"
                                            pending_info = "Pending: N/A"

                                        await strt_fwd.edit(
                                            text=f"Total Forwarded : `{MessageCount}`\nForwarded Using: User\nCurrent Channel: {channel_info}\n{pending_info}\nSleeping for `{mainsleep}` Seconds\nLast Forwarded at `{ISTIME}`"
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

        channels = await get_channels()
        if len(channels) > 1:
            distribution_text = f"✅ Successfully Forwarded {MessageCount:,} messages\n\n📊 **Final Distribution:**\n\n"

            for channel in channels:
                if channel.processed_files > 0:
                    distribution_text += f"Channel {channel.channel_number} ({channel.channel_id}): {channel.processed_files:,} messages\n"

            await strt_fwd.edit(text=distribution_text)
        else:
            await strt_fwd.edit(
                text=f"✅ Successfully Forwarded {MessageCount:,} messages"
            )
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

    await clear_channels()
    LOGGER.info("Cleared channels from database after clone completion")

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
        except (
            ChannelInvalid,
            PeerIdInvalid,
            ChannelPrivate,
            UserNotParticipant,
        ) as e:
            LOGGER.error(f"Channel access error in send_user_message for chat_id {chat_id}: {e}")
            raise e
        except Exception as e:
            LOGGER.error(e)
            await message.reply_text(f"Error:\n{e}")
    except (
        ChannelInvalid,
        PeerIdInvalid,
        ChannelPrivate,
        UserNotParticipant,
    ):
        raise
    except Exception as e:
        LOGGER.error(e)
        await message.reply_text(f"Error:\n{e}")
