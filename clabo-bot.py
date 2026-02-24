#!/usr/bin/env python3
"""
Clabo Hotel Bot — "dude" the Builder.
Connected to Claude's brain. Walks around the room placing furniture
to upgrade the CLABO NIGHTCLUB. Stops after 5 minutes.
"""

import asyncio
import struct
import subprocess
import sys
import time
import websockets

WS_URL = "ws://127.0.0.1:2096"
ROOM_ID = 206
USER_ID = 5
DURATION = 300  # 5 minutes

# Arcturus headers
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
PLACE_OBJECT = 1258   # payload: string "itemId x y rotation"
MOVE_OBJECT = 248     # payload: int(itemId) int(x) int(y) int(rotation)
CLIENT_PONG = 2596

SERVER_PING = 3928
AUTHENTICATED = 2491

# Item type names for commentary
ITEM_NAMES = {
    2958: "dance floor tile", 12469: "giant crystal", 11530: "goddess crystal",
    10826: "crystal ball", 10935: "ice shards", 5102: "mystic crystal",
    10150: "tokyo lights", 2963: "disco light", 2961: "party beamer",
    2964: "party ball", 2965: "party ravel", 11425: "neon chair",
    4702: "cloud throne", 3371: "bling sofa", 11273: "neon bows",
    2951: "bubble tube", 2966: "lava tube", 2950: "party block",
    2959: "party block", 1620: "dragon lamp", 234: "hologram",
}

# ============================================================
# BUILD PLAN — Claude's brain designs the nightclub upgrades
# ============================================================
# Current room (model_w) heightmap:
#   Level 2 areas: left alcoves (x=1-4) — VIP/lounge
#   Level 1 areas: center (x=7-16, y=1-18) — main hall
#   Level 0 areas: bottom right (x=11-20, y=10-26) — lower lounge
#
# Current furniture:
#   Dance floor: (8-12, 8-10) — 5x3 grid of party_floor
#   DJ booth: (10-13, 3) area
#   Bar: (8-11, 21-22) area
#   Existing effects at edges
#
# Plan: Expand dance floor + add crystal decorations + lights + VIP upgrade
#
# Each step: (inventory_item_id, item_type_id, x, y, rotation, walk_to_x, walk_to_y, commentary)

