# DrawChaos 🎨✨

> A real-time multiplayer drawing game where the only constant is chaos. Revolutionary game mechanics that transform every round into something completely different.

![Python](https://img.shields.io/badge/Python-3.9+-blue?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-Latest-009485?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

## Overview

DrawChaos is a real-time multiplayer drawing game built on a foundation of dynamic, unpredictable game modifiers called **Twists**. Unlike traditional drawing games with static mechanics, DrawChaos introduces layers of chaos that fundamentally alter gameplay each round—from stealing strokes to hijacking drawings to pixelating canvases.

Players draw, guess, and compete while adapting to ever-changing rules, creating a uniquely engaging and hilarious experience.

**Designed for:**
- Friends who want genuinely unpredictable gameplay
- Teams seeking creative competition
- Social gatherings that need genuine laughs
- PThe Twists: Where the Magic Happens ✨

DrawChaos's revolutionary differentiator is its **Twist System**—dynamic gameplay modifiers that activate each round:

| Twist | Effect |
|-------|--------|
| **Stroke Thief** | Players can reconstruct drawings by stealing opponent strokes mid-game |
| **Foggy Vision** | Canvas obscured with fog, revealing only partial drawings |
| **Pixelated Art** | All drawings converted to pixel-art style, hiding fine details |
| **Ghostly Mode** | Semi-transparent drawings force guessers to rely on intuition |
| **Imposter Syndrome** | One player secretly draws something completely different |
| **Hijack Pairs** | Teams randomly form mid-round with shared drawing responsibilities |
| **Fake Words** | Multiple word choices appear—only one is correct |
| **Dynamic Difficulty** | Word pools shift between easy, medium, and hard mid-game |

**Customization:** Hosts dial the chaos level from *Mild* to *Spicy* to *Total Pandemonium*, selecting which twists activate and their intensity.

### Core Features
- **Real-time multiplayer drawing** - Synchronous drawing and guessing with zero delay
- **Invite-based rooms** - Generate 6-character codes with expiry and use limits
- **Flexible architecture** - Host-controlled settings for rounds, draw time, player count, and difficulty
- **Spectator mode** - Watch matches without participating
- **Asynchronous infrastructure** - WebSocket-powered real-time communication
- **Session persistence** - Automatic cleanup of expired sessions
- **Scalable architecture** - Support for multiple concurrent rooms

## Quick Start

### Prerequisites
- Python 3.9+
- pip package manager

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/notahuman404/drawchaos.git
cd drawchaos
```

2. **Install dependencies**
```bash
bash requirements.sh
```

Or manually install:
```bash
pip install fastapi uvicorn python-socketio
```

3. **Run the server**
```bash
python main.py
```

The server will start at `http://localhost:8000`

## Project Structure

```
drawchaos/
├── main.py                 # FastAPI server & WebSocket handler
├── room_manager.py         # Room creation, player management, game state
├── invite_manager.py       # Invite code generation & validation
├── twist_engine.py         # Game modifier system
├── word_list.py            # Word databases for different difficulties
├── requirements.sh         # Dependency installation script
├── static/
│   └── templates/
│       └── index.html      # Frontend UI
└── devlog/                 # Development documentation
```

## How to Play

### For Hosts
1. Start the server: `python main.py`
2. Create a room with your preferred settings (rounds, draw time, difficulty)
3. Share the invite code with friends
4. Configure twists for each round
5. Host the drawing sessions

### For Players
1. Get the invite code from the host
2. Join the room
3. Take turns drawing while others guess
4. Earn points for correct guesses
5. Deal with the unpredictable twists!

## Game Settings

When creating a room, customize:
- **max_players** - Maximum number of players (default: 8)
- **rounds** - Number of rounds to play (default: 5)
- **draw_time** - Seconds per drawing (default: 80)
- **difficulty** - Word difficulty: `easy`, `medium`, `hard` (default: medium)
- **twist_intensity** - Chaos level: `mild`, `spicy`, `chaos` (default: chaos)
- **word_mode** - `normal` or `player_submitted`
- **is_private** - Private room for friends only
- **thief_count** - Number of stroke thieves per round
- **pixelated_count** - Pixelated drawing modifiers
- **foggy_count** - Foggy vision modifiers

## API Overview

The server communicates via WebSocket events. Key events include:

- `create_room` - Host creates a new game room
- `join_room` - Player joins with invite code
- `start_round` - Begin a new drawing round
- `draw` - Send brush stroke data
- `guess` - Submit a word guess
- `guess_thief_stroke` - Steal strokes from other players

## Architecture

DrawChaos is built on:
- **FastAPI** - Modern async web framework
- **Socket.IO** - Real-time bidirectional communication
- **Uvicorn** - Production-grade ASGI server

The architecture is designed for:
- Low latency (critical for real-time drawing)
- Concurrent room management
- Easy deployment and scaling

## Development

### Adding New Twists
Edit `twist_engine.py` and register new twist modifiers in `TWIST_REGISTRY`. Each twist can define:
- Canvas modifications
- Gameplay rules
- Scoring adjustments
- Visual effects

### Extending Word Lists
Update `word_list.py` to add words for different difficulty levels.

### Frontend Development
The UI is in `static/templates/index.html` - extend it to add new features or improve the user experience.

## Troubleshooting

### Can't connect to the server?
- Ensure the server is running: `python main.py`
- Check that port 8000 is available
- Verify firewall settings allow WebSocket connections

### Invite code expired?
- Codes expire after 1 hour or after 20 uses
- Host can revoke codes and generate new ones

### Rooms not persisting?
- Currently, rooms and data are stored in memory
- Consider adding a database layer for persistence (future enhancement)

## Roadmap

- [ ] Database integration for persistent rooms
- [ ] User accounts and statistics tracking
- [ ] More twist modifiers and combinations
- [ ] Mobile app (React Native)
- [ ] Audio chat integration
- [ ] Replay system for saved games
- [ ] Leaderboards and achievements

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-twist`)
3. Commit your changes (`git commit -m 'Add amazing twist'`)
4. Push to the branch (`git push origin feature/amazing-twist`)
5. Open a Pull Request

## Future Enhancements

- **Authentication system** - User accounts and login
- **Game analytics** - Track player stats and performance
- **Custom themes** - Personalize the drawing canvas
- **Tournament mode** - Competitive ranking system
- **Cross-room chat** - Talk to players globally

## Built With ❤️

DrawChaos is an original creation focused on delivering genuinely unique gameplay through innovative twist mechanics.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This project is designed to be chaotic and fun. No friendships were harmed (mostly) in the making of DrawChaos. 😄

---

**Questions or Suggestions?** Open an issue on GitHub or reach out to the development team!

*Happy drawing, and may the chaos be ever in your favor!* 🎨✨