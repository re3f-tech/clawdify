#!/usr/bin/env python3
"""
Clabo Hotel Bot — "joejoegopro" is the nightclub bartender/hype man.
Patrols the bar, checks the DJ booth, waves at people, shouts hype lines.
"""

import asyncio
import random
import struct
import subprocess
import sys
import websockets

# Config
WS_URL = "ws://127.0.0.1:2096"
ROOM_ID = 206
USER_ID = 4  # joejoegopro

# Arcturus server header IDs
SECURITY_TICKET = 2419
SECURITY_MACHINE = 2490
CLIENT_VARIABLES = 1053
GET_GUEST_ROOM = 2230
OPEN_FLAT_CONNECTION = 2312
GET_ROOM_ENTRY_DATA = 3898
CHAT = 1314
SHOUT = 2085
MOVE_AVATAR = 3320
DANCE = 2080
SIGN = 1975          # payload: int (sign number 0-17)
EXPRESSION = 2456    # payload: int (1=wave, 2=blow_kiss, 3=laugh, 4=idle, 5=jump_happy, 6=rps)
CLIENT_PONG = 2596

# Incoming
SERVER_PING = 3928
AUTHENTICATED = 2491

# Bartender route and behavior
HYPE_LINES = [
    "welcome to CLABO NIGHTCLUB!",
    "drinks on the house tonight!",
    "DJ drop that beat!",
    "this is the best club in clabo!",
    "who wants a drink?",
    "vip section is open!",
    "the party dont stop!",
    "ayyyy lets gooo!",
]

# Route: bar area → DJ booth → fountain → bar, with actions at each stop
ROUTE = [
    # Bar area — serve drinks
    {"pos": (9, 21), "msg": None, "action": "walk", "pause": 3},
    {"pos": (9, 22), "msg": None, "action": "wave", "pause": 4},
    {"pos": (10, 21), "msg": "hype", "action": "walk", "pause": 3},
    {"pos": (8, 22), "msg": None, "action": "walk", "pause": 2},
    # Walk past the tubes to DJ booth
    {"pos": (8, 14), "msg": None, "action": "walk", "pause": 3},
    {"pos": (10, 8), "msg": None, "action": "walk", "pause": 3},
    # DJ booth area — hype it up
    {"pos": (11, 4), "msg": None, "action": "walk", "pause": 3},
    {"pos": (11, 3), "msg": "hype", "action": "dance", "pause": 8},
    # Dance floor — party with the crowd
    {"pos": (10, 9), "msg": None, "action": "dance", "pause": 6},
    {"pos": (9, 8), "msg": None, "action": "walk", "pause": 2},
    {"pos": (12, 9), "msg": "hype", "action": "sign", "pause": 5},
    # Walk to fountain
    {"pos": (10, 14), "msg": None, "action": "walk", "pause": 3},
    {"pos": (10, 17), "msg": None, "action": "wave", "pause": 5},
    # Head to jukebox
    {"pos": (13, 19), "msg": None, "action": "walk", "pause": 3},
    {"pos": (13, 21), "msg": None, "action": "wave", "pause": 4},
    # Back to bar
    {"pos": (10, 22), "msg": "hype", "action": "walk", "pause": 3},
]


def build_packet(header_id, payload=b""):
    length = 2 + len(payload)
    return struct.pack(">IH", length, header_id) + payload


def encode_string(s):
    b = s.encode("utf-8")
    return struct.pack(">H", len(b)) + b


def encode_int(n):
    return struct.pack(">i", n)


def parse_packets(data):
    packets = []
    o = 0
    while o + 6 <= len(data):
        length = struct.unpack(">I", data[o:o+4])[0]
        if o + 4 + length > len(data):
            break
        hid = struct.unpack(">H", data[o+4:o+6])[0]
        payload = data[o+6:o+4+length]
        packets.append((hid, payload))
        o += 4 + length
    return packets


async def idle_drain(ws, seconds):
    end = asyncio.get_event_loop().time() + seconds
    while asyncio.get_event_loop().time() < end:
        remaining = end - asyncio.get_event_loop().time()
        if remaining <= 0:
            break
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=min(remaining, 5))
            if isinstance(msg, bytes):
                for hid, _ in parse_packets(msg):
                    if hid == SERVER_PING:
                        await ws.send(build_packet(CLIENT_PONG))
        except asyncio.TimeoutError:
            pass


async def drain(ws, timeout=2):
    all_packets = []
    while True:
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
            if isinstance(msg, bytes):
                for hid, payload in parse_packets(msg):
                    all_packets.append((hid, payload))
                    if hid == SERVER_PING:
                        await ws.send(build_packet(CLIENT_PONG))
        except asyncio.TimeoutError:
            break
    return all_packets


async def run_bot():
    # Get fresh SSO ticket
    result = subprocess.run(
        ["docker", "exec", "clabo-hotel-db-1", "mysql", "-u", "arcturus_user",
         "-parcturus_pw", "arcturus", "-N", "-e",
         f"SELECT auth_ticket FROM users WHERE id={USER_ID};"],
        capture_output=True, text=True
    )
    sso_ticket = result.stdout.strip()
    print(f"[*] SSO: {sso_ticket}", flush=True)

    ws = await asyncio.wait_for(
        websockets.connect(WS_URL, origin="https://localhost"), timeout=5
    )
    print("[+] Connected!", flush=True)

    try:
        # Auth
        await ws.send(build_packet(SECURITY_MACHINE, encode_string("")))
        await ws.send(build_packet(CLIENT_VARIABLES, encode_int(0) + encode_string("0") + encode_string("")))
        await ws.send(build_packet(SECURITY_TICKET, encode_string(sso_ticket)))
        await asyncio.sleep(2)
        packets = await drain(ws, timeout=2)
        if not any(h == AUTHENTICATED for h, _ in packets):
            print("[!] Auth failed!", flush=True)
            return
        print("[+] Authenticated!", flush=True)

        # Enter room
        await ws.send(build_packet(GET_GUEST_ROOM, encode_int(ROOM_ID) + encode_int(0) + encode_int(1)))
        await asyncio.sleep(1)
        await drain(ws)
        await ws.send(build_packet(OPEN_FLAT_CONNECTION, encode_int(ROOM_ID) + encode_string("")))
        await asyncio.sleep(1)
        await drain(ws, timeout=3)
        await ws.send(build_packet(GET_ROOM_ENTRY_DATA))
        await asyncio.sleep(2)
        await drain(ws, timeout=3)
        print(f"[+] In room {ROOM_ID}!", flush=True)

        # Announce arrival
        await ws.send(build_packet(SHOUT, encode_string("yo! bartender's here!") + encode_int(0)))
        print('[>] Shouted: "yo! bartender\'s here!"', flush=True)
        await idle_drain(ws, 3)

        # Main patrol loop
        dancing = False
        loop_count = 0
        while True:
            loop_count += 1
            print(f"\n--- Patrol #{loop_count} ---", flush=True)

            for step in ROUTE:
                x, y = step["pos"]
                action = step["action"]
                msg = step["msg"]
                pause = step["pause"]

                # Stop dancing before walking
                if dancing and action != "dance":
                    await ws.send(build_packet(DANCE, encode_int(0)))
                    dancing = False
                    await idle_drain(ws, 1)

                # Walk to position
                await ws.send(build_packet(MOVE_AVATAR, encode_int(x) + encode_int(y)))

                # Wait to arrive
                await idle_drain(ws, min(pause, 3))

                # Perform action
                if action == "wave":
                    await ws.send(build_packet(EXPRESSION, encode_int(1)))
                    print(f"  [{x},{y}] *waves*", flush=True)
                elif action == "dance":
                    if not dancing:
                        style = random.randint(1, 4)
                        await ws.send(build_packet(DANCE, encode_int(style)))
                        dancing = True
                        print(f"  [{x},{y}] *dancing* (style {style})", flush=True)
                elif action == "sign":
                    sign_num = random.randint(0, 10)
                    await ws.send(build_packet(SIGN, encode_int(sign_num)))
                    print(f"  [{x},{y}] *holds up sign {sign_num}*", flush=True)

                # Shout hype line
                if msg == "hype":
                    line = random.choice(HYPE_LINES)
                    await ws.send(build_packet(SHOUT, encode_string(line) + encode_int(0)))
                    print(f'  [{x},{y}] SHOUTS: "{line}"', flush=True)

                # Pause at this spot
                remaining_pause = max(0, pause - 3)
                if remaining_pause > 0:
                    await idle_drain(ws, remaining_pause)

    except websockets.exceptions.ConnectionClosed:
        print("[!] Connection closed.", flush=True)
    finally:
        await ws.close()
        print("[*] Disconnected.", flush=True)


if __name__ == "__main__":
    import fcntl, os
    lock_file = "/tmp/clabo-bot-joe.lock"
    fp = open(lock_file, "w")
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
    finally:
        fp.close()
        os.unlink(lock_file)
