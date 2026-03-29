# SimGen

SimGen is a prompt-to-scene using a library of pre-trained policies as building blocks. The policies are like instruments in an orchestra — they're already trained to play. The creator is the conductor describing what the music should sound like.  

How does it Work? Describe a scene in plain English. Get 4 physics simulations back. Iterate until it's perfect. Every like and dislike teaches the system your creative style — grounded in the real laws of physics.

## Progress

```
┌────────────────────────────────────────────────────────────────────────┬──────────────┐
│Feature │Status│
├────────────────────────────────────────────────────────────────────────┼──────────────┤
│ FastAPI backend + Next.js frontend │ Working│
├────────────────────────────────────────────────────────────────────────┼──────────────┤
│ 5 MuJoCo templates (pendulum, ball, arm, cartpole, humanoid) │ Working│
├────────────────────────────────────────────────────────────────────────┼──────────────┤
│ Claude API prompt parsing with physics guardrails│ Working│
├────────────────────────────────────────────────────────────────────────┼──────────────┤
│ Environment presets (Earth, Moon, Mars, etc.)│ Working│
├────────────────────────────────────────────────────────────────────────┼──────────────┤
│ SQLite persistence (generations, ratings)│ Working│
├────────────────────────────────────────────────────────────────────────┼──────────────┤
│ Feedback loop (ratings → Claude few-shot context)│ Working│
├────────────────────────────────────────────────────────────────────────┼──────────────┤
│ Stats/Insights panel │ Working│
├────────────────────────────────────────────────────────────────────────┼──────────────┤
│ Flow Mode (pick → auto-iterate)│ Working│
├────────────────────────────────────────────────────────────────────────┼──────────────┤
│ Prompt chaining + undo │ Working│
├────────────────────────────────────────────────────────────────────────┼──────────────┤
│ "None of these worked" reject-all + auto-retry │ Working│
├────────────────────────────────────────────────────────────────────────┼──────────────┤
│ Trained walking policy on H100 (Brax PPO)│ Trained│
├────────────────────────────────────────────────────────────────────────┼──────────────┤
│ GPU render server on H100│ Running│
├────────────────────────────────────────────────────────────────────────┼──────────────┤
│ Camera tracking for locomotion │ Deployed │
├────────────────────────────────────────────────────────────────────────┼──────────────┤
│ History sidebar│ Just shipped │
├────────────────────────────────────────────────────────────────────────┼──────────────┤
│ 14px base font size│ Done │
├────────────────────────────────────────────────────────────────────────┼──────────────┤
│ All docs (product vision, build log, locomotion plan, lessons learned) │ Written│
└────────────────────────────────────────────────────────────────────────┴──────────────┘

Still to do

┌──────────┬──────────────────────────────────────────────────┬──────────────────────────────────────────────┐
│ Priority │ What │ Why│
├──────────┼──────────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ P0 │ Speed — generation is 2-4 min for walking│ Kills the creative flow│
├──────────┼──────────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ P1 │ Consistent humanoid model (Brax vs our XML)│ Two different looking humanoids is confusing │
├──────────┼──────────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ P1 │ JIT warmup on GPU server startup │ First request shouldn't be 60s slower│
├──────────┼──────────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ P2 │ More policies (jump, stumble, push recovery) │ Only walking works; falling is still ragdoll │
├──────────┼──────────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ P2 │ Multi-user support │ Need for the 100-creator activation│
├──────────┼──────────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ P2 │ Video export/download button │ Creators need to save their work │
├──────────┼──────────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ P3 │ Camera angle selection │ Let creators pick front/side/top view│
├──────────┼──────────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ P3 │ Prompt suggestions based on popular past prompts │ Help new users get started │
├──────────┼──────────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ P3 │ Fine-tuning a model on accumulated feedback data │ The real moat│
└──────────┴──────────────────────────────────────────────────┴──────────────────────────────────────────────┘
```

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


# FAQS

1. Wouldnt this better be called "prompt-to-policy"?

No — this is NOT "prompt-to-policy." Here's the distinction:                                                                                               
- Prompt-to-policy = user describes a task, system trains a new RL policy from scratch. That takes minutes-hours per prompt. Research tool.
- SimGen = user describes a scene, system selects from pre-trained policies + configures physics params. That takes seconds. Creative tool.
   