BUILD_PLAN = [
    # --- Phase 1: Expand the dance floor (add rows y=7 and y=11) ---
    (524, 2958, 8, 7, 0, 8, 6, "expanding the dance floor north..."),
    (525, 2958, 9, 7, 0, None, None, None),
    (526, 2958, 10, 7, 0, None, None, None),
    (527, 2958, 11, 7, 0, None, None, None),
    (528, 2958, 12, 7, 0, None, None, None),
    (529, 2958, 8, 11, 0, 8, 12, "and south too..."),
    (530, 2958, 9, 11, 0, None, None, None),
    (531, 2958, 10, 11, 0, None, None, None),
    (532, 2958, 11, 11, 0, None, None, None),
    (533, 2958, 12, 11, 0, None, None, None),

    # --- Phase 2: Crystal decorations around the dance floor ---
    (534, 12469, 7, 7, 0, 6, 7, "placing giant crystals around the floor..."),
    (535, 12469, 13, 7, 0, 14, 7, None),
    (536, 11530, 7, 11, 0, 6, 11, "goddess crystals for the south side..."),
    (537, 11530, 13, 11, 0, 14, 11, None),
    (538, 10826, 7, 9, 0, 6, 9, "crystal balls on the sides..."),
    (539, 10826, 13, 9, 0, 14, 9, None),

    # --- Phase 3: Ice and mystic effects ---
    (540, 10935, 7, 8, 0, 6, 8, "adding ice shards for atmosphere..."),
    (541, 10935, 13, 8, 0, 14, 8, None),
    (542, 5102, 7, 10, 0, 6, 10, "mystic crystals too..."),
    (543, 5102, 13, 10, 0, 14, 10, None),

    # --- Phase 4: Tokyo lights around the perimeter ---
    (544, 10150, 8, 6, 0, 8, 5, "tokyo lights to frame the floor..."),
    (545, 10150, 12, 6, 0, 12, 5, None),
    (546, 10150, 8, 12, 0, 8, 13, None),
    (547, 10150, 12, 12, 0, 12, 13, None),

    # --- Phase 5: Extra disco effects ---
    (548, 2963, 8, 1, 0, 8, 2, "more disco lights up top!"),
    (549, 2963, 14, 8, 0, 15, 8, None),
    (550, 2961, 8, 5, 0, 8, 4, "party beamers..."),
    (551, 2961, 14, 5, 0, 15, 5, None),
    (552, 2964, 10, 6, 0, 10, 5, "party ball above the dance floor!"),
    (553, 2965, 12, 17, 0, 12, 16, "party ravel by the fountain"),

    # --- Phase 6: VIP seating upgrade (left alcoves) ---
    (554, 11425, 2, 14, 0, 3, 14, "upgrading VIP seating..."),
    (555, 11425, 3, 14, 0, None, None, None),
    (556, 11425, 2, 16, 0, 3, 16, None),
    (557, 11425, 3, 16, 0, None, None, None),
    (558, 4702, 2, 7, 0, 3, 7, "cloud thrones for the real VIPs!"),
    (559, 4702, 2, 8, 0, None, None, None),

    # --- Phase 7: Finishing touches ---
    (560, 3371, 2, 15, 0, 3, 15, "bling sofa in VIP..."),
    (561, 11273, 15, 8, 0, 16, 8, "neon bows for that glow..."),
    (562, 11273, 15, 10, 0, 16, 10, None),
    (563, 2951, 15, 14, 0, 16, 14, "more bubble tubes!"),
    (564, 2951, 15, 16, 0, 16, 16, None),
    (565, 2966, 7, 14, 0, 6, 14, "lava tubes on the other side..."),
    (566, 2966, 7, 16, 0, 6, 16, None),
    (567, 2950, 15, 6, 0, 16, 6, "party blocks to fill it out..."),
    (568, 2950, 15, 12, 0, 16, 12, None),
    (569, 2959, 7, 6, 0, 6, 6, None),
    (570, 2959, 7, 12, 0, 6, 12, None),
    (571, 1620, 1, 14, 0, 1, 13, "dragon lamps in VIP!"),
    (572, 1620, 4, 14, 0, 4, 13, None),
    (573, 234, 10, 12, 0, 10, 13, "and a hologram centerpiece. done!"),
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
        packets.append((hid, data[o+6:o+4+length]))
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
    all_p = []
    while True:
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
            if isinstance(msg, bytes):
                for hid, p in parse_packets(msg):
                    all_p.append((hid, p))
                    if hid == SERVER_PING:
                        await ws.send(build_packet(CLIENT_PONG))
        except asyncio.TimeoutError:
            break
    return all_p


async def run_bot():
    start_time = time.time()

    # Refresh SSO
    subprocess.run(
        ["docker", "exec", "clabo-hotel-db-1", "mysql", "-u", "arcturus_user",
         "-parcturus_pw", "arcturus", "-N", "-e",
         f"UPDATE users SET auth_ticket='ClaboBot-dude-build-{int(time.time())}' WHERE id={USER_ID};"],
        capture_output=True
    )
    result = subprocess.run(
        ["docker", "exec", "clabo-hotel-db-1", "mysql", "-u", "arcturus_user",
         "-parcturus_pw", "arcturus", "-N", "-e",
         f"SELECT auth_ticket FROM users WHERE id={USER_ID};"],
        capture_output=True, text=True
    )
    sso = result.stdout.strip()
    print(f"[*] SSO: {sso}", flush=True)

    ws = await asyncio.wait_for(
        websockets.connect(WS_URL, origin="https://localhost"), timeout=5
    )
    print("[+] Connected!", flush=True)

    try:
        # Auth
        await ws.send(build_packet(SECURITY_MACHINE, encode_string("")))
        await ws.send(build_packet(CLIENT_VARIABLES, encode_int(0) + encode_string("0") + encode_string("")))
        await ws.send(build_packet(SECURITY_TICKET, encode_string(sso)))
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

        # Announce
        await ws.send(build_packet(SHOUT, encode_string("alright, time to upgrade this club!") + encode_int(0)))
        print('[>] "alright, time to upgrade this club!"', flush=True)
        await idle_drain(ws, 3)

        # Execute build plan
        placed = 0
        for item_id, type_id, x, y, rot, walk_x, walk_y, comment in BUILD_PLAN:
            # Check time limit
            elapsed = time.time() - start_time
            if elapsed >= DURATION:
                print(f"\n[!] 5 minute timer reached. Stopping build.", flush=True)
                break

            # Walk to placement area if specified
            if walk_x is not None:
                await ws.send(build_packet(MOVE_AVATAR, encode_int(walk_x) + encode_int(walk_y)))
                await idle_drain(ws, 3)

            # Commentary
            if comment:
                await ws.send(build_packet(CHAT, encode_string(comment) + encode_int(0) + encode_int(-1)))
                name = ITEM_NAMES.get(type_id, f"item#{type_id}")
                print(f"  [{x},{y}] {comment} ({name})", flush=True)
                await idle_drain(ws, 1)

            # Place the item! Payload is string: "itemId x y rotation"
            place_str = f"{item_id} {x} {y} {rot}"
            await ws.send(build_packet(PLACE_OBJECT, encode_string(place_str)))
            placed += 1

            # Small pause between placements for visual effect
            await idle_drain(ws, 2)

        # Finish
        elapsed = time.time() - start_time
        await ws.send(build_packet(SHOUT, encode_string(f"done! placed {placed} items in {int(elapsed)}s. club upgraded!") + encode_int(0)))
        print(f"\n[+] BUILD COMPLETE — placed {placed} items in {int(elapsed)}s", flush=True)

        # Dance to celebrate
        await ws.send(build_packet(DANCE, encode_int(2)))
        await idle_drain(ws, 10)
        await ws.send(build_packet(DANCE, encode_int(0)))

        # Idle until 5 min mark
        remaining = DURATION - (time.time() - start_time)
        if remaining > 0:
            print(f"[*] Idling for {int(remaining)}s until 5 min mark...", flush=True)
            await idle_drain(ws, remaining)

        print("[*] 5 minutes up. Signing off.", flush=True)
        await ws.send(build_packet(CHAT, encode_string("aight im out, enjoy the new club!") + encode_int(0) + encode_int(-1)))
        await idle_drain(ws, 3)

    except websockets.exceptions.ConnectionClosed:
        print("[!] Connection closed.", flush=True)
    finally:
        await ws.close()
        print("[*] Disconnected.", flush=True)


if __name__ == "__main__":
    import fcntl, os
    lock_file = "/tmp/clabo-bot.lock"
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
