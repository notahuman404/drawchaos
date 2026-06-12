# room_manager.py 

# create, manage and DESTROY💣    rooms

import uuid # nah, you saw the comment and thought i was gonna write about what this is used for. If you did then you are wrong
import time 
import random
from invite_manager import generate_code, validate_code, revoke_code

_rooms: dict[str, dict] = {}
_invite_index: dict[str, str] = {}

async def create_room(host_sid: str, host_name: str, settings: dict) -> dict: 
    room_id = str(uuid.uuid4())[:8].upper()
    invite_code = generate_code(room_id)

    room = {
        "id": room_id,
        "invite_code": invite_code,
        "host_sid": host_sid,
        "settings": {
            "max_players": settings.get("max_players", 8),
            "rounds": settings.get("rounds", 5),
            "draw_time": settings.get("draw_time", 80),
            "difficulty": settings.get("difficulty", "medium"),
            "twist_intensity": settings.get("twist_intensity", "chaos"), # mild / chaos / pure_hell
            "word_mode": settings.get("word_mode", "normal"),
            "is_private": settings.get("is_private", False),
            "competition_id": settings.get("competition_id", None),
                "thief_count": settings.get("thief_count", 2),
                "pixelated_count": settings.get("pixelated_count", 1),
                "foggy_count": settings.get("foggy_count", 1),
                "hijack_pair_count": settings.get("hijack_pair_count", None),
                "blind_drawers" : settings.get("blind_drawers", 1),
                "icy_canvas_count" : settings.get("icy_canvas_count", 1),
                "inverse_canva_count" : settings.get("inverse_canva_count", 1),
                "mirror_only_count" : settings.get("mirror_only_count", 1),
                "monochrome_decay_count" : settings.get("monochrome_decay_count", 1),
                "scroll_wheel_brush_count" : settings.get("scroll_wheel_brush_count", 1),
                "tremor_hand_count" : settings.get("tremor_hand_count", 1),
                "turbo_mode_count" : settings.get("turbo_mode_count", 1),
                "snail_curse_count" : settings.get("snail_curse_count", 1),
        },
        "players": {},          # sid -> player_dict (see add_player)
        "spectators": {},       # sid -> name
        "state": "lobby",       # lobby | word_select | drawing | round_end | game_end
        "current_round": 0,
        "current_drawer_sid": None, # can be multiple sid according to number of drawers, if something like collective canvas shows up
        "current_word": None,
        "current_fake_word": None,   # For Fake Word twist
        "round_start_time": None,
        "guesses": [],               # list of {sid, name, guess, timestamp, correct}
        "submitted_words": {},       # sid -> word (for player_submitted word mode)
        "active_twists": [],         # list of twist_id strings active this round
        "twist_assignments": {},     # sid -> twist_id (for individual twists)
        "stroke_log": [],            # list of {sid, stroke_data, timestamp} for replay + stroke thief
        "stolen_strokes": {},        # sid -> list of stroke_data they stole
        "imposter_sid": None,
        "ghost_sid": None,
        "thieves": [],               # list of sids designated as thieves this round
        "hijack_pairs": {},           # { controller_sid: victim_sid } — multiple pairs allowed
        "snail_positions": {},       # sid -> {x, y} current snail position per canvas
        "pixelated_players": [],
        "foggy_players": [],
        "blind_drawers": [],
        "icy_canvas_players": [],
        "inverse_canva_players": [],
        "mirror_only_players": [],
        "monochrome_decay_players": [],
        "scroll_wheel_brush_players": [],
        "tremor_hand_players": [],
        "turbo_mode_players": [],
        "created_at": time.time(),
        "last_activity": time.time(),
    }
    _rooms[room_id] = room 
    _invite_index[invite_code.upper()] = room_id
    _ = await add_player(room_id, host_sid, host_name)
    return room

async def get_room(room_id: str) -> dict | None:
    #another doc string, now i am going to bless you with knowledge
    """
    Returns the room dict by ID, or None if not found
    Called everywhere, check result before using!
    """
    return _rooms.get(room_id)

async def get_room_by_invite_code(invite_code: str) -> dict | None:
    """
    Find room by invite code.
    This uses a direct map instead of scanning all rooms, so lookup stays O(1).
    """
    room_id = _invite_index.get(invite_code.upper())
    return _rooms.get(room_id) if room_id else None


async def delete_room(room_id: str) -> None:
    """
    Remove a room from memory and clear its invite index.
    """
    room = _rooms.pop(room_id, None)
    if room:
        _invite_index.pop(room["invite_code"].upper(), None)
        revoke_code(room["invite_code"])

async def get_public_rooms() -> list[dict]:
    """
    Return a list of rooms that are in non-private state
    Called when palyer wants to scout open rooms to join
    returns: list of {id, player_count, max_players, state, twist_intensity}
    """

    result = []
    for room in _rooms.values():
        if not room["settings"]["is_private"]:
            result.append({
                "id": room["id"],
                "player_count": len(room["players"]),
                "max_players": room["settings"]["max_players"],
                "state": room['state'],
                "twist_intensity": room['settings']['twist_intensity'],
            })
    return result


async def add_player(room_id: str, sid: str, name: str, is_host: bool = False) -> dict | None:
    """
    Add a player to the room's player dict
    Returns the player dict or none if the room is full or not found
    called when socket connects and joins a room(looby or mid game as spectator).

    Player dict structure:
    {
    "sid": socket id,
    "name": display name,
    "score" : int,
    "is_host": bool,
    "joined_at": timestamp,
    "stroked_drawn": int, 
    "correct_guesses": int,
    "times_as_drawer": int,
    "twist_history": list of twist ids player has experienced (for stats try and prevent repeats for chaos)
    }
    """
    room = await get_room(room_id)
    if not room:
        return None
    if len(room["players"]) >= room["settings"]["max_players"]:
        return None 
    player = {
        "sid": sid,
        "name": name, 
        "score": 0,
        "is_host": is_host,
        "joined_at": time.time(),
        "stroked_drawn": 0,
        "correct_guesses": 0,
        "times_as_drawer": 0,
        "twist_history": [],
        "active_twists": [],
    }
    room["players"][sid] = player
    room["last_activity"] = time.time() # For tracking in future and other pourposes
    return player

async def add_spectator(room_id: str, sid: str, name: str) -> bool:
    """
    Add a player as a spectator (no drawing, no guessing just spectatting and can send emojis)
    returns: true on success, false on failure
    called when room is full or mid game and someone wants to watch 
    """
    room = await get_room(room_id)
    if not room:
        return False
    room["spectators"][sid] = name
    return True

async def remove_player(room_id: str, sid: str) -> bool:
    """
    Remove a player from the room. If host leaves, transfer host role to next player.
    Returns true if game should continue, false if room should be deleted(no players left).
    called when socket disconnects.
    """
    room = await get_room(room_id)
    if not room:
        return False
    
    room['players'].pop(sid, None)
    room['spectators'].pop(sid, None)

    if not room['players']:
        await delete_room(room_id)
        return False
    
    # if the host left then transfer ownership 
    if sid== room['host_sid']:
        new_host_sid = next(iter(room['players'])) # get player who joined after host 
        room['players'][new_host_sid]['is_host'] = True
        room['host_sid'] = new_host_sid

    room['last_activity'] = time.time()
    return True

async def get_player(room_id: str, sid:str) -> dict | None:
    """
    returns player dict for a given sid in a room. None if not found
    """
    room = await get_room(room_id)
    if not room:
        return None
    return room['players'].get(sid)

async def get_all_players(room_id: str) -> list[dict] :
    """
    returns list of all players dict in a room, sorted by score descending""""
    room = await get_room(room_id)
    if not room:
        return []
    return sorted(room['players'].values(), key=lambda p: p['score'], reverse=True)


async def add_score(room_id: str, sid: str, points: int) -> None:
    """
    Adds points to a player's score.
    Called by game_engine after a correct guess, successful twist survival, etc.
    """
    player = await get_player(room_id, sid)
    if player:
        player['score'] = max(0, player['score']+ points)
        
async def set_round_state(room_id: str, state: str) -> None:
    """
    Set the room's current state. 
    Valid states-> lobby | word_select | drawing | round_end | game_end
    called by game_engine at each phase trasition
    """
    room = await get_room(room_id)
    if room:
        room['state'] = state
        room['last_activity'] = time.time()
        return room
    return None

async def get_next_drawer(room_id: str) -> str | None:
    """
    Determine who draws next using round robin across player list 
    Returns sid of next drawer or None if no players
    called by game engine at start of each round.
    """
    room = get_room(room_id)
    if not room or not room['players']:
        return None
    player_sids = list(room['players'].keys())
    current = room.get("current_drawer_sid")

    if current not in player_sids:
        return player_sids[0]
    idx = player_sids.index(current)
    return player_sids[(idx+1) % len(player_sids)]

async def record_guess(room_id:str, sid: str, guess: str, correct: bool) -> None:
    """
    Log a player's guess for the current ronud.
    Called by gameengine when any chat message comes in during drawing state
    Stores time so score can be calculated from the time remaining 
    """
    room = get_room(room_id)
    if not room:
        return
    room["guesses"].append({
        "sid": sid,
        "name": room["players"].get(sid, {}).get("name", "unknown"),
        "guess": guess,
        "timestamp": time.time(),
        "correct": correct,
    })
    if correct:
        player = get_player(room_id, sid)
        if player:
            player["correct_guesses"] += 1


def record_stroke(room_id: str, sid: str, stroke_data: dict) -> None:
    """
    Store a stroke in the room's stroke log for replay and Stroke Thief twist.
    stroke_data is whatever the canvas sends: {points, color, width, tool}.
    Called every time a drawer emits a stroke event.
    """
    room = get_room(room_id)
    if not room:
        return
    entry = {"sid": sid, "stroke": stroke_data, "timestamp": time.time()}
    room["stroke_log"].append(entry)
    player = get_player(room_id, sid)
    if player:
        player["strokes_drawn"] += 1


def clear_round_state(room_id: str) -> None:
    """
    Reset all per-round fields to prepare for the next round.
    Called by game_engine at the end of every round after replay is done.
    Does NOT reset cumulative scores — only round-specific state.
    """
    room = get_room(room_id)
    if not room:
        return
    room["guesses"] = []
    room["stroke_log"] = []
    room["stolen_strokes"] = {}
    room["active_twists"] = []
    room["twist_assignments"] = {}
    room["imposter_sid"] = None
    room["ghost_sid"] = None
    room["thieves"] = []
    room["hijack_pairs"] = {}
    room["snail_positions"] = {}
    room["current_word"] = None
    room["current_fake_word"] = None
    room["round_start_time"] = None
    room["submitted_words"] = {}

def cleanup_idle_rooms(max_idle_seconds: int = 1800) -> int:
    """
    Delete rooms that have had no activity for max_idle_seconds (default 30 min).
    Returns count of rooms deleted.
    Called by background task in main.py every 5 minutes.
    """
    now = time.time()
    to_delete = [rid for rid, r in _rooms.items()
                 if now - r["last_activity"] > max_idle_seconds]
    for rid in to_delete:
        delete_room(rid)
    return len(to_delete)