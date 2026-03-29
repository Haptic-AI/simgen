# SimGen

SimGen is a prompt-to-scene using a library of pre-trained policies as building blocks. The policies are like instruments in an orchestra — they're already trained to play. The creator is the conductor describing what the music should sound like.

How does it Work? Describe a scene in plain English. Get 4 physics simulations back. Iterate until it's perfect. Every like and dislike teaches the system your creative style — grounded in the real laws of physics.

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

## Progress

| Feature | Status |
|---------|--------|
| FastAPI backend + Next.js frontend | Working |
| 5 MuJoCo templates (pendulum, ball, arm, cartpole, humanoid) | Working |
| Claude API prompt parsing with physics guardrails | Working |
| Environment presets (Earth, Moon, Mars, etc.) | Working |
| Visual themes (Studio, Outdoor, Industrial, Desert, Night, Snow) | Working |
| SQLite persistence (generations, ratings) | Working |
| Feedback loop (ratings → Claude few-shot context) | Working |
| Stats/Insights panel | Working |
| Flow Mode (pick → auto-iterate) | Working |
| Prompt chaining + undo | Working |
| "None of these worked" reject-all + auto-retry | Working |
| Trained walking + running + hopping policies on H100 | Trained |
| GPU render server on H100 | Running |
| Camera tracking for locomotion | Deployed |
| History sidebar | Shipped |
| JIT warmup on GPU server startup | Done |

## Still to do

| Priority | What | Why |
|----------|------|-----|
| P0 | Speed — generation is 2-4 min for walking | Kills the creative flow |
| P1 | Consistent humanoid model (Brax vs our XML) | Two different looking humanoids is confusing |
| P2 | Multi-user support | Need for the 100-creator activation |
| P2 | Video export/download button | Creators need to save their work |
| P2 | Real 3D environments (textures, meshes, Isaac Sim) | Creators want warehouses not colored floors |
| P3 | Camera angle selection | Let creators pick front/side/top view |
| P3 | Prompt suggestions based on popular past prompts | Help new users get started |
| P3 | Fine-tuning a model on accumulated feedback data | The real moat |

## FAQs

**Wouldn't this better be called "prompt-to-policy"?**

No — this is NOT "prompt-to-policy." Here's the distinction:
- **Prompt-to-policy** = user describes a task, system trains a new RL policy from scratch. That takes minutes-hours per prompt. Research tool.
- **SimGen** = user describes a scene, system selects from *pre-trained* policies + configures physics params. That takes seconds. Creative tool.
