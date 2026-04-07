# SimGen

![SimGen Screenshot](docs/Screenshot%202026-04-07%20at%204.19.53%E2%80%AFPM.png)

SimGen is a prompt-to-scene using a library of pre-trained policies as building blocks. The policies are like instruments in an orchestra — they're already trained to play. The creator is the conductor describing what the music should sound like.

How does it Work? Describe a scene in plain English. Get 4 physics simulations back. Iterate until it's perfect. Every like and dislike teaches the system your creative style — grounded in the real laws of physics.

## Architecture

```
Browser → Cloudflare (HTTPS) → simgen-frontend (nginx, e2-small)
                                    ├── /  → Next.js :3000
                                    └── /generate, /job, /video, etc.
                                              ↓
                                    simgen-a100 (A100 80GB GPU, a2-highgpu-1g)
                                    ├── Backend (FastAPI :8000)
                                    │     ├── Async job queue (submit → poll)
                                    │     ├── Claude API for prompt parsing
                                    │     └── Parallel rendering (4 threads)
                                    └── GPU Renderer (FastAPI :8100)
                                          ├── Trained locomotion policies (walk, run, hop)
                                          ├── Passive physics rendering (/render_passive)
                                          └── JIT warmup on startup
```

**Live at:** https://simgen.hapticlabs.ai

**GCloud project:** `www-hapticlabs-org`

| VM | Spec | Zone | Access |
|---|---|---|---|
| `simgen-frontend` | e2-small | us-central1-a | Cloudflare IPs only, port 80/443 |
| `simgen-a100` | a2-highgpu-1g (A100 80GB) | us-central1-f | Internal only, no external IP |

## What Have We Done

- **Prompt-to-scene generation** — Type a scene description in plain English, get 4 physics simulations back in seconds
- **5 simulation templates** — Pendulums, bouncing balls, robotic arms, balancing carts, and humanoid characters
- **Trained locomotion** — Humanoids that can walk, run, and hop using pre-trained movement policies running on a GPU
- **AI-powered prompt understanding** — Claude interprets your descriptions and maps them to real physics parameters (gravity, friction, mass, etc.)
- **Creative iteration tools** — Pick your favorite variation and the system auto-generates 4 more like it. Chain prompts together, undo, or reject all and retry
- **Learning from feedback** — Every thumbs-up or thumbs-down teaches the system your creative preferences
- **Environment presets** — Simulate on Earth, the Moon, Mars, or Jupiter (different gravity!)
- **Visual themes** — Studio, Outdoor, Industrial, Desert, Night, and Snow looks
- **History and stats** — Browse past creations, see insights on what you've generated
- **Live in production** — Fully deployed with GPU rendering, HTTPS, and parallel video generation

## Ideas For What To Do Next

- **Speed up rendering** — Right now 4 videos take ~40 seconds. We want to get that under 20 so the creative loop feels instant
- **Download and export** — Let creators save and share their favorite simulations as video files
- **Richer 3D worlds** — Move beyond colored floors to real environments like warehouses, parks, and cityscapes
- **Multi-user support** — Let many creators use SimGen at the same time
- **Planet selector in the UI** — The Moon/Mars gravity modes are cool but need a cleaner interface
- **Camera angle picker** — Choose front, side, or top-down views of your scene
- **Prompt suggestions** — Help new users get started with popular example prompts
- **Learn from all feedback** — Use accumulated ratings data to fine-tune the AI's understanding of what makes a great simulation

## FAQs

**Wouldn't this better be called "prompt-to-policy"?**

No — this is NOT "prompt-to-policy." Here's the distinction:
- **Prompt-to-policy** = user describes a task, system trains a new RL policy from scratch. That takes minutes-hours per prompt. Research tool.
- **SimGen** = user describes a scene, system selects from *pre-trained* policies + configures physics params. That takes seconds. Creative tool.
