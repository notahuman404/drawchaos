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
        pool = TWIST_REGISTRY

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

        LOCAL_TS = copy.deepcopy(TWIST_REGISTRY) 
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
    guessers_sid = [player['sid'] for player in room['players'] if player['sid'] not in drawers]
    for twist in active_twist_ids:
        twist_id = twist
        twist_target = TWIST_REGISTERY[twist]
        if twist_target = "drawer":
            
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
    players_sids = list(room['player'].keys())
    number_to_be_notified = max(1, len(players_sids) // 3)
    # these players will be notified
    notified_sid = random.sample(players_sids, number_to_be_notified)
    # now shuffle them, then who will get who's 
    players = random.shuffle(players_sids)

