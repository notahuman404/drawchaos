# room_manager.py 

# create, manage and DESTROY💣    rooms

import uuid # nah, you saw the comment and thought i was gonna write about what this is used for. If you did then you are wrong
import time 
import random
from invite_manager import generate_code, validate_code, revoke_code

_rooms: dict[str, dict] = {}

def create_room(host_sid: str, host_name: str, settings: dict) -> dict: 
    room_id = str(uuid.uuid4())[:8].upper()
    invite_code = generate_code(room_id)

    room = {
        "id": room_id,
        "invite_code": invite_code,
        "host_sid": host_sid,
        "settings": settings,
        "players": {},
        "spectators": {},
        "state": "lobby",
        "current_round": 0,
        "current_drawer_sid": None,
        "current_word": None,
        "current_fake_word": None,
        "round_start_time": None,
        "guesses": [],
        "submitted_words": {},
        "active_twists": [],
        "twist_assignments": {},
        "stroke_log": [],
        "stolen_strokes": {},
        "imposter_sid": None,
        "ghost_sid": None,
        "thieves": [],
        "snail_positions": {},
        "hijack_pairs": {},           # { controller_sid: victim_sid }
        
    }