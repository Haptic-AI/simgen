# SimGen

**Midjourney = dream without limits. SimGen = discover what's beautiful within the limits of reality.**

Describe a scene in plain English. Get 4 physics simulations back. Iterate until it's perfect. Every like and dislike teaches the system your creative style — grounded in the real laws of physics.

## Architecture

```
Frontend (Next.js)          Backend (FastAPI)
┌─────────────────┐        ┌──────────────────────────┐
│ Prompt input     │──POST──│ /generate                │
│ 2x2 video grid   │  /gen  │   Claude API → sim config│
│ Thumbs up/down   │        │   MuJoCo render → MP4    │
│                  │◄─video─│ /video/{id}              │
│                  │──POST──│ /feedback                │
└─────────────────┘        └──────────────────────────┘
```

## Quick start

### Backend

```bash
cd backend
pip install -e .
# Set your Anthropic API key
export ANTHROPIC_API_KEY=sk-ant-...
# Start the server
uvicorn backend.main:app --port 8000 --reload
```

Requires `ffmpeg` installed (`brew install ffmpeg`).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 and type a prompt like "a pendulum swinging in low gravity".

## Simulation templates

| Template | Parameters |
|----------|-----------|
| **pendulum** | length, damping, initial_angle, gravity |
| **bouncing_ball** | elasticity, initial_height, ball_size, gravity |
| **robot_arm** | stiffness, damping, target_angle, speed |
| **cartpole** | pole_length, cart_mass, initial_angle, gravity |
| **humanoid** | initial_height, push_force, gravity, damping |

## How it works

1. You type a prompt ("bouncing ball with high elasticity")
2. Claude API interprets it → picks a template + generates 4 parameter variations
3. MuJoCo simulates each variation (5 sec, 30fps)
4. ffmpeg encodes frames to H.264 MP4
5. Frontend displays 4 videos in a grid with feedback buttons

## Project structure

```
backend/
  main.py              # FastAPI endpoints
  renderer.py          # MuJoCo → MP4 pipeline
  prompt_parser.py     # Claude API integration
  templates.py         # Template schemas + param ranges
  templates/           # MuJoCo XML files
    pendulum.xml
    bouncing_ball.xml
    robot_arm.xml
    cartpole.xml
    humanoid.xml

frontend/
  app/page.tsx         # Main UI
  components/
    prompt-input.tsx
    simulation-grid.tsx
    simulation-card.tsx
    feedback-buttons.tsx
```
