#!/usr/bin/env python3
import asyncio
import logging
import random
from telethon import TelegramClient, events
from telethon.tl.functions.messages import SendReactionRequest
from telethon.tl.types import ReactionEmoji

# Setup logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# ------------ ACCOUNT DETAILS ------------
accounts = [
    {
        "session": "termux_session",
        "api_id": 23978958,
        "api_hash": "43cbf43c413af11c24f2b9870e266090",
        "phone": "+998200065670"
    }
# -----------------------------------------

# Delays
FIRST_DELAY = 60   # Level 1 (seconds)
SECOND_DELAY = 30  # Level 2
THIRD_DELAY = 15   # Level 3

# Level 1 fixed text
first_reply_text = (
    "Salom alaykum 👋\n"
    "Mani guruhchamga qo'shlib qoin\n"
    "Olov reaksiya bosib turardiz 🔥\n"
    "Keyin gaplashamiz🩵🩵🩵\n"
    "t.me/+vDKa1KtT_XE5N2Qy"
)

# Level 2 random replies (choose 1)
second_replies = [
    "Ismiz nima?",
    "Qayerliksiz",
    "Nechanchi yilsiz",
    "Nima qilyabsiz",
    "Nima Gap",
    "Kimsiz",
    "Tanimadim",
    "Yaxshimisiz",
    "Zo'rmisiz"
]

# Level 3 random replies (choose 1)
third_replies = [
    "Qo'shildizmi?",
    "Qo'shildizmi? qabul qilib qo'yaman",
    "Grga qoshilmadizmi sizni topolmadim",
    "Grga qo'shildizmi? oxirgi postga Yurakcha bosib bering",
    "Voxtiz bormi? Guruhimdagi Oxirgi postga Yurakcha bosib bering"
]

# Track states per client: levels[client] -> { chat_id: {"level": int, "pending": None|int, "lock": asyncio.Lock()} }
levels = {}

# ---------- sending functions ----------
async def send_level_1(client: TelegramClient, chat_id, entity):
    state = levels[client].get(chat_id)
    try:
        await asyncio.sleep(FIRST_DELAY)
        sent_msg = await client.send_message(entity, first_reply_text)
        logger.info(f"[{client.session.filename}] Sent level 1 reply to {chat_id}")

        # ❤️ reaction only for level 1
        try:
            await client(SendReactionRequest(
                peer=entity,
                msg_id=sent_msg.id,
                reaction=[ReactionEmoji(emoticon="❤️")]
            ))
        except Exception as e:
            logger.warning(f"[{client.session.filename}] Failed ❤️ reaction: {e}")

        await client.send_read_acknowledge(entity)

        # mark level completed
        if state:
            async with state["lock"]:
                state["level"] = 1
                state["pending"] = None
    except Exception as e:
        logger.exception(f"[{client.session.filename}] Error sending level 1 to {chat_id}: {e}")
        if state:
            async with state["lock"]:
                state["pending"] = None


async def send_level_2(client: TelegramClient, chat_id, entity):
    state = levels[client].get(chat_id)
    try:
        await asyncio.sleep(SECOND_DELAY)
        text = random.choice(second_replies)
        await client.send_message(entity, text)
        logger.info(f"[{client.session.filename}] Sent level 2 reply to {chat_id}")
        await client.send_read_acknowledge(entity)

        # mark level completed
        if state:
            async with state["lock"]:
                state["level"] = 2
                state["pending"] = None
    except Exception as e:
        logger.exception(f"[{client.session.filename}] Error sending level 2 to {chat_id}: {e}")
        if state:
            async with state["lock"]:
                state["pending"] = None


async def send_level_3(client: TelegramClient, chat_id, entity):
    state = levels[client].get(chat_id)
    try:
        await asyncio.sleep(THIRD_DELAY)
        text = random.choice(third_replies)
        await client.send_message(entity, text)
        logger.info(f"[{client.session.filename}] Sent level 3 reply to {chat_id}")
        await client.send_read_acknowledge(entity)

        # mark level completed
        if state:
            async with state["lock"]:
                state["level"] = 3
                state["pending"] = None
    except Exception as e:
        logger.exception(f"[{client.session.filename}] Error sending level 3 to {chat_id}: {e}")
        if state:
            async with state["lock"]:
                state["pending"] = None


# ---------- handlers registration ----------
def register_handlers(client: TelegramClient):
    # initialize client entry
    levels[client] = {}

    @client.on(events.NewMessage(incoming=True))
    async def new_message_handler(event):
        # ignore non-private or outgoing
        if not event.is_private or event.out:
            return

        chat_id = event.chat_id
        entity = await event.get_sender()

        # ensure state exists
        state = levels[client].get(chat_id)
        if state is None:
            # create state for this chat
            state = {"level": 0, "pending": None, "lock": asyncio.Lock()}
            levels[client][chat_id] = state

        # operate under lock to avoid races
        async with state["lock"]:
            # if finished all levels -> do nothing
            if state["level"] >= 3:
                return

            # if already waiting to send a reply for this chat -> do nothing
            if state["pending"] is not None:
                # user sending more messages during wait should NOT schedule next level
                return

            # schedule appropriate level depending on completed level
            if state["level"] == 0:
                state["pending"] = 1
                asyncio.create_task(send_level_1(client, chat_id, entity))
                logger.debug(f"[{client.session.filename}] Scheduled level 1 for {chat_id}")
                return

            if state["level"] == 1:
                state["pending"] = 2
                asyncio.create_task(send_level_2(client, chat_id, entity))
                logger.debug(f"[{client.session.filename}] Scheduled level 2 for {chat_id}")
                return

            if state["level"] == 2:
                state["pending"] = 3
                asyncio.create_task(send_level_3(client, chat_id, entity))
                logger.debug(f"[{client.session.filename}] Scheduled level 3 for {chat_id}")
                return


# ---------- Main ----------
async def main():
    clients = []
    for acc in accounts:
        client = TelegramClient(acc["session"], acc["api_id"], acc["api_hash"])
        register_handlers(client)
        await client.start(phone=acc.get("phone"))
        logger.info(f"✅ Logged in as {acc.get('phone')} ({client.session.filename})")
        clients.append(client)

    # keep all clients running
    await asyncio.gather(*(client.run_until_disconnected() for client in clients))


if __name__ == "__main__":
    asyncio.run(main())
