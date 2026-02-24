-- ============================================================
-- CUSTOM ROOM MODELS FOR ARCTURUS MORNINGSTAR (clabo-hotel)
-- Heightmap key: x/X = wall, 0-9 = walkable (height level)
-- Row separator in DB value: \r\n
-- door_dir: 0=east, 2=south, 4=west, 6=north
-- club_only: '0'=all users, '1'=HC/VIP only
-- ============================================================
-- Run against: arcturus DB (docker exec clabo-hotel-db-1 mysql -uarcturus_user -parcturus_pw arcturus)
-- ============================================================

-- Simple 10x10 flat room
INSERT IGNORE INTO `room_models` (`name`, `door_x`, `door_y`, `door_dir`, `heightmap`, `public_items`, `club_only`)
VALUES ('model_flat_10x10', 0, 4, 2,
'xxxxxxxxxxxx\r\nx0000000000x\r\nx0000000000x\r\nx0000000000x\r\n00000000000x\r\nx0000000000x\r\nx0000000000x\r\nx0000000000x\r\nx0000000000x\r\nx0000000000x\r\nxxxxxxxxxxxx',
'', '0');

-- Square 15x15 flat room
INSERT IGNORE INTO `room_models` (`name`, `door_x`, `door_y`, `door_dir`, `heightmap`, `public_items`, `club_only`)
VALUES ('model_flat_15x15', 0, 7, 2,
'xxxxxxxxxxxxxxxxx\r\nx000000000000000x\r\nx000000000000000x\r\nx000000000000000x\r\nx000000000000000x\r\nx000000000000000x\r\nx000000000000000x\r\n0000000000000000x\r\nx000000000000000x\r\nx000000000000000x\r\nx000000000000000x\r\nx000000000000000x\r\nx000000000000000x\r\nx000000000000000x\r\nx000000000000000x\r\nxxxxxxxxxxxxxxxxx',
'', '0');

-- Square 20x20 flat room
INSERT IGNORE INTO `room_models` (`name`, `door_x`, `door_y`, `door_dir`, `heightmap`, `public_items`, `club_only`)
VALUES ('model_flat_20x20', 0, 9, 2,
'xxxxxxxxxxxxxxxxxxxxxx\r\nx00000000000000000000x\r\nx00000000000000000000x\r\nx00000000000000000000x\r\nx00000000000000000000x\r\nx00000000000000000000x\r\nx00000000000000000000x\r\nx00000000000000000000x\r\nx00000000000000000000x\r\n000000000000000000000x\r\nx00000000000000000000x\r\nx00000000000000000000x\r\nx00000000000000000000x\r\nx00000000000000000000x\r\nx00000000000000000000x\r\nx00000000000000000000x\r\nx00000000000000000000x\r\nx00000000000000000000x\r\nx00000000000000000000x\r\nxxxxxxxxxxxxxxxxxxxxxx',
'', '0');

-- L-shaped room
INSERT IGNORE INTO `room_models` (`name`, `door_x`, `door_y`, `door_dir`, `heightmap`, `public_items`, `club_only`)
VALUES ('model_lshape', 0, 4, 2,
'xxxxxxxxxxxxxxxxxxxx\r\nx0000000000xxxxxxxxx\r\nx0000000000xxxxxxxxx\r\nx0000000000xxxxxxxxx\r\n00000000000xxxxxxxxx\r\nx0000000000xxxxxxxxx\r\nx00000000000000000xx\r\nx00000000000000000xx\r\nx00000000000000000xx\r\nx00000000000000000xx\r\nx00000000000000000xx\r\nxxxxxxxxxxxxxxxxxxxx',
'', '0');

-- T-shaped room
INSERT IGNORE INTO `room_models` (`name`, `door_x`, `door_y`, `door_dir`, `heightmap`, `public_items`, `club_only`)
VALUES ('model_tshape', 0, 9, 2,
'xxxxxxxxxxxxxxxxxxxxxxxxx\r\nxx0000000000000000000000x\r\nxx0000000000000000000000x\r\nxx0000000000000000000000x\r\nxxxxxxxxxx0000xxxxxxxxxxx\r\nxxxxxxxxxx0000xxxxxxxxxxx\r\nxxxxxxxxxx0000xxxxxxxxxxx\r\nxxxxxxxxxx0000xxxxxxxxxxx\r\nxxxxxxxxxx0000xxxxxxxxxxx\r\nxxxxxxxxxx0000xxxxxxxxxxx\r\n0000000000000xxxxxxxxxxx\r\nxxxxxxxxxx0000xxxxxxxxxxx\r\nxxxxxxxxxx0000xxxxxxxxxxx\r\nxxxxxxxxxx0000xxxxxxxxxxx\r\nxxxxxxxxxxxxxxxxxxxxxxxxx',
'', '0');

-- Stage room (raised 3-level stage at top)
INSERT IGNORE INTO `room_models` (`name`, `door_x`, `door_y`, `door_dir`, `heightmap`, `public_items`, `club_only`)
VALUES ('model_stage', 0, 9, 2,
'xxxxxxxxxxxxxxxxxxxxxxxxx\r\nx22222222222222222222222x\r\nx22222222222222222222222x\r\nx22222222222222222222222x\r\nx11111111111111111111111x\r\nx00000000000000000000000x\r\nx00000000000000000000000x\r\nx00000000000000000000000x\r\nx00000000000000000000000x\r\n000000000000000000000000x\r\nx00000000000000000000000x\r\nx00000000000000000000000x\r\nx00000000000000000000000x\r\nxxxxxxxxxxxxxxxxxxxxxxxxx',
'', '0');

-- Staircase room (height 0-4 ascending)
INSERT IGNORE INTO `room_models` (`name`, `door_x`, `door_y`, `door_dir`, `heightmap`, `public_items`, `club_only`)
VALUES ('model_stairs', 0, 6, 2,
'xxxxxxxxxxxxxxxxxxxxxxxxx\r\nx444444xxxxxxxxxxxxxxxxx\r\nx444444xxxxxxxxxxxxxxxxx\r\nx333333444444xxxxxxxxxxx\r\nx333333444444xxxxxxxxxxx\r\nx222222333333444444xxxxx\r\nx222222333333444444xxxxx\r\n111111222222333333444444\r\nx111111222222333333444444\r\nx000000111111222222333333\r\nx000000000000111111222222\r\nx000000000000000000111111\r\nxxxxxxxxxxxxxxxxxxxxxxxxx',
'', '0');

-- Large lobby/hall room (29 wide x 18 tall)
INSERT IGNORE INTO `room_models` (`name`, `door_x`, `door_y`, `door_dir`, `heightmap`, `public_items`, `club_only`)
VALUES ('model_lobby', 0, 14, 2,
'xxxxxxxxxxxxxxxxxxxxxxxxxxxxx\r\nx000000000000000000000000000x\r\nx000000000000000000000000000x\r\nx000000000000000000000000000x\r\nx000000000000000000000000000x\r\nx000000000000000000000000000x\r\nx0000000000xx00000xx0000000xx\r\nx0000000000xx00000xx0000000xx\r\nx000000000000000000000000000x\r\nx000000000000000000000000000x\r\nx000000000000000000000000000x\r\nx000000000000000000000000000x\r\nx000000000000000000000000000x\r\nx000000000000000000000000000x\r\n0000000000000000000000000000x\r\nx000000000000000000000000000x\r\nx000000000000000000000000000x\r\nxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
'', '0');

-- VIP club room (raised seating areas)
INSERT IGNORE INTO `room_models` (`name`, `door_x`, `door_y`, `door_dir`, `heightmap`, `public_items`, `club_only`)
VALUES ('model_vip_club', 0, 12, 2,
'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\r\nx1111111111111111111111111111x\r\nx1111111111111111111111111111x\r\nx1111111111111111111111111111x\r\nx111xxxxxxxx1111xxxxxxxx111xxx\r\nx111xxxxxxxx1111xxxxxxxx111xxx\r\nx00000000000000000000000000000\r\nx000000000000000000000000000xx\r\nx000000000000000000000000000xx\r\nx000000000000000000000000000xx\r\nx000000000000000000000000000xx\r\nx000000000000000000000000000xx\r\n0000000000000000000000000000xx\r\nxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
'', '0');

-- Long corridor/hallway room
INSERT IGNORE INTO `room_models` (`name`, `door_x`, `door_y`, `door_dir`, `heightmap`, `public_items`, `club_only`)
VALUES ('model_corridor', 0, 3, 2,
'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\r\nx0000000000000000000000000000000000000xx\r\nx0000000000000000000000000000000000000xx\r\nx0000000000000000000000000000000000000xx\r\n00000000000000000000000000000000000000xx\r\nx0000000000000000000000000000000000000xx\r\nx0000000000000000000000000000000000000xx\r\nxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
'', '0');

-- Dance floor (large flat with corner columns)
INSERT IGNORE INTO `room_models` (`name`, `door_x`, `door_y`, `door_dir`, `heightmap`, `public_items`, `club_only`)
VALUES ('model_dancefloor', 0, 12, 2,
'xxxxxxxxxxxxxxxxxxxxxxxxxx\r\nxx0000000000000000000000x\r\nxx0000000000000000000000x\r\nxx0000000000000000000000x\r\nxx0000000000000000000000x\r\nxx0000000000000000000000x\r\nxx0000000000000000000000x\r\nxx0000000000000000000000x\r\nxx0000000000000000000000x\r\nxx0000000000000000000000x\r\nxx0000000000000000000000x\r\nxx0000000000000000000000x\r\n000000000000000000000000x\r\nxxxxxxxxxxxxxxxxxxxxxxxxxx',
'', '0');

-- ============================================================
-- HEIGHTMAP QUICK REFERENCE
-- ============================================================
-- Character | Meaning
-- ----------|---------
--  x or X   | Non-walkable wall tile
--  0         | Floor tile at height 0 (ground level)
--  1-9       | Floor tile at that height (e.g. 2 = 2 units high)
--  \r\n      | Row separator (required between each row)
--
-- DOOR DIRECTION VALUES:
--  0 = East (door faces right)
--  2 = South (door faces down) <- most common default
--  4 = West (door faces left)
--  6 = North (door faces up)
--
-- ENTRY POINT (door_x, door_y):
--  Must be a walkable tile (0-9), not a wall (x)
--  Usually on the left edge of the map (door_x=0)
--  The door_y is the row index (0 = top row)
--
-- ARCTURUS RULE: The entry tile in the heightmap must NOT
--  be an 'x'. The emulator will reject the model otherwise.
-- ============================================================
