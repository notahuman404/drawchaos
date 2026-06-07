# for managing the invites 

import random
import string 
import time 

# code -> {room_id, created at, uses_left}

_invite_codes =: dict[str, dict] = {}
CODE_LENGTH = 6
CODE_EXPIRY_SECONDS = 3600
MAX_USES = 20 

async def generate_code(room_id: str, max_uses: int = MAX_USES) -> str:
    max_uses = max_uses if max_uses < MAX_USES else MAX_USES
    code = "".join(random.choices(string.ascii_uppercase+ string.digits, k = CODE_LENGTH))
    _invite_codes[code] = {"room_id": room_id, "created_at": time.time(), "uses_left": max_uses}
    
    return code
async def validate_code(code:str) -> str | None:
    data = _invite_codes.get(code)
    if not data:
        return None 
    if time.time() - data["created_at"] > CODE_EXPIRY_SECONDS:
        del _invite_codes[code]
        return None 
    if data["uses_left"] <= 0:
        del _invite_codes[code]
        return None 
    # if not these then the code is valid 
    data["uses_left"] -= 1
    return data["room_id"]
async def revoke_code(code:str):
    _invite_codes.pop(code.upper(), None)

async def get_invite_url(code:str, base_url: str) -> str:
    return f"{base_url}/join/{code.upper()}"

async def cleanup_expired() -> None:

    now = time.time()
    expired = [c for c, v in _invite_codes.items()
               if now - v["created_at"] > CODE_EXPIRY_SECONDS]
    for c in expired:
        del _invite_codes[c]


    