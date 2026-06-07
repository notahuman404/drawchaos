# Just words organized by thier catecgoires(i will fix spelling later) 
# the twist engine and game engine both pull from here 
# if you wanna enjoy the game i would suggest not to look at these 
import random

EASY = ["cat", "dog", "sun", "house","tree", "car", "boat", "fish"
        "bird", "apple", "chair", "book", "phone", "shoe","hat", "cloud", 
        "moon", "star", "door", "clock", "mountain", "river", "school bag",
        "cup", "table", "pikachu", "mario", "ketchup"]

MEDIUM = ["elephant", "volcano", "bicycle", "lighthouse", "umbrella", "sandwich",
          "rainbow", "telescope", "penguin", "cactus", "submarine", "tornado", "pyramid",
          "astronaut", "dragon", "compass", "jellyfish", "escalator", "waterfall", "trampoline"]


    "democracy", "nostalgia", "photosynthesis", "gravity", "infinity",
    "procrastination", "ambiguous", "bureaucracy", "claustrophobia",
    "metamorphosis", "superstition", "thermodynamics", "apocalypse",
    "renaissance", "existential", "hallucination", "camouflage"
HARD = ["hippopotamus", "microscope", "saxophone", "chameleon", "parachute", "xylophone",
        "democracy", "nostalgia", "gravity", "procrastination", "ambiguous", "bureaucracy",
        "claustrophobia", "placebo effect", "camouflage", "hallucination"]

CURSED = ["You", "Monday", "Angry boss", "e=mc^2 prove", "meaning of 4th dimension",
          "conciousness", "wrong wifi password", "free will", "captcha", "Luck"]

async def get_word(difficulty = "medium"):
    pool = {
        "easy": EASY,
        "medium": MEDIUM,
        "hard": HARD,
        "cursed": CURSED
    }
    return random.choice(pool[difficulty])

async def get_word_choices(n:int = 3, # number of choices
                           difficulty:str = "medium"):
    pool = {
        "easy": EASY,
        "medium": MEDIUM,
        "hard": HARD,
        "cursed": CURSED
    }
    return random.sample(pool[difficulty], n)

def get_fake_word(real_word: str, difficulty: str = "medium") -> str:
    
    """
    Return a plausible-looking fake word for the Fake Word twist.
    The fake word must be from the same difficulty but not the real word.
    """
    #yup i wrote a doc for this, i know i am great
    pools = {"easy": EASY, "medium": MEDIUM, "hard": HARD, "cursed": CURSED}
    pool = [w for w in pools.get(difficulty, MEDIUM) if w != real_word]
    return random.choice(pool)
CATEGORY_MAP = {
    **{w: "animal" for w in ["cat", "dog", "fish", "bird", "elephant", "penguin", "jellyfish"]},
    **{w: "vehicle" for w in ["car", "boat", "bicycle", "submarine"]},
    **{w: "nature" for w in ["sun", "tree", "cloud", "moon", "star", "volcano", "rainbow", "tornado", "waterfall", "cactus", "snowflake"]},
    **{w: "object" for w in ["house", "chair", "book", "phone", "shoe", "hat", "door", "clock", "umbrella", "compass", "telescope", "trampoline", "lighthouse", "pyramid"]},
    **{w: "concept" for w in ["e=mc^2 prove", "meaning of 4th dimension", "conciousness", "wrong wifi password", "free will", "captcha", "luck",
                              "democracy", "nostalgia", "photosynthesis", "gravity", "infinity", "procrastination", "ambiguous", "bureaucracy",
                              "claustrophobia", "metamorphosis", "superstition", "thermodynamics", "apocalypse", "renaissance", "existential",
                              "hallucination", "camouflage"]},
    **{w: "character" for w in ["pikachu", "mario"]},
    **{w: "food" for w in ["apple", "ketchup", "sandwich"]},
    **{w: "place" for w in ["school bag"]},
    **{w: "person" for w in ["you", "monday", "angry boss"]},
}

def get_category(word="e=mc^2 prove"):
    word = word.strip().lower()
    return CATEGORY_MAP.get(word, "unknown")