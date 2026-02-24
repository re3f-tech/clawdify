#!/usr/bin/env python3
"""
Clabo Hotel Bot — "claude" — AI-powered chat bot.
Connects via WebSocket as a real player, listens to room chat,
responds with AI (OpenRouter), does keyword commands, greets new
users, and patrols the room with ambient behavior.
"""

import asyncio
import json
import os
import random
import struct
import subprocess
import sys
import time

import aiohttp
import websockets

# ── Config ────────────────────────────────────────────────────────────
WS_URL = "ws://127.0.0.1:2096"
ROOM_ID = 208
BOT_USER_ID = 8
BOT_USERNAME = "claude"
LOCK_FILE = "/tmp/clabo-bot-claude.lock"

OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

DB_USER = os.environ.get("MYSQL_USER", "arcturus_user")
DB_PASS = os.environ.get("MYSQL_PASSWORD", "arcturus_pw")
DB_NAME = os.environ.get("MYSQL_DATABASE", "arcturus")

# ── Outgoing packet headers ──────────────────────────────────────────
SECURITY_TICKET = 2419
SECURITY_MACHINE = 2490
CLIENT_VARIABLES = 1053
GET_GUEST_ROOM = 2230
OPEN_FLAT_CONNECTION = 2312
GET_ROOM_ENTRY_DATA = 3898
OUT_CHAT = 1314
OUT_SHOUT = 2085
OUT_WHISPER = 1543
MOVE_AVATAR = 3320
DANCE = 2080
EXPRESSION = 2456    # 1=wave 2=blow_kiss 3=laugh 5=jump_happy
SIGN = 1975
CLIENT_PONG = 2596

# ── Incoming packet headers ──────────────────────────────────────────
SERVER_PING = 3928
IN_AUTHENTICATED = 2491
IN_CHAT = 1446
IN_SHOUT = 1036
IN_WHISPER = 1132
IN_ROOM_USERS = 374
IN_USER_REMOVE = 2661
IN_USER_UPDATE = 1640

# ── AI persona ───────────────────────────────────────────────────────
SYSTEM_PROMPT = (
    "You are Claude, a professional personal assistant working at the "
    "front desk of Clabo Hotel (a Habbo-style virtual hotel). You're "
    "polite, warm, and helpful — like a great hotel concierge. Keep "
    "responses SHORT (1-2 sentences, under 80 characters ideally). "
    "Use proper grammar but stay approachable and friendly. You help "
    "guests with questions, welcome them warmly, and make them feel "
    "at home. If asked what you are, you're the hotel's front desk "
    "assistant. Never be rude. If someone is difficult, stay composed "
    "and professional."
)

# ── Keyword data ─────────────────────────────────────────────────────
GREETING_WORDS = {
    "hi", "hey", "hello", "sup", "yo", "hii", "heyy", "heya",
    "hiya", "hewwo", "ello", "hai",
}
GREETING_RESPONSES = [
    "Welcome!", "Hello there!", "Hi! Nice to see you!", "Hey, welcome!",
    "Good to see you!", "Hello! How can I help?",
]
FOLLOW_KEYWORDS = ["follow me", "come here", "follow"]
IDLE_LINES = [
    "Let me know if you need anything!", "Welcome to Clabo Hotel.",
    "Feel free to look around!", "I'm here if you need help.",
    "Hope everyone's having a great time!",
    "The hotel is looking lovely today.",
    "Don't hesitate to ask if you need something.",
]
PATROL_WAYPOINTS = [
    (16, 19), (13, 15), (10, 12), (14, 18), (11, 16), (15, 14), (12, 20),
]


# ── Wire helpers ─────────────────────────────────────────────────────
class PayloadReader:
    """Read Habbo wire-format fields from a binary payload."""

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def read_int(self) -> int:
        if self.pos + 4 > len(self.data):
            raise ValueError("EOF reading int")
        val = struct.unpack(">i", self.data[self.pos:self.pos + 4])[0]
        self.pos += 4
        return val

    def read_short(self) -> int:
        if self.pos + 2 > len(self.data):
            raise ValueError("EOF reading short")
        val = struct.unpack(">H", self.data[self.pos:self.pos + 2])[0]
        self.pos += 2
        return val

    def read_string(self) -> str:
        length = self.read_short()
        if self.pos + length > len(self.data):
            raise ValueError("EOF reading string")
        val = self.data[self.pos:self.pos + length].decode("utf-8", errors="replace")
        self.pos += length
        return val

    def read_bool(self) -> bool:
        if self.pos + 1 > len(self.data):
            raise ValueError("EOF reading bool")
        val = self.data[self.pos] != 0
        self.pos += 1
        return val

    def remaining(self) -> int:
        return len(self.data) - self.pos


def build_packet(header_id: int, payload: bytes = b"") -> bytes:
    length = 2 + len(payload)
    return struct.pack(">IH", length, header_id) + payload


def encode_string(s: str) -> bytes:
    b = s.encode("utf-8")
    return struct.pack(">H", len(b)) + b


def encode_int(n: int) -> bytes:
    return struct.pack(">i", n)


def parse_packets(data: bytes):
    packets = []
    o = 0
    while o + 6 <= len(data):
        length = struct.unpack(">I", data[o:o + 4])[0]
        if o + 4 + length > len(data):
            break
        hid = struct.unpack(">H", data[o + 4:o + 6])[0]
        payload = data[o + 6:o + 4 + length]
        packets.append((hid, payload))
        o += 4 + length
    return packets


# ── Packet parsers ───────────────────────────────────────────────────
def parse_room_users(payload: bytes, room_users: dict):
    """Parse ROOM_USERS (374) packet → update room_users dict.
    Returns list of (room_unit_id, username) for newly parsed users."""
    parsed = []
    try:
        r = PayloadReader(payload)
        count = r.read_int()
        for _ in range(count):
            user_id = r.read_int()
            username = r.read_string()
            motto = r.read_string()
            figure = r.read_string()
            room_unit_id = r.read_int()
            x = r.read_int()
            y = r.read_int()
            z = r.read_string()      # height "0.0"
            body_dir = r.read_int()
            head_dir = r.read_int()
            user_type = r.read_string()  # "legacy" / "bot" / "pet"

            room_users[room_unit_id] = {
                "username": username,
                "user_id": user_id,
                "x": x,
                "y": y,
            }
            parsed.append((room_unit_id, username))

            # Skip type-specific trailing fields
            try:
                if user_type == "legacy":
                    r.read_string()  # gender
                    r.read_int()     # groupId
                    r.read_int()     # groupStatus
                    r.read_string()  # groupName
                    r.read_string()  # swimFigure
                    r.read_int()     # achievementScore
                    r.read_bool()    # isModerator
                elif user_type == "bot":
                    r.read_string()  # ownerName
                    r.read_int()     # ownerId
                    # some implementations add extra bot fields
                    # we'll be tolerant of parse errors here
            except ValueError:
                break  # couldn't read trailing fields, stop
    except Exception as e:
        print(f"[!] ROOM_USERS parse (got {len(parsed)}): {e}", flush=True)
    return parsed


def parse_user_update(payload: bytes, room_users: dict):
    """Parse USER_UPDATE (1640) to track positions."""
    try:
        r = PayloadReader(payload)
        count = r.read_int()
        for _ in range(count):
            room_unit_id = r.read_int()
            x = r.read_int()
            y = r.read_int()
            z = r.read_string()
            head_dir = r.read_int()
            body_dir = r.read_int()
            status_str = r.read_string()
            if room_unit_id in room_users:
                room_users[room_unit_id]["x"] = x
                room_users[room_unit_id]["y"] = y
    except Exception:
        pass  # best-effort


def parse_chat(payload: bytes):
    """Parse CHAT_MESSAGE / SHOUT_MESSAGE → (roomUnitId, message)."""
    r = PayloadReader(payload)
    sender_ruid = r.read_int()
    message = r.read_string()
    return sender_ruid, message


# ── AI ───────────────────────────────────────────────────────────────
def chunk_message(text: str, max_len: int = 100) -> list[str]:
    """Split text into word-boundary chunks for Habbo's chat limit."""
    words = text.split()
    chunks = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > max_len:
            chunks.append(current)
            current = word
        else:
            current = (current + " " + word) if current else word
    if current:
        chunks.append(current)
    return chunks if chunks else [text[:max_len]]


async def ai_respond(username: str, message: str, history: list, session):
    """Call OpenRouter for an AI response."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for role, content in history:
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": f"{username}: {message}"})

    try:
        async with session.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": messages,
                "max_tokens": 150,
                "temperature": 0.8,
            },
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                body = await resp.text()
                print(f"[!] OpenRouter {resp.status}: {body[:200]}", flush=True)
                return None
    except Exception as e:
        print(f"[!] AI error: {e}", flush=True)
        return None


# ── Main bot ─────────────────────────────────────────────────────────
async def run_bot():
    # Shared state
    own_room_unit_id = None
    room_users = {}                # roomUnitId → {username, user_id, x, y}
    user_histories = {}            # username → [(role, content), ...] max 6
    chat_queue = asyncio.Queue()
    ws_lock = asyncio.Lock()
    room_loaded = False
    responding = asyncio.Event()
    responding.set()               # set = bot is free (not busy)

    # ── Auth ──────────────────────────────────────────────────────────
    sso_ticket = f"ClaboBot-claude-{int(time.time())}"
    subprocess.run(
        ["docker", "exec", "clabo-hotel-db-1", "mysql", "-u", DB_USER,
         f"-p{DB_PASS}", DB_NAME, "-N", "-e",
         f"UPDATE users SET auth_ticket='{sso_ticket}' WHERE id={BOT_USER_ID};"],
        capture_output=True,
    )
    print(f"[*] SSO: {sso_ticket}", flush=True)

    ws = await asyncio.wait_for(
        websockets.connect(WS_URL, origin="https://localhost"), timeout=5,
    )
    print("[+] Connected!", flush=True)

    # Send handshake
    await ws.send(build_packet(SECURITY_MACHINE, encode_string("")))
    await ws.send(build_packet(CLIENT_VARIABLES,
                               encode_int(0) + encode_string("0") + encode_string("")))
    await ws.send(build_packet(SECURITY_TICKET, encode_string(sso_ticket)))
    await asyncio.sleep(2)

    # Drain auth response
    auth_ok = False
    try:
        while True:
            msg = await asyncio.wait_for(ws.recv(), timeout=3)
            if isinstance(msg, bytes):
                for hid, _ in parse_packets(msg):
                    if hid == IN_AUTHENTICATED:
                        auth_ok = True
                    if hid == SERVER_PING:
                        await ws.send(build_packet(CLIENT_PONG))
    except asyncio.TimeoutError:
        pass

    if not auth_ok:
        print("[!] Auth failed!", flush=True)
        await ws.close()
        return
    print("[+] Authenticated!", flush=True)

    # ── Enter room ────────────────────────────────────────────────────
    await ws.send(build_packet(GET_GUEST_ROOM,
                               encode_int(ROOM_ID) + encode_int(0) + encode_int(1)))
    await asyncio.sleep(1)

    # Drain
    try:
        while True:
            msg = await asyncio.wait_for(ws.recv(), timeout=2)
            if isinstance(msg, bytes):
                for hid, _ in parse_packets(msg):
                    if hid == SERVER_PING:
                        await ws.send(build_packet(CLIENT_PONG))
    except asyncio.TimeoutError:
        pass

    await ws.send(build_packet(OPEN_FLAT_CONNECTION,
                               encode_int(ROOM_ID) + encode_string("")))
    await asyncio.sleep(1)

    # Drain — parse room users
    try:
        while True:
            msg = await asyncio.wait_for(ws.recv(), timeout=3)
            if isinstance(msg, bytes):
                for hid, payload in parse_packets(msg):
                    if hid == SERVER_PING:
                        await ws.send(build_packet(CLIENT_PONG))
                    if hid == IN_ROOM_USERS:
                        parse_room_users(payload, room_users)
                        for ruid, info in room_users.items():
                            if info["username"].lower() == BOT_USERNAME:
                                own_room_unit_id = ruid
    except asyncio.TimeoutError:
        pass

    await ws.send(build_packet(GET_ROOM_ENTRY_DATA))
    await asyncio.sleep(2)

    # Drain more
    try:
        while True:
            msg = await asyncio.wait_for(ws.recv(), timeout=3)
            if isinstance(msg, bytes):
                for hid, payload in parse_packets(msg):
                    if hid == SERVER_PING:
                        await ws.send(build_packet(CLIENT_PONG))
                    if hid == IN_ROOM_USERS:
                        parse_room_users(payload, room_users)
                        for ruid, info in room_users.items():
                            if info["username"].lower() == BOT_USERNAME:
                                own_room_unit_id = ruid
    except asyncio.TimeoutError:
        pass

    print(f"[+] In room {ROOM_ID}! (roomUnitId={own_room_unit_id})", flush=True)
    print(f"[*] Users: {[u['username'] for u in room_users.values()]}", flush=True)

    # Let initial user list settle before greeting arrivals
    await asyncio.sleep(2)
    room_loaded = True

    # Announce
    async with ws_lock:
        await ws.send(build_packet(OUT_CHAT,
                                   encode_string("Good day! Front desk is open.") + encode_int(0) + encode_int(-1)))
    print('[>] "heyyy, just got here"', flush=True)

    # ── Listener task ─────────────────────────────────────────────────
    async def listener_task():
        nonlocal own_room_unit_id, room_loaded
        while True:
            try:
                msg = await ws.recv()
                if not isinstance(msg, bytes):
                    continue
                for hid, payload in parse_packets(msg):
                    # Ping
                    if hid == SERVER_PING:
                        async with ws_lock:
                            await ws.send(build_packet(CLIENT_PONG))
                        continue

                    # Room users (arrivals / initial)
                    if hid == IN_ROOM_USERS:
                        old_ruids = set(room_users.keys())
                        newly_parsed = parse_room_users(payload, room_users)
                        # Grab own roomUnitId
                        for ruid, uname in newly_parsed:
                            if uname.lower() == BOT_USERNAME:
                                own_room_unit_id = ruid
                        # Greet new arrivals (after room is loaded)
                        if room_loaded:
                            for ruid, uname in newly_parsed:
                                if ruid not in old_ruids and uname.lower() != BOT_USERNAME:
                                    print(f"[>] {uname} entered!", flush=True)
                                    await chat_queue.put(("new_user", ruid, uname, ""))
                        continue

                    # User left
                    if hid == IN_USER_REMOVE:
                        try:
                            r = PayloadReader(payload)
                            ruid_str = r.read_string()
                            ruid = int(ruid_str)
                            removed = room_users.pop(ruid, None)
                            if removed:
                                print(f"[<] {removed['username']} left", flush=True)
                        except Exception:
                            pass
                        continue

                    # Position updates
                    if hid == IN_USER_UPDATE:
                        parse_user_update(payload, room_users)
                        continue

                    # Chat / Shout / Whisper
                    if hid in (IN_CHAT, IN_SHOUT, IN_WHISPER):
                        try:
                            sender_ruid, message = parse_chat(payload)
                            # Skip our own messages
                            if sender_ruid == own_room_unit_id:
                                continue
                            sender_info = room_users.get(sender_ruid, {})
                            sender_name = sender_info.get("username", f"User#{sender_ruid}")
                            kind = "whisper" if hid == IN_WHISPER else "chat"
                            tag = "[whisper]" if kind == "whisper" else "[chat]"
                            print(f"  {tag} {sender_name}: {message}", flush=True)
                            await chat_queue.put((kind, sender_ruid, sender_name, message))
                        except Exception as e:
                            print(f"[!] Chat parse err: {e}", flush=True)
                        continue

            except websockets.exceptions.ConnectionClosed:
                print("[!] Connection closed (listener).", flush=True)
                break
            except Exception as e:
                print(f"[!] Listener err: {e}", flush=True)
                await asyncio.sleep(1)

    # ── Chat handler task ─────────────────────────────────────────────
    async def chat_handler_task():
        async with aiohttp.ClientSession() as http:
            while True:
                event_type, sender_ruid, sender_name, message = await chat_queue.get()
                responding.clear()  # busy
                try:
                    # ── New user greeting ──
                    if event_type == "new_user":
                        await asyncio.sleep(1.5)
                        greeting = random.choice(GREETING_RESPONSES)
                        async with ws_lock:
                            await ws.send(build_packet(EXPRESSION, encode_int(1)))  # wave
                            await ws.send(build_packet(
                                OUT_CHAT,
                                encode_string(f"Welcome to Clabo Hotel, {sender_name}!")
                                + encode_int(0) + encode_int(-1)))
                        print(f"[>] Greeted {sender_name}", flush=True)
                        continue

                    msg_lower = message.lower().strip()

                    # ── Keyword: dance ──
                    if "dance" in msg_lower:
                        style = random.randint(1, 4)
                        async with ws_lock:
                            await ws.send(build_packet(DANCE, encode_int(style)))
                            await ws.send(build_packet(
                                OUT_CHAT,
                                encode_string("Sure, I love a good dance!")
                                + encode_int(0) + encode_int(-1)))
                        print(f"[>] Dancing (style {style})", flush=True)
                        await asyncio.sleep(8)
                        async with ws_lock:
                            await ws.send(build_packet(DANCE, encode_int(0)))
                        continue

                    # ── Keyword: wave ──
                    if msg_lower in ("wave", "wave!"):
                        async with ws_lock:
                            await ws.send(build_packet(EXPRESSION, encode_int(1)))
                        print("[>] *waves*", flush=True)
                        continue

                    # ── Keyword: follow me ──
                    if any(kw in msg_lower for kw in FOLLOW_KEYWORDS):
                        sender_info = room_users.get(sender_ruid)
                        if sender_info:
                            tx, ty = sender_info.get("x", 10), sender_info.get("y", 10)
                            async with ws_lock:
                                await ws.send(build_packet(MOVE_AVATAR,
                                                           encode_int(tx) + encode_int(ty)))
                                await ws.send(build_packet(
                                    OUT_CHAT,
                                    encode_string("Right behind you!")
                                    + encode_int(0) + encode_int(-1)))
                            print(f"[>] Following {sender_name} → ({tx},{ty})", flush=True)
                        continue

                    # ── Keyword: greetings (hi/hey/hello…) ──
                    words = set(
                        msg_lower.replace("!", "").replace("?", "")
                        .replace(",", " ").replace(".", " ").split()
                    )
                    if words & GREETING_WORDS and (
                        "claude" in msg_lower or len(words) <= 3
                    ):
                        greeting = random.choice(GREETING_RESPONSES)
                        async with ws_lock:
                            await ws.send(build_packet(EXPRESSION, encode_int(1)))
                            await ws.send(build_packet(
                                OUT_CHAT,
                                encode_string(f"{greeting} {sender_name}!")
                                + encode_int(0) + encode_int(-1)))
                        print(f"[>] Greeting → {sender_name}", flush=True)
                        continue

                    # ── Check if message is directed at claude ──
                    is_directed = (
                        "claude" in msg_lower
                        or event_type == "whisper"
                        or msg_lower.startswith("@claude")
                    )
                    if not is_directed:
                        continue

                    # ── AI response via OpenRouter ──
                    history = user_histories.get(sender_name, [])
                    reply = await ai_respond(sender_name, message, history, http)
                    if reply:
                        history.append(("user", f"{sender_name}: {message}"))
                        history.append(("assistant", reply))
                        user_histories[sender_name] = history[-6:]

                        chunks = chunk_message(reply)
                        for chunk in chunks:
                            async with ws_lock:
                                await ws.send(build_packet(
                                    OUT_CHAT,
                                    encode_string(chunk)
                                    + encode_int(0) + encode_int(-1)))
                            print(f"[>] {chunk}", flush=True)
                            if len(chunks) > 1:
                                await asyncio.sleep(1.5)
                    else:
                        # Fallback if AI fails
                        async with ws_lock:
                            await ws.send(build_packet(
                                OUT_CHAT,
                                encode_string("hmm idk lol")
                                + encode_int(0) + encode_int(-1)))

                except Exception as e:
                    print(f"[!] Chat handler err: {e}", flush=True)
                finally:
                    responding.set()  # free

    # ── Ambient behavior task ─────────────────────────────────────────
    async def ambient_task():
        await asyncio.sleep(15)  # let the bot settle in first
        wp_idx = 0
        dancing = False
        while True:
            try:
                # Pause while responding to chat
                await responding.wait()

                roll = random.random()

                if roll < 0.12:
                    # Dance
                    style = random.randint(1, 4)
                    async with ws_lock:
                        await ws.send(build_packet(DANCE, encode_int(style)))
                    dancing = True
                    print(f"[~] Ambient dance (style {style})", flush=True)
                    await asyncio.sleep(random.uniform(6, 12))
                    async with ws_lock:
                        await ws.send(build_packet(DANCE, encode_int(0)))
                    dancing = False

                elif roll < 0.20:
                    # Wave
                    async with ws_lock:
                        await ws.send(build_packet(EXPRESSION, encode_int(1)))
                    print("[~] Ambient wave", flush=True)
                    await asyncio.sleep(3)

                elif roll < 0.28:
                    # Say something casual
                    line = random.choice(IDLE_LINES)
                    async with ws_lock:
                        await ws.send(build_packet(
                            OUT_CHAT,
                            encode_string(line) + encode_int(0) + encode_int(-1)))
                    print(f'[~] "{line}"', flush=True)
                    await asyncio.sleep(5)

                else:
                    # Patrol to next waypoint
                    if dancing:
                        async with ws_lock:
                            await ws.send(build_packet(DANCE, encode_int(0)))
                        dancing = False
                    x, y = PATROL_WAYPOINTS[wp_idx % len(PATROL_WAYPOINTS)]
                    async with ws_lock:
                        await ws.send(build_packet(MOVE_AVATAR,
                                                   encode_int(x) + encode_int(y)))
                    wp_idx += 1
                    print(f"[~] Patrol → ({x},{y})", flush=True)

                await asyncio.sleep(random.uniform(10, 25))

            except websockets.exceptions.ConnectionClosed:
                break
            except Exception as e:
                print(f"[!] Ambient err: {e}", flush=True)
                await asyncio.sleep(5)

    # ── Run all three tasks concurrently ──────────────────────────────
    try:
        await asyncio.gather(
            listener_task(),
            chat_handler_task(),
            ambient_task(),
        )
    except websockets.exceptions.ConnectionClosed:
        print("[!] Connection closed.", flush=True)
    finally:
        await ws.close()
        print("[*] Disconnected.", flush=True)


# ── Entry point ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import fcntl

    fp = open(LOCK_FILE, "w")
    try:
        fcntl.flock(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fp.write(str(os.getpid()))
        fp.flush()
    except BlockingIOError:
        print("[!] Bot is already running.")
        sys.exit(1)

    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n[*] Bot stopped.")
    except Exception as e:
        print(f"[!] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        fp.close()
        try:
            os.unlink(LOCK_FILE)
        except OSError:
            pass
