# twist_engine.py
# Purpose: Define, select, and apply all chaos twists.
# Each twist is a config dict + a set of server-side functions.
# Client-side effects live in static/js/twists.js (you build that later).
# The engine tells clients WHAT to do — the client renders it.
import copy
import random
import asyncio
import time
from room_manager import (
    get_room, get_all_players, add_score, get_player,
    record_stroke, set_round_state
)


# ─── Twist Registry ───────────────────────────────────────────────────────────
# Every twist is registered here.
# intensity: "mild" | "chaos" | "pure_hell"
# scope: "room" (affects everyone) | "individual" (assigned to specific player)
# timing: "start" (activated at round start) | "mid" (fires mid-round randomly)
# target: "drawer" | "guesser" | "random" | "all"


MILD = {'copycat': {'description': 'One player must copy the style of the previous '
                            "round's winning drawing. Voted on by others.",
             'id': 'copycat',
             'intensity': 'mild',
             'name': 'Copycat',
             'scope': 'individual',
             'target': 'random',
             'timing': 'start'},
 'elimination_round': {'description': 'The player whose drawing gets fewest '
                                      'correct guesses is eliminated.',
                       'id': 'elimination_round',
                       'intensity': 'mild',
                       'name': 'Elimination Round',
                       'scope': 'room',
                       'target': 'all',
                       'timing': 'start'},
 'foggy_canvas': {'description': 'One or more guessers see a densely fogged '
                                 'canvas. The number affected is configurable '
                                 'via room.settings.foggy_count (default 1).',
                  'id': 'foggy_canvas',
                  'intensity': 'mild',
                  'name': 'Foggy Canvas',
                  'scope': 'individual',
                  'target': 'guesser',
                  'timing': 'start'},
 'hot_and_cold': {'description': 'Every 10 seconds drawer is told if best '
                                 'current guess is warmer or colder. No actual '
                                 'guesses shown.',
                  'id': 'hot_and_cold',
                  'intensity': 'mild',
                  'name': 'Hot and Cold',
                  'scope': 'room',
                  'target': 'drawer',
                  'timing': 'start'},
 'jury_round': {'description': 'No drawing. Three previous canvases shown. '
                               'Players vote on which best matched its word.',
                'id': 'jury_round',
                'intensity': 'mild',
                'name': 'Jury Round',
                'scope': 'room',
                'target': 'all',
                'timing': 'start'},
 'pixelated_vision': {'description': "One or more guessers see the drawer's "
                                     'canvas heavily pixelated. The number '
                                     'affected is configurable via '
                                     'room.settings.pixelated_count (default '
                                     '1).',
                      'id': 'pixelated_vision',
                      'intensity': 'mild',
                      'name': 'Pixelated Vision',
                      'scope': 'individual',
                      'target': 'guesser',
                      'timing': 'start'},
 'ten_strokes': {'description': 'Exactly 10 strokes allowed. No undo. Canvas '
                                'locks after stroke 10.',
                 'id': 'ten_strokes',
                 'intensity': 'mild',
                 'name': '10 Strokes Hard Limit',
                 'scope': 'individual',
                 'target': 'drawer',
                 'timing': 'start'}}

CHAOS = {'audience_takeover': {'description': '5 emoji reactions in 3 seconds from '
                                      'spectators triggers crowd vote to flip '
                                      "one player's canvas for 20 seconds.",
                       'id': 'audience_takeover',
                       'intensity': 'chaos',
                       'name': 'Audience Takeover',
                       'scope': 'room',
                       'target': 'all',
                       'timing': 'mid'},
 'blind_drawer': {'description': "Drawer can't see their own canvas. Everyone "
                                 'else sees it. A late-joining guesser tries '
                                 'to decode the result.',
                  'id': 'blind_drawer',
                  'intensity': 'chaos',
                  'name': 'Blind Drawer',
                  'scope': 'individual',
                  'target': 'drawer',
                  'timing': 'start'},
 'collective_canvas': {'description': 'Everyone draws on the same canvas '
                                      'simultaneously.',
                       'id': 'collective_canvas',
                       'intensity': 'chaos',
                       'name': 'Collective Canvas',
                       'scope': 'room',
                       'target': 'all',
                       'timing': 'start'},
 'color_chaos': {'description': 'Brush color cycles to a random hue every 2 '
                                'seconds. Color picker disabled.',
                 'id': 'color_chaos',
                 'intensity': 'chaos',
                 'name': 'Color Chaos',
                 'scope': 'individual',
                 'target': 'drawer',
                 'timing': 'start'},
 'drunk_cursor': {'description': 'Every stroke drifts 20-40px in a random '
                                 'direction that changes per stroke.',
                  'id': 'drunk_cursor',
                  'intensity': 'chaos',
                  'name': 'Drunk Cursor',
                  'scope': 'individual',
                  'target': 'drawer',
                  'timing': 'start'},
 'earthquake': {'description': 'Calm while not drawing. 1-10 seconds into any '
                               'stroke, violent shaking begins. Resets each '
                               'stroke.',
                'id': 'earthquake',
                'intensity': 'chaos',
                'name': 'Earthquake',
                'scope': 'room',
                'target': 'drawer',
                'timing': 'mid'},
 'fake_word': {'description': 'Drawer knows real and fake word. Guessers each '
                              'get one — some get the real word, some the '
                              'fake.',
               'id': 'fake_word',
               'intensity': 'chaos',
               'name': 'Fake Word',
               'scope': 'room',
               'target': 'all',
               'timing': 'start'},
 'ghost_round': {'description': 'One player is invisible this round. Their '
                                'strokes appear but identity is hidden. '
                                'Survive unidentified to win bonus.',
                 'id': 'ghost_round',
                 'intensity': 'chaos',
                 'name': 'Ghost Round',
                 'scope': 'room',
                 'target': 'random',
                 'timing': 'start'},
 'icy_canvas': {'description': "Cursor slides and doesn't stop when you do — "
                               'keeps drifting like ice. Overshoots every '
                               'stroke.',
                'id': 'icy_canvas',
                'intensity': 'chaos',
                'name': 'Icy Canvas',
                'scope': 'individual',
                'target': 'drawer',
                'timing': 'start'},
 'imposter_prompt': {'description': 'One player gets a vague category instead '
                                    'of the real word.',
                     'id': 'imposter_prompt',
                     'intensity': 'chaos',
                     'name': 'Imposter Prompt',
                     'scope': 'room',
                     'target': 'all',
                     'timing': 'start'},
 'inverse_mode': {'description': 'Both X and Y axes inverted for 20 seconds. '
                                 'Announced to drawer 3 seconds before. '
                                 'Re-inverts again later.',
                  'id': 'inverse_mode',
                  'intensity': 'chaos',
                  'name': 'Inverse Mode',
                  'scope': 'individual',
                  'target': 'drawer',
                  'timing': 'mid'},
 'mirror_only': {'description': 'Drawer sees horizontally mirrored canvas. '
                                'Everyone else sees it correctly.',
                 'id': 'mirror_only',
                 'intensity': 'chaos',
                 'name': 'Mirror Only',
                 'scope': 'individual',
                 'target': 'drawer',
                 'timing': 'start'},
 'monochrome_decay': {'description': 'Every 15 seconds one color channel drops '
                                     "from drawer's view. By 45 seconds "
                                     "they're drawing blind to their own "
                                     'colors.',
                      'id': 'monochrome_decay',
                      'intensity': 'chaos',
                      'name': 'Monochrome Decay',
                      'scope': 'individual',
                      'target': 'drawer',
                      'timing': 'start'},
 'narrate_dont_draw': {'description': 'Word holder types text clues. A second '
                                      'player draws from those clues. A third '
                                      'player guesses. Telephone chain.',
                       'id': 'narrate_dont_draw',
                       'intensity': 'chaos',
                       'name': "Narrate Don't Draw",
                       'scope': 'room',
                       'target': 'all',
                       'timing': 'start'},
 'reverse_round': {'description': 'Draw your word as badly as possible on '
                                  'purpose. Players vote on sabotage '
                                  'technique.',
                   'id': 'reverse_round',
                   'intensity': 'chaos',
                   'name': 'Reverse Round',
                   'scope': 'room',
                   'target': 'all',
                   'timing': 'start'},
 'rotating_prompt': {'description': 'Everyone draws a different word. Canvases '
                                    'are shuffled and players match word to '
                                    'drawing.',
                     'id': 'rotating_prompt',
                     'intensity': 'chaos',
                     'name': 'Rotating Prompt',
                     'scope': 'room',
                     'target': 'all',
                     'timing': 'start'},
 'scroll_wheel_brush': {'description': 'Brush size only changeable by scroll '
                                       'wheel. Server randomly scrolls it '
                                       'unpredictably.',
                        'id': 'scroll_wheel_brush',
                        'intensity': 'chaos',
                        'name': 'Scroll Wheel Brush',
                        'scope': 'individual',
                        'target': 'drawer',
                        'timing': 'start'},
 'traitor_vote': {'description': 'At round end, players vote on who threw the '
                                 'round. Most accused loses half their points.',
                  'id': 'traitor_vote',
                  'intensity': 'chaos',
                  'name': 'Traitor Vote',
                  'scope': 'room',
                  'target': 'all',
                  'timing': 'start'},
 'tremor_hand': {'description': 'High-frequency jitter on every stroke — like '
                                'drawing while riding a bumpy road.',
                 'id': 'tremor_hand',
                 'intensity': 'chaos',
                 'name': 'Tremor Hand',
                 'scope': 'individual',
                 'target': 'drawer',
                 'timing': 'start'},
 'turbo_mode': {'description': "One player's cursor moves at 4x sensitivity. "
                               'Everything overshoots.',
                'id': 'turbo_mode',
                'intensity': 'chaos',
                'name': 'Turbo Mode',
                'scope': 'individual',
                'target': 'random',
                'timing': 'start'},
 'zoom_trap': {'description': 'Canvas randomly zooms to 3x or shrinks to 0.25x '
                              'for 12 seconds with no warning.',
               'id': 'zoom_trap',
               'intensity': 'chaos',
               'name': 'Zoom Trap',
               'scope': 'room',
               'target': 'drawer',
               'timing': 'mid'}}

PURE_HELL = {'cursor_hijack': {'description': 'One or more controller/victim pairs are '
                                  'created; each controller gets control of '
                                  "their victim's cursor for a short duration. "
                                  'The number of pairs is configurable via '
                                  'room.settings.hijack_pair_count (None => '
                                  'auto-pair as many as possible).',
                   'id': 'cursor_hijack',
                   'intensity': 'pure_hell',
                   'name': 'Cursor Hijack',
                   'scope': 'room',
                   'target': 'all',
                   'timing': 'mid'},
 'cursor_swap_roulette': {'description': "Everyone's cursor swaps with a "
                                         'random other player for 10 seconds. '
                                         '1/3 are warned 3 seconds early.',
                          'id': 'cursor_swap_roulette',
                          'intensity': 'pure_hell',
                          'name': 'Cursor Swap Roulette',
                          'scope': 'room',
                          'target': 'all',
                          'timing': 'mid'},
 'rewind': {'description': 'Last 10 seconds of drawing undraws itself in '
                           'reverse at 2x speed. No warning.',
            'id': 'rewind',
            'intensity': 'pure_hell',
            'name': 'Rewind',
            'scope': 'room',
            'target': 'all',
            'timing': 'mid'},
 'silent_pivot': {'description': "Mid-round the drawer's word changes with no "
                                 'announcement of what the new word is. Flash '
                                 'notification only.',
                  'id': 'silent_pivot',
                  'intensity': 'pure_hell',
                  'name': 'Silent Pivot',
                  'scope': 'individual',
                  'target': 'drawer',
                  'timing': 'mid'},
 'snail_curse': {'description': 'A snail follows your stroke trail. If it '
                                'reaches your cursor, your canvas freezes.',
                 'id': 'snail_curse',
                 'intensity': 'pure_hell',
                 'name': 'Snail Curse',
                 'scope': 'individual',
                 'target': 'drawer',
                 'timing': 'start'},
 'stroke_thief': {'description': 'Configurable number of thieves '
                                 '(room.settings.thief_count, default 2). '
                                 "Thieves may steal strokes from others' "
                                 'canvases and blend them in. Caught = lose '
                                 'points.',
                  'id': 'stroke_thief',
                  'intensity': 'pure_hell',
                  'name': 'Stroke Thief',
                  'scope': 'room',
                  'target': 'all',
                  'timing': 'start'}}

TWIST_REGISTER = MILD | CHAOS | PURE_HELL
# the conflict map

CONFLICTS = {
    "collective_canvas": ["stroke_thier", "rotating_prompt"],
    "rotating_prompt": ["imposter_prompt", "fake_word", "ghost_round",
                         "stroke_thief", "collective_canvs"],
    "cursor_hijack": ["cursor_swap_roulette"],
    # stroke thief has ten strokes as conflict because i dont wanna reduce the no. of 
    # storkes the thief can steal and if limited to only 10 strokes then the other person
    # cant paint
    "stroke_thief": ["collective_canvas", "rotating_propmt", "ten_strokes"],
    "ten_strokes": ['stroke_thief'],
    'narrate_dont_draw': ["*"],
    'jury_round': ['*'],

}
# I know i should rather make it a list but this behaviour i think is a bit faster. I am trading simplicity and readability for a bit of speed
INDIVIDUAL_TWISTs = ['copycat',
 'foggy_canvas',
 'pixelated_vision',
 'ten_strokes',
 'blind_drawer',
 'color_chaos',
 'drunk_cursor',
 'icy_canvas',
 'inverse_mode',
 'mirror_only',
 'monochrome_decay',
 'scroll_wheel_brush',
 'tremor_hand',
 'turbo_mode',
 'snail_curse']
TWIST_COUNT_MAP = {
    "stroke_thief":         ("thief_count",                 "thieves"),
    "pixelated_vision":     ("pixelated_count",             "pixelated_players"),
    "foggy_canvas":         ("foggy_count",                 "foggy_players"),
    "cursor_hijack":        ("hijack_pair_count",           "hijack_pairs"),
    "blind_drawer":         ("blind_drawers",               "blind_drawers"),
    "icy_canvas":           ("icy_canvas_count",            "icy_canvas_players"),
    "inverse_mode":         ("inverse_canva_count",         "inverse_canva_players"),
    "mirror_only":          ("mirror_only_count",           "mirror_only_players"),
    "monochrome_decay":     ("monochrome_decay_count",      "monochrome_decay_players"),
    "scroll_wheel_brush":   ("scroll_wheel_brush_count",    "scroll_wheel_brush_players"),
    "tremor_hand":          ("tremor_hand_count",           "tremor_hand_players"),
    "turbo_mode":           ("turbo_mode_count",            "turbo_mode_players"),
    "snail_curse":          ("snail_curse_count",           "snail_positions"),
}

# default counts if settings key is missing or None
TWIST_DEFAULT_COUNTS = {
    "stroke_thief":         2,
    "pixelated_vision":     1,
    "foggy_canvas":         1,
    "cursor_hijack":        None,   # None means pair everyone
    "blind_drawer":         1,
    "icy_canvas":           1,
    "inverse_mode":         1,
    "mirror_only":          1,
    "monochrome_decay":     1,
    "scroll_wheel_brush":   1,
    "tremor_hand":          1,
    "turbo_mode":           1,
    "snail_curse":          1,
}


async def get_twist_count(room_id: str, twist_id: str) -> int:
    """
    Given a room and a twist_id, returns how many players
    should be affected by that twist this round.

    For cursor_hijack specifically, None in settings means
    pair everyone — so returns len(players) // 2.

    O(1) lookup — just a dict index and one settings read.
    """
    room = get_room(room_id)
    if not room:
        return 1

    mapping = TWIST_COUNT_MAP.get(twist_id)
    if not mapping:
        return 1  # twist not in map, single target default

    settings_key, _ = mapping
    raw = room["settings"].get(settings_key)

    # None means "pair everyone" (cursor hijack default)
    if raw is None:
        default = TWIST_DEFAULT_COUNTS.get(twist_id, 1)
        if default is None:
            return len(room["players"]) // 2
        return default

    player_count = len(room["players"])
    # cap at player count so you never assign more targets than exist
    return min(int(raw), player_count)


async def get_twist_state_key(twist_id: str) -> str | None:
    """
    Given a twist_id returns the room dict key where
    assigned players for that twist are stored.
    Used by assign_individual_twists to know where to write results.
    """
    mapping = TWIST_COUNT_MAP.get(twist_id)
    if not mapping:
        return None
    _, state_key = mapping
    return state_key

async def count_internal_conflicts(twist_id: str, selected: list[str]) -> int:
    """
    Count how many twist in the selected list conflict with this twist 
    This tells How much damange removing this twist will save. 
    High = more conflicting = better to remove.
    """
    conflicts = CONFLICTS.get(twist_id,[])
    if conflict == ["*"]:
        return 0 # jury or narrate own the whole round 
    # do the sum
    return sum(1 for t in selected if t in conflicts)


async def resolve_conflicts(selectd_ids: list[str], room_id: str) -> list[str]:
    """
    Resolve the conflicts by repeating the twist with most conflicts until no conflict is left 
    find subtitue for the ones getting removed
    """
    room = get_room(room_id)
    if not room: return selected_ids
    working = list(selected_ids)
    used = set(selected_ids)
    for t in used: # using the set for speed because this part insint that speedy  
        if t in ("jury_round", "narrate_dont_draw"):
            return [t]
    max_passes = 10  # safety limit
    passes = 0
    while passes < max_passes:
        # find all conflicting pairs in current working list
        conflicting = set()
        for i, t in enumerate(working):
            twist_conflicts = CONFLICTS.get(t, [])
            if twist_conflicts == ["*"]:
                continue
            for other in working:
                if other != t and other in twist_conflicts:
                    conflicting.add(t)

        if not conflicting:
            break  # clean, no conflicts

        # find which conflicting twist has the most conflicts within working list
        worst = max(
            conflicting,
            key=lambda t: count_internal_conflicts(t, working)
        )

        # remove it and substitute
        working.remove(worst)
        substitute = await find_substitute(
            blocked=set(CONFLICTS.get(worst, [])) | used,
            used=used,
            intensity=intensity,
            working=working
        )
        if substitute:
            working.append(substitute)
            used.add(substitute)

        passes += 1

    return working

    
async def find_substitute(
    blocked: set,
    used: set,
    intensity: str,
    working: list[str]
) -> str | None:
    """
    Find a random twist that:
    - is not blocked by any conflict
    - is not already used or in the working list
    - matches the intensity level
    - does not conflict with anything currently in working list
    """
    if intensity == "mild":
        pool = MILD
    elif intensity == "chaos":
        pool = {**MILD, **CHAOS}
    else:
        pool = TWIST_REGISTER

    candidates = []
    for twist_id in pool:
        if twist_id in blocked:
            continue
        if twist_id in used:
            continue
        if twist_id in ("jury_round", "narrate_dont_draw"):
            continue
        # check it doesnt conflict with anything already in working list
        twist_conflicts = CONFLICTS.get(twist_id, [])
        if any(w in twist_conflicts for w in working):
            continue
        candidates.append(twist_id)

    if not candidates:
        return None

    return random.choice(candidates)

async def select_twist_for_round(room_id: str):
    """
    Gets a random twist for the specific round in a room
    Returns: list of twist id or none if room not found
    """
    room = get_room(room_id)
    if not room: 
        return None
    intensity = room["settings"]["twist_intensity"]
    # right now i just made it a dict and then converting twists to list here 
    # later i will switch to only list 
    if intensity == "mild":
        twist = random.choice(list(MILD.values()))
        # no check need in mild because only 1 twist
        return twist['id']
    
    if intensity == "chaos":
        # 2 chaos 1 hell 
        twistC = random.sample(list(CHAOS.values()),2)
        twistH = random.sample(list(PURE_HELL.values()),1)[0]['id']
        T = [t['id'] for t in twistC] + twistH
        CleanT = await resolve_conflicts(T)
        return CleanT
    if intensity == "pure_hell":
        # 3 hell, and 2 random from twist registry 
        hell = random.sample(list(PURE_HELL.values()), 3)

        LOCAL_TS = copy.deepcopy(TWIST_REGISTER) 
        #avoid getting the ones already gotten at the same time getting the id of the twists gotten
        hell_twist = []
        for twist in hell:
            id = twist['id']
            hell_twist.append(id)
            LOCAL_TS.pop(id)   
        R = random.sample(list(LOCAL_TS.values()),2)
        t = [r['id'] for r in R] + hell_twist
        CleanT = await resolve_conflicts(t)
        return CleanT 
    
async def assign_individual_twists(room_id: str, active_twist_ids) -> dict :
    room = get_room(room_id)

    assignments = {}
    drawers_sid = room['current_drawer_sid']
    guessers_sid = [player['sid'] for player in room['players'].values() if player['sid'] not in drawers]
    for twist in active_twist_ids:
        twist_id = twist
        twist_target = TWIST_REGISTERY[twist]
        if twist_target == "drawer":
            
            number_of_affected = get_twist_count(room_id, twist_id)
            target = random.sample(drawers_sid, min(count, len(drawers_sid)))

        elif twist_target == "guesser":
            no_of_affected = get_twist_count(room_id, twist_id)
            targets = random.sample(no_of_affected, min(count, len(guessers_sid)))
             
        elif twist_target == "random":

            no_of_affected = get_twist_count(room_id, twist_id)
            targets = random.sample(player_sids, min(count, len(player_sids)))
        else: continue 

        assignments[twist_id] = targets
    return assignments

async def run_cursor_swap_roulette(sio, room_id: str) -> None:
    room = get_room(room_id)
    players_sids = list(room['players'].keys())
    number_to_be_notified = max(1, len(players_sids) // 3)
    # these players will be notified
    notified_sid = random.sample(players_sids, number_to_be_notified)
    # now shuffle them, then who will get who's 
    random.shuffle(players_sids)
    # warn sids
    for sid in notified_sid:

        await sio.emit("twist_warning", {
            "twist": "cursor_swap_roulette",
            "message": "Cursor swap incoming in 3 seconds...",
            "countdown": 3
        }, to=sid)

    await asyncio.sleep(3)

    prev = None
    for index, sid in enumerate(players_sids):
        #using out of index error as a way to know the last one
        try:
            await sio.emit("cursor_swap_start", {
                "your_new_canvas": players[(index+1)]},
                to=sid
            )
        except IndexError:
            await sio.emit("cursor_swap_start", {
                "your_new_canvas": players_sids[0]},
                to=sid
            )
    await asyncio.sleep(10)

    await sio.emit("cursor_swap_end", {}, room=room_id)

async def run_rewind(sio, room_id):
    room = await get_room(room_id)
    if not room:
        return None
    now = time.time()
    recent_strokes = [stroke for stroke in room['stroke_log'] 
                      if now - stroke['timestamp'] <= 15]
    
    await sio.emit("rewind_start", {
        "strokes": recent_strokes,
        "speed_multiplier": 2
    }, room= room_id)
    await asyncio.sleep(7.5)
    await sio.emit("rewind_end", {}, room=room_id)
# todo later, confusion in this
# later comment, finaled on behvaiour, shake with a delay when the user starts drawing for a duration 
# and then stop, did use stop when user because they need to be able to consequences of thier actions
async def run_earthquake(sio, room_id, drawer_sid):
    while room["earthquake_active"]:
        await room["stroke_start_event"].wait()
        room["stroke_start_event"].clear()

        if not room["earthquake_active"]:
            break

        # small delay before the timer starts
        await asyncio.sleep(random.uniform(0.5, 1.5))

        shake_duration = random.randint(1, 10)

        await sio.emit("earthquake_start", {
            "intensity": random.randint(3, 8),
            "duration": shake_duration
        }, to=drawer_sid)

        await asyncio.sleep(shake_anim_duration)
        await sio.emit("earthquake_end", {}, to=drawer_sid)
# this is ai gen, clearly mentioning before someone grabs my neck 
async def run_stroke_thier_assignment(sio, room_id) -> None:
    
    room = get_room(room_id)
    if not room:
        return

    player_sids = list(room["players"].keys())
    configured = int(room["settings"].get("thief_count", 2))
    # clamp to 1..4 and ensure at least one non-thief exists
    max_allowed = max(1, min(4, len(player_sids) - 1))
    thief_count = max(1, min(configured, max_allowed))
    thieves = random.sample(player_sids, thief_count)
    room["thieves"] = thieves

    for sid in thieves:
        await sio.emit("you_are_thief", {
            "message": "You are a Stroke Thief. Click 'Steal' to take a stroke from someone.",
            "targets": [s for s in player_sids if s != sid]
        }, to=sid)

async def process_steal_request(sio, room_id, thief_sid, target_sid):
    room = get_room(room_id)
    if not room or thief_sid not in room["thieves"]:
        return

    target_strokes = [s for s in room["stroke_log"] if s["sid"] == target_sid]
    if not target_strokes:
        return

    stolen = random.choice(target_strokes)
    room["stroke_log"].remove(stolen)

    # Track stolen strokes for post-round reveal
    if thief_sid not in room["stolen_strokes"]:
        room["stolen_strokes"][thief_sid] = []
    room["stolen_strokes"][thief_sid].append(stolen["stroke"])

    # Tell target their stroke is gone
    await sio.emit("stroke_stolen", {
        "stroke_id": stolen["stroke"].get("id"),
    }, to=target_sid)

    # Send stroke to thief's canvas
    await sio.emit("receive_stolen_stroke", {
        "stroke": stolen["stroke"],
        "from_player": room["players"].get(target_sid, {}).get("name", "someone")
    }, to=thief_sid)

# somewhwre to enforce that 
async def run_cursor_hijack(sio, room_id):
    room = await get_room(room_id)

    if not room: 
        return None

    players = list(room['players'].keys())

    no_of_hijackers = room['settings']['hijack_pair_count']
    total = random.sample(players, no_of_hijackers*2)
    half = len(total) // 2

    hijackers = total[:half]
    victims = total[half:]

    for (controller, victim) in zip(hijackers, victims):
        room["hijack_pairs"][controller] = victim
        await sio.emit("hijack_start", {
            "victim_sid": victim,
            "duration": 20
        }, to=controller)
        await sio.emit("hijack_victim_notice", {
            "message": "Your cursor has been hijacked. You can do nothing.",
            "duration": 20
        }, to=victim)

    await asyncio.sleep(20)
    room["hijack_pairs"] = {}
    await sio.emit("hijack_end", {}, room=room_id)
# if anyone is still unclear, no = number and non is for the actualy negative sense

async def run_snail_curse(sio, room_id):
    room = await get_room(room_id)
    drawers = room['current_drawer_sid']
    if type(drawer) == str or len(drawer) == 1:
        sid = drawers[0] if len(drawers) == 1 else drawers
        await sio.emit("snail_spawn", {
            "speed": 50, # px per second
            "follows_stroke": True, # can also not follow the stroke and move on a direct line to user is user not drawing
        }, to = sid)
    else:
        number_of_cursed = room['settings']['snail_curse_count']
        cursed = random.sample(drawer, number_of_cursed)
        for sid in drawers:
            await sio.emit("snail_spawn", {
            "speed": 50, # px per second
            "follows_stroke": True, # can also not follow the stroke and move on a direct line to user is user not drawing
        }, to = sid)

async def run_zoom_trap(sio, room_id: str) -> None:
    room = await get_room(room_id)
    _ = room['settings']['current_drawer_sid']
    drawers = [_] if type(_) == str else _
    drawers = random.sample(drawers, room['settings']['zoom_trap_count'])
    zoom = random.choice([0.25, 3])
    payload = {
        "zoom": zoom,
        "duration": 12
    }
    if zoom < 1:
        payload["region"] = {
            "x": random.randint(0, 600),
            "y": random.randint(0, 400),
            "scale": 3
        }
    for drawer_sid in drawers:
        await sio.emit("zoom_trap_start", payload, to=drawer_sid)
    await asyncio.sleep(12)
    for drawer_sid in drawers:
        await sio.emit("zoom_trap_end", {}, to=drawer_sid)

async def check_hot_and_cold(sio, room_id: str) -> None:
    """
    Hot and Cold logic.
    - Every 10 seconds, find the closest current guess to the answer.
    - Compare to previous closest guess.
    - Emit 'warmer' or 'colder' to drawer.
    Called as a looping task during the drawing phase.
    Uses simple character-level similarity (not semantic — intentional).
    """
    room = get_room(room_id)
    if not room or not room["current_word"]:
        return

    target = room["current_word"].lower()
    prev_best = 1.0

    while room["state"] == "drawing":
        await asyncio.sleep(10)

        correct_guesses = [g["guess"].lower() for g in room["guesses"] if not g["correct"]]
        if not correct_guesses:
            continue

        # Simple similarity: count matching characters at same position
        def similarity(a, b):
            return sum(c1 == c2 for c1, c2 in zip(a, b)) / max(len(a), len(b))

        best = max(similarity(target, g) for g in correct_guesses)
        direction = "warmer" if best > prev_best else "colder"
        prev_best = best

        drawer_sid = room["current_drawer_sid"]
        if drawer_sid:
            # send to every drawer
            drawer_sid = [drawer_sid] if type(drawer_sid) == str else drawer_sid 

            for drawer_id in drawer_sid:
                await sio.emit("hot_cold_update", {
                    "direction": direction
                }, to=drawer_id)
# changed to that the traitor has to find the word while other guessers at the end vote who the traitor was
async def run_imposter_assignment(sio, room_id, real_word, fake_category):
    room = await get_room(room_id)
    drawer = room['current_drawer_sid']
    drawers = [drawer] if type(drawer) == str else drawer
    guessers = [s for s in room['players'].keys() if s not in drawers]


    if len(drawers) > 1:
        # more than one drawer, keep the initial twist 
        imposter_sid = random.choice(drawers)
        if guessers:
            for sid in guessers:
                await sio.emit({
                    "your_word": real_word,
                    "is_imposter": False,
                    "message": "Find out who the imposter is."
                }, to=sid)

        for sid in drawers:
            if sid == imposter_sid:
                await sio.emit({
                    "your_word": fake_category,
                    "is_imposter": True,
                    "message": "You're the imposter. Draw convincingly without the real word."
                }, to=sid)
            else:
                await sio.emit({
                    "your_word": real_word,
                    "is_imposter": False,
                    "message": "Try to find out who the imposter is."
                }, to=sid)
    else:
        guessers = [s for s in room['players'].keys() if s not in drawers]
        # send to guesser
        await sio.emit("your_word", {
                    "word": real_word,
                    "is_imposter": False
                }, to=drawers[0])
        traitor = random.choice(guessers)
        
        for sid in guessers:
            if sid == traitor:
                await sio.emit({
                    "word": fake_category,
                    "is_imposter": True,
                    "message": "Your are the imposter, try to blend in with rest of guessers."
                }, to=sid)
            else:
                await sio.emit({
                    "word": real_word,
                    "is_imposter": False,
                    "message": "Find out who the imposter is."
                }, to=sid)

async def run_ten_strokes(sio, room_id: str) -> None:
    room = get_room(room_id)
    if not room:
        return

    drawer = room['current_drawer_sid']
    drawers = [drawer] if type(drawer) == str else drawer

    if len(drawers) > 1:
        count = room['settings'].get('ten_strokes_count', 1)
        count = min(count, len(drawers))
        targets = random.sample(drawers, count)
    else:
        targets = drawers

    for sid in targets:
        await sio.emit("ten_strokes_start", {
            "max_strokes": 10,
            "message": "You have exactly 10 strokes. No undo. Canvas locks after stroke 10."
        }, to=sid)

async def run_foggy_canvas(sio, room_id: str) -> None:
    room = get_room(room_id)
    if not room:
        return

    drawer = room['current_drawer_sid']
    drawers = [drawer] if type(drawer) == str else drawer
    guessers = [s for s in room['players'].keys() if s not in drawers]

    settings = room['settings']
    foggy_count = settings.get("foggy_count", 1)
    foggy_count = min(foggy_count, len(guessers))

    targets = random.sample(guessers, foggy_count)

    for sid in targets:
        await sio.emit("foggy_canvas_start", {
            "message": "Your view of the canvas is heavily fogged."
        }, to=sid)


async def run_pixelated_vision(sio, room_id: str) -> None:
    room = get_room(room_id)
    if not room:
        return

    drawer = room['current_drawer_sid']
    drawers = [drawer] if type(drawer) == str else drawer
    guessers = [s for s in room['players'].keys() if s not in drawers]

    settings = room['settings']
    pixelated_count = settings.get("pixelated_count", 1)
    pixelated_count = min(pixelated_count, len(guessers))

    targets = random.sample(guessers, pixelated_count)

    for sid in targets:
        await sio.emit("pixelated_vision_start", {
            "message": "Your view of the canvas is heavily pixelated."
        }, to=sid)

async def run_turbo_mode(sio, room_id):
    room = await get_room(room_id)
    
    drawers = room['current_drawer_sid']
    drawers = [drawers] if type(drawers) == str else drawers

    affected_count = min(len(drawers), room['settings']['turbo_mode_count']) 
    affected_drawers = random.sample(drawers, affected_count)

    while "turbo_mode" in room['active_twists']:
        for sid in affected_drawers:
            await sio.emit("turbo_mode_update", {"twist": "turbo_mode",
                            "speed": random.choice([0.1, 0.5, 3, 4]),
                            "message": "Your speed has been changed, enjoy!"}, to=sid)
        await asyncio.sleep(10)

async def run_drunk_cursor(sio, room_id):
    room = await get_room(room_id)
    if not room:
        return

    drawer = room['current_drawer_sid']
    drawers = [drawer] if type(drawer) == str else drawer
    drawers = min(len(drawers), room['drunk_cursor_count'])
    for sid in drawers:
        await sio.emit("drunk_cursor_start", {
            "twist": "drunk_cursor",
            "drift_min": 20,
            "drift_max": 60,
            "message": "Your cursor drifts randomly with every stroke."
        }, to=sid)


async def run_icy_canvas(sio, room_id):
    room = await get_room(room_id)
    if not room:
        return

    drawer = room['current_drawer_sid']
    drawers = [drawer] if type(drawer) == str else drawer

    settings = room['settings']
    icy_count = settings.get("icy_canvas_count", 1)
    icy_count = min(icy_count, len(drawers))

    affected_drawers = random.sample(drawers, icy_count)

    for sid in affected_drawers:
        await sio.emit("icy_canvas_start", {
            "twist": "icy_canvas",
            "deceleration": 0.92,
            "message": "Your cursor slides on ice and won't stop where you want."
        }, to=sid)

async def run_tremor_hand(sio, room_id):
    room = await get_room(room_id)
    if not room:
        return

    drawer = room['current_drawer_sid']
    drawers = [drawer] if type(drawer) == str else drawer

    settings = room['settings']
    tremor_count = settings.get("tremor_hand_count", 1)
    tremor_count = min(tremor_count, len(drawers))

    affected_drawers = random.sample(drawers, tremor_count)

    for sid in affected_drawers:
        await sio.emit("tremor_hand_start", {
            "twist": "tremor_hand",
            "jitter_amplitude": 3,
            "jitter_frequency": 30,
            "message": "Your hand is trembling — every stroke jitters."
        }, to=sid)

async def run_mirror_only(sio, room_id):
    room = await get_room(room_id)
    if not room:
        return

    drawer = room['current_drawer_sid']
    drawers = [drawer] if type(drawer) == str else drawer

    settings = room['settings']
    mirror_count = settings.get("mirror_only_count", 1)
    mirror_count = min(mirror_count, len(drawers))

    affected_drawers = random.sample(drawers, mirror_count)

    for sid in affected_drawers:
        await sio.emit("mirror_only_start", {
            "twist": "mirror_only",
            "axis": "horizontal",
            "message": "Your view of the canvas is mirrored."
        }, to=sid)

async def run_scroll_wheel_brush(sio, room_id):
    room = await get_room(room_id)
    if not room:
        return

    drawer = room['current_drawer_sid']
    drawers = [drawer] if type(drawer) == str else drawer

    settings = room['settings']
    scroll_count = settings.get("scroll_wheel_brush_count", 1)
    scroll_count = min(scroll_count, len(drawers))

    affected_drawers = random.sample(drawers, scroll_count)

    while "scroll_wheel_brush" in room["active_twists"]:
        for sid in affected_drawers:
            await sio.emit("scroll_wheel_brush_update", {
                "twist": "scroll_wheel_brush",
                "brush_size": random.randint(1, 50),
                "message": "Your brush size just changed on its own."
            }, to=sid)
        await asyncio.sleep(7)

async def run_inverse_mode(sio, room_id):
    room = await get_room(room_id)
    if not room:
        return

    drawer = room['current_drawer_sid']
    drawers = [drawer] if type(drawer) == str else drawer

    settings = room['settings']
    inverse_count = settings.get("inverse_canva_count", 1)
    inverse_count = min(inverse_count, len(drawers))

    affected_drawers = random.sample(drawers, inverse_count)

    for sid in affected_drawers:
        await sio.emit("inverse_mode_warning", {
                "twist": "inverse_mode",
                "message": "Axes will invert in 3 seconds...",
                "countdown": 3
            }, to=sid)

    await asyncio.sleep(3)
    for sid in affected_drawers:
        await sio.emit("inverse_mode_start", {
                "twist": "inverse_mode",
                "duration": 20,
                "message": "Both axes are now inverted!"
            }, to=sid)

async def run_monochrome_decay(sio, room_id):
    room = await get_room(room_id)
    if not room:
        return

    drawer = room['current_drawer_sid']
    drawers = [drawer] if type(drawer) == str else drawer

    settings = room['settings']
    decay_count = settings.get("monochrome_decay_count", 1)
    decay_count = min(decay_count, len(drawers))

    affected_drawers = random.sample(drawers, decay_count)

    for sid in affected_drawers:
        await sio.emit("monochrome_decay_start", {
            "twist": "monochrome_decay",
            "message": "Your color vision is starting to fade..."
        }, to=sid)

    channels = ["red", "green", "blue"]

    for channel in channels:
        await asyncio.sleep(15)
        for sid in affected_drawers:
            await sio.emit("monochrome_decay_channel_drop", {
                "twist": "monochrome_decay",
                "channel": channel,
                "message": f"You can no longer see the {channel} channel."
            }, to=sid)

async def run_color_chaos(sio, room_id):
    room = await get_room(room_id)
    if not room:
        return

    drawer = room['current_drawer_sid']
    drawers = [drawer] if type(drawer) == str else drawer

    for sid in drawers:
        await sio.emit("color_chaos_start", {
            "twist": "color_chaos",
            "message": "Your color picker is disabled — your brush color now changes on its own for 5 seconds."
        }, to=sid)

    while "color_chaos" in room["active_twists"]:
        for sid in drawers:
            await sio.emit("color_chaos_update", {
                "twist": "color_chaos",
                "color": f"#{random.randint(0, 0xFFFFFF):06x}"
            }, to=sid)
        await asyncio.sleep(5)

async def run_fake_word(sio, room_id, real_word, fake_word):
    room = get_room(room_id)
    if not room:
        return

    drawer = room['current_drawer_sid']
    drawers = [drawer] if type(drawer) == str else drawer
    guessers = [s for s in room['players'].keys() if s not in drawers]

    for sid in drawers:
        await sio.emit("your_word", {
            "real_word": real_word,
            "fake_word": fake_word,
            "message": "Draw the real word, but guessers may be misled by a fake word."
        }, to=sid)

    random.shuffle(guessers)
    half = len(guessers) // 2
    real_group = guessers[:half]
    fake_group = guessers[half:]

    for sid in real_group:
        await sio.emit("your_word", {
            "word": real_word,
            "message": "Guess what's being drawn."
        }, to=sid)

    for sid in fake_group:
        await sio.emit("your_word", {
            "word": fake_word,
            "message": "Guess what's being drawn."
        }, to=sid)

async def run_reverse_round(sio, room_id):
    room = get_room(room_id)
    if not room:
        return

    await sio.emit("reverse_round_start", {
        "twist": "reverse_round",
        "message": "Draw your word as badly as possible — on purpose!"
    }, room=room_id)


async def run_reverse_round_voting(sio, room_id):
    room = get_room(room_id)
    if not room:
        return

    await sio.emit("reverse_round_vote", {
        "twist": "reverse_round",
        "message": "Vote for the best sabotage technique!"
    }, room=room_id)

async def handle_emoji_reaction(sio, room_id, spectator_sid):
    room = get_room(room_id)
    if not room:
        return

    now = time.time()
    timestamps = room.setdefault("emoji_timestamps", [])
    timestamps.append(now)
    room["emoji_timestamps"] = [t for t in timestamps if now - t <= 3]

    if len(room["emoji_timestamps"]) >= 5:
        room["emoji_timestamps"] = []
        await run_audience_takeover(sio, room_id)


async def run_audience_takeover(sio, room_id):
    room = get_room(room_id)
    if not room:
        return

    player_sids = list(room['players'].keys())
    target_sid = random.choice(player_sids)

    await sio.emit("audience_takeover_start", {
        "twist": "audience_takeover",
        "target": target_sid,
        "duration": 20,
        "message": "The crowd has flipped a canvas!"
    }, room=room_id)

    await asyncio.sleep(20)

    await sio.emit("audience_takeover_end", {
        "target": target_sid
    }, room=room_id)
async def run_silent_pivot(sio, room_id, new_word):
    room = get_room(room_id)
    if not room:
        return

    drawer = room['current_drawer_sid']
    drawers = [drawer] if type(drawer) == str else drawer

    room["current_word"] = new_word

    for sid in drawers:
        await sio.emit("silent_pivot_flash", {
            "twist": "silent_pivot",
            "new_word": new_word,
            "message": "The word has changed!"
        }, to=sid)

async def run_elimination_round(sio, room_id):
    room = get_room(room_id)
    if not room:
        return

    try:
        eliminated = room['eliminated_players']
    except KeyError:
        room['eliminated_players'] = []
        eliminated = room['eliminated_players']

    try:
        stash = room['eliminated_player_data']
    except KeyError:
        room['eliminated_player_data'] = {}
        stash = room['eliminated_player_data']

    drawer = room['current_drawer_sid']
    drawers = [drawer] if type(drawer) == str else drawer

    # candidates = this round's drawers, minus anyone already eliminated
    candidates = [sid for sid in drawers if sid not in eliminated]
    if not candidates:
        return

    # voters: drawers themselves until 2+ eliminated, then eliminated players take over
    if len(eliminated) >= 2:
        voters = eliminated
    else:
        voters = drawers

    votes = room.get("elimination_votes", {})
    vote_counts = {}
    for voter, accused in votes.items():
        if voter in voters and accused in candidates:
            vote_counts[accused] = vote_counts.get(accused, 0) + 1

    if vote_counts:
        target_sid = max(vote_counts, key=vote_counts.get)
    else:
        # fallback: fewest correct guesses gained this round among candidates
        snapshot = room.get("elimination_snapshot", {})
        round_gains = {
            sid: room['players'][sid]['correct_guesses'] - snapshot.get(sid, 0)
            for sid in candidates
        }
        target_sid = min(round_gains, key=round_gains.get)

    room["elimination_votes"] = {}

    stash[target_sid] = room['players'].pop(target_sid)
    eliminated.append(target_sid)

    await sio.emit("elimination_round_result", {
        "twist": "elimination_round",
        "eliminated": target_sid,
        "message": "This player has been eliminated for the round!"
    }, room=room_id)


async def restore_eliminated_players(room_id):
    room = get_room(room_id)
    if not room:
        return

    try:
        stash = room['eliminated_player_data']
    except KeyError:
        return

    for sid, player_data in stash.items():
        room['players'][sid] = player_data

    room['eliminated_players'] = []
    room['eliminated_player_data'] = {}

async def run_traitor_vote(sio, room_id):
    room = get_room(room_id)
    if not room:
        return

    votes = room.get("traitor_votes", {})
    if not votes:
        return

    vote_counts = {}
    for voter, accused in votes.items():
        vote_counts[accused] = vote_counts.get(accused, 0) + 1

    most_accused = max(vote_counts, key=vote_counts.get)

    rounds_played = room.get("current_round", 1)
    avg_score_per_round = room["players"][most_accused]["score"] / rounds_played
    penalty = round(2 * avg_score_per_round)

    room["players"][most_accused]["score"] -= penalty

    await sio.emit("traitor_vote_result", {
        "twist": "traitor_vote",
        "accused": most_accused,
        "penalty": penalty,
        "message": "The crowd has spoken — points deducted!"
    }, room=room_id)

    room["traitor_votes"] = {}

async def run_blind_drawer(sio, room_id):
    room = await get_room(room_id)
    if not room:
        return

    drawer = room['current_drawer_sid']
    drawers = [drawer] if type(drawer) == str else drawer

    blind_count = room['settings'].get('blind_drawers', 1)
    blind_count = min(blind_count, len(drawers))

    affected_drawers = random.sample(drawers, blind_count)
    room['blind_drawers'] = affected_drawers

    for sid in affected_drawers:
        await sio.emit("blind_drawer_start", {
            "twist": "blind_drawer",
            "message": "You are drawing blind — your canvas is hidden from you."
        }, to=sid)

async def run_jury_round(sio, room_id):
    room = get_room(room_id)
    if not room:
        return

    previous_drawings = room.get("previous_drawing", {})
    previous_word = room.get("previous_word")

    if not previous_drawings or not previous_word:
        return

    await sio.emit("jury_round_start", {
        "twist": "jury_round",
        "word": previous_word,
        "drawings": previous_drawings,
        "vote_duration": 30,
        "message": f"Vote for the best drawing of '{previous_word}' from last round!"
    }, room=room_id)

    await asyncio.sleep(30)

    votes = room.get("jury_votes", {})
    vote_counts = {}
    for voter, voted_for in votes.items():
        if voted_for in previous_drawings:
            vote_counts[voted_for] = vote_counts.get(voted_for, 0) + 1

    room["jury_votes"] = {}

    if not vote_counts:
        await sio.emit("jury_round_result", {
            "twist": "jury_round",
            "message": "No votes cast — no points awarded.",
            "results": {}
        }, room=room_id)
        return

    winner_sid = max(vote_counts, key=vote_counts.get)
    loser_sid = min(vote_counts, key=vote_counts.get)

    BONUS = 50
    PENALTY = 20

    if winner_sid in room["players"]:
        room["players"][winner_sid]["score"] += BONUS

    if loser_sid in room["players"] and loser_sid != winner_sid:
        room["players"][loser_sid]["score"] = max(0, room["players"][loser_sid]["score"] - PENALTY)

    await sio.emit("jury_round_result", {
        "twist": "jury_round",
        "winner": winner_sid,
        "loser": loser_sid,
        "vote_counts": vote_counts,
        "bonus": BONUS,
        "penalty": PENALTY,
        "message": "The jury has spoken!"
    }, room=room_id)

async def run_copycat(sio, room_id):
    room = get_room(room_id)
    if not room:
        return

    reference_sid = room.get("last_round_winner_sid")
    reference_drawing = room.get("previous_drawing", {}).get(reference_sid)
    previous_word = room.get("previous_word")

    if not reference_drawing or not previous_word:
        return

    await sio.emit("copycat_start", {
        "twist": "copycat",
        "reference_drawing": reference_drawing,
        "word": previous_word,
        "message": f"Copy the style of last round's winner! Draw '{previous_word}' in their style."
    }, room=room_id)

    await asyncio.sleep(room["settings"].get("draw_time", 80))

    await sio.emit("copycat_vote", {
        "twist": "copycat",
        "drawings": room.get("previous_drawing", {}),
        "vote_duration": 30,
        "message": "Vote for the best copycat!"
    }, room=room_id)

    await asyncio.sleep(30)

    votes = room.get("copycat_votes", {})
    vote_counts = {}
    for voter, voted_for in votes.items():
        vote_counts[voted_for] = vote_counts.get(voted_for, 0) + 1

    room["copycat_votes"] = {}

    if not vote_counts:
        await sio.emit("copycat_result", {
            "twist": "copycat",
            "message": "No votes cast.",
            "results": {}
        }, room=room_id)
        return

    winner_sid = max(vote_counts, key=vote_counts.get)
    loser_sid = min(vote_counts, key=vote_counts.get)

    BONUS = 50
    PENALTY = 20

    if winner_sid in room["players"]:
        room["players"][winner_sid]["score"] += BONUS

    if loser_sid in room["players"] and loser_sid != winner_sid:
        room["players"][loser_sid]["score"] = max(0, room["players"][loser_sid]["score"] - PENALTY)

    await sio.emit("copycat_result", {
        "twist": "copycat",
        "winner": winner_sid,
        "loser": loser_sid,
        "vote_counts": vote_counts,
        "bonus": BONUS,
        "penalty": PENALTY,
        "message": "The votes are in!"
    }, room=room_id)

async def run_ghost_round(sio, room_id):
    room = get_room(room_id)
    if not room:
        return

    drawer = room["current_drawer_sid"]
    drawers = [drawer] if type(drawer) == str else drawer
    ghost_sid = random.choice(drawers)
    room["ghost_sid"] = ghost_sid

    for sid, player in room["players"].items():
        if sid == ghost_sid:
            await sio.emit("ghost_round_start", {
                "twist": "ghost_round",
                "role": "ghost",
                "word": room["current_word"],
                "message": "You are the ghost. Draw normally — no one knows it's you."
            }, to=sid)
        else:
            await sio.emit("ghost_round_start", {
                "twist": "ghost_round",
                "role": "guesser",
                "players": [
                    {"sid": s, "name": p["name"]}
                    for s, p in room["players"].items()
                    if s != ghost_sid
                ],
                "message": "One player is a ghost — guess the word AND who the ghost is!"
            }, to=sid)

async def resolve_ghost_round(sio, room_id):
    room = get_room(room_id)
    if not room:
        return

    ghost_sid = room.get("ghost_sid")
    if not ghost_sid:
        return

    identity_votes = room.get("ghost_identity_votes", {})
    correct_identifiers = [
        sid for sid, guessed in identity_votes.items()
        if guessed == ghost_sid and sid != ghost_sid
    ]
    identified = len(correct_identifiers) > 0

    IDENTIFIER_BONUS = 40
    GHOST_UNIDENTIFIED_BONUS = 60
    GHOST_WORD_BONUS = 30

    for sid in correct_identifiers:
        if sid in room["players"]:
            room["players"][sid]["score"] += IDENTIFIER_BONUS

    if not identified and ghost_sid in room["players"]:
        room["players"][ghost_sid]["score"] += GHOST_UNIDENTIFIED_BONUS

    word_guessed = room.get("ghost_word_reveal", False)
    if word_guessed and ghost_sid in room["players"]:
        room["players"][ghost_sid]["score"] += GHOST_WORD_BONUS

    room["ghost_identity_votes"] = {}
    room["ghost_word_reveal"] = False
    room["ghost_sid"] = None

    await sio.emit("ghost_round_result", {
        "twist": "ghost_round",
        "ghost_sid": ghost_sid,
        "identified": identified,
        "correct_identifiers": correct_identifiers,
        "word_guessed": word_guessed,
        "identifier_bonus": IDENTIFIER_BONUS if identified else 0,
        "ghost_unidentified_bonus": GHOST_UNIDENTIFIED_BONUS if not identified else 0,
        "ghost_word_bonus": GHOST_WORD_BONUS if word_guessed else 0,
        "message": "The ghost has been revealed!"
    }, room=room_id)
async def run_rotating_prompt(sio, room_id, word_bank):
    room = get_room(room_id)
    if not room:
        return

    all_players = list(room["players"].keys())

    if len(word_bank) < len(all_players):
        return

    words = random.sample(word_bank, len(all_players))
    rotating_words = dict(zip(all_players, words))
    room["rotating_words"] = rotating_words
    room["current_drawer_sid"] = all_players

    for sid, word in rotating_words.items():
        await sio.emit("rotating_prompt_start", {
            "twist": "rotating_prompt",
            "word": word,
            "message": "Everyone draws! You'll vote on who drew what after."
        }, to=sid)

async def resolve_rotating_prompt(sio, room_id):
    room = get_room(room_id)
    if not room:
        return

    rotating_words = room.get("rotating_words", {})
    votes = room.get("rotating_votes", {})

    if not rotating_words or not votes:
        return

    correct_per_voter = {}
    for voter_sid, guesses in votes.items():
        correct = sum(
            1 for drawing_sid, guessed_word in guesses.items()
            if rotating_words.get(drawing_sid) == guessed_word
        )
        correct_per_voter[voter_sid] = correct

    POINTS_PER_CORRECT = 20

    for sid, correct_count in correct_per_voter.items():
        if sid in room["players"] and correct_count > 0:
            room["players"][sid]["score"] += correct_count * POINTS_PER_CORRECT

    room["rotating_votes"] = {}
    room["rotating_words"] = {}

    await sio.emit("rotating_prompt_result", {
        "twist": "rotating_prompt",
        "correct_per_voter": correct_per_voter,
        "actual_words": rotating_words,
        "points_per_correct": POINTS_PER_CORRECT,
        "message": "Here's who drew what!"
    }, room=room_id)

async def run_narrate_dont_draw(sio, room_id):
    room = get_room(room_id)
    if not room:
        return

    all_players = list(room["players"].keys())
    if len(all_players) < 3:
        return

    selected = random.sample(all_players, 2)
    narrator_sid = selected[0]
    narrate_drawer_sid = selected[1]
    guessers = [s for s in all_players if s not in selected]

    room["narrator_sid"] = narrator_sid
    room["narrate_drawer_sid"] = narrate_drawer_sid
    room["current_drawer_sid"] = narrate_drawer_sid

    await sio.emit("narrate_dont_draw_start", {
        "twist": "narrate_dont_draw",
        "role": "narrator",
        "word": room["current_word"],
        "message": "You know the word — describe it to the drawer without saying it directly!"
    }, to=narrator_sid)

    await sio.emit("narrate_dont_draw_start", {
        "twist": "narrate_dont_draw",
        "role": "drawer",
        "message": "Listen to the narrator's clues and draw what they describe."
    }, to=narrate_drawer_sid)

    for sid in guessers:
        await sio.emit("narrate_dont_draw_start", {
            "twist": "narrate_dont_draw",
            "role": "guesser",
            "message": "Guess what's being drawn based on the narrator's clues!"
        }, to=sid)

async def handle_narrator_clue(sio, room_id, narrator_sid, clue):
    room = get_room(room_id)
    if not room:
        return

    if narrator_sid != room.get("narrator_sid"):
        return

    await sio.emit("narrator_clue", {
        "clue": clue,
    }, room=room_id)

async def resolve_narrate_dont_draw(sio, room_id, guesser_sid):
    room = get_room(room_id)
    if not room:
        return

    narrator_sid = room.get("narrator_sid")
    narrate_drawer_sid = room.get("narrate_drawer_sid")

    GUESSER_BONUS = 40
    NARRATOR_BONUS = 30
    DRAWER_BONUS = 30

    if guesser_sid in room["players"]:
        room["players"][guesser_sid]["score"] += GUESSER_BONUS
    if narrator_sid and narrator_sid in room["players"]:
        room["players"][narrator_sid]["score"] += NARRATOR_BONUS
    if narrate_drawer_sid and narrate_drawer_sid in room["players"]:
        room["players"][narrate_drawer_sid]["score"] += DRAWER_BONUS

    room["narrator_sid"] = None
    room["narrate_drawer_sid"] = None

    await sio.emit("narrate_dont_draw_result", {
        "twist": "narrate_dont_draw",
        "guesser": guesser_sid,
        "narrator": narrator_sid,
        "drawer": narrate_drawer_sid,
        "word": room["current_word"],
        "message": f"The word was '{room['current_word']}'!"
    }, room=room_id)

async def run_collective_canvas(sio, room_id):
    room = get_room(room_id)
    if not room:
        return

    all_players = list(room["players"].keys())
    room["current_drawer_sid"] = all_players

    await sio.emit("collective_canvas_start", {
        "twist": "collective_canvas",
        "word": room["current_word"],
        "message": "Everyone draws on the same canvas — good luck on keeping your sanity!"
    }, room=room_id)