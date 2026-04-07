# From Cloud GPUs to Creative Canvas: Building SimGen, a Prompt-to-Simulation Engine

*Part 3 of the MuJoCo deployment series — where infrastructure becomes a product.*

---

In [Part 1](https://www.hapticlabs.ai/blog/2026/03/21/deploying-mujoco-on-azure-ml), I documented the surprisingly painful process of getting MuJoCo running on Azure ML — the filesystem traps, the driver conflicts, the four-hour startup delays nobody warned us about. In [Part 2](https://www.hapticlabs.ai/blog/2026/03/31/deploying-mujoco-on-azure-ml-part-2), Microsoft responded, and we learned we'd been fighting the wrong abstraction the entire time. Blobfuse2, not CIFS. Download Mode, not mount-and-pray.

Those articles solved a real problem for researchers at Georgia Tech who needed GPU-accelerated physics simulations without a six-week DevOps detour. We packaged the lessons into `mjcloud`, a CLI that deploys a MuJoCo-ready GPU VM in one command. Humanoid loads, Jupyter starts, you're simulating in minutes.

But while building that tool, a question kept nagging me.

## The Question Nobody Was Asking

Working in forward deployment with robotics researchers, I watched brilliant people spend days configuring environments just to test a hypothesis about how a robot might walk. The simulation itself — the interesting part — was buried under layers of XML authoring, parameter tuning, and rendering pipelines. It struck me as absurd.

We live in a world where you can type "astronaut riding a horse on Mars" into Midjourney and get four photorealistic images in seconds. You can describe a video to Runway and watch it render. The prompt-to-creation pattern has transformed every visual medium — except the one grounded in physics.

Why isn't there a Midjourney for simulation?

Not a toy. Not a visualizer. A creative tool where you describe what you want to see happen in a physics engine, and it generates variations for you to explore, rate, and refine.

## What SimGen Is

SimGen is a prompt-to-physics-simulation engine. You type a natural language prompt — "a humanoid doing a backflip on the Moon" or "a pendulum swinging in zero gravity" — and the system generates four MuJoCo simulation videos, each a different interpretation of your intent.

The interface borrows deliberately from Midjourney's creative workflow. Four variations appear. You upvote the ones that capture what you imagined. The system enters Flow Mode: hover over a favorite, click "Pick this one," and it generates four new variations within a tight parameter range of your selection. A breadcrumb trail tracks your creative journey. An undo button lets you backtrack.

But here's what makes it fundamentally different from image or video generation: **physics is the constraint, and the constraint is the point.**

Midjourney lets you imagine the impossible — cities floating in clouds, geometry that couldn't exist. SimGen is the opposite. Gravity is real. Mass matters. A person can jump two feet, not twenty. The laws of physics aren't limitations to work around; they're the creative medium itself. The beauty comes from what's actually possible.

## How It Works Under the Hood

The architecture splits across two machines. A FastAPI backend running on a standard server handles prompt parsing through Claude, which acts as both creative director and physics referee. Claude translates natural language into MuJoCo simulation parameters — gravity, mass, damping, initial velocity — constrained by real-world physics knowledge baked into its system prompt. It never refuses a prompt. Instead, it always generates four variations spanning a spectrum: Realistic, Cinematic, Stylized, and Pushing Limits.

The heavy lifting happens on an H100 GPU server running headless MuJoCo with EGL rendering. For locomotion — walking, running, hopping — Brax PPO policies trained on 8,192 parallel environments via JAX produce the motion. A Next.js frontend ties it together with environment presets (Earth, Moon, Mars, Jupiter, Zero-G) and visual themes that let creators set mood without touching a single physics parameter.

Every rating feeds back into the system. Upvoted simulations become few-shot examples in Claude's context, teaching it what this particular creator considers beautiful, dramatic, or realistic. After enough iterations, the model learns your aesthetic. That preference data — mapping creative intent to physics parameters — is the real product. It's a dataset nobody else has.

## Why I Built It

The motivation was never to replace research tools. MuJoCo, dm_control, Isaac Sim — these are extraordinary platforms for people who know what they're doing. The motivation was to open the door for people who don't.

Robotics simulation has no social layer. There's no community of creators sharing physics scenes the way photographers share on Instagram or designers share on Dribbble. There's no feedback loop between what someone imagines and what the physics engine can produce — unless you already speak the language of MJCF XML and reward functions.

I wanted to remove that barrier. A filmmaker should be able to prototype a zero-gravity fight scene. A game designer should be able to test whether a physics mechanic feels right. A student should be able to explore orbital mechanics by describing what they want to see, not by writing simulation code.

The work at Georgia Tech planted the seed. Helping researchers deploy MuJoCo on cloud GPUs showed me how much friction exists between having a physics question and getting a physics answer. The two blog posts were about reducing infrastructure friction. SimGen is about reducing the creative friction that comes after.

## Where It Stands

SimGen is live, deployed on GCloud with three Docker containers. The core loop works: prompt, generate, rate, refine. Five simulation templates render correctly — pendulum, bouncing ball, robot arm, cartpole, humanoid. Environment presets and visual themes give creators intuitive controls. The feedback loop learns from every rating.

The honest gap is locomotion. Walking is the first thing everyone asks for, and it's the hardest thing to get right. Our Brax-trained policies optimized for forward velocity but learned to crawl instead of walk upright — a classic reward-shaping problem. Fixing this is priority one.

The next milestone is getting 100 creators generating and rating simulations. At 50 generations each, that's 5,000 rated physics scenes — enough preference data to fine-tune a model that genuinely understands the mapping between what people describe and what they want to see. That's when SimGen stops being a tool and starts being a platform.

## The Bigger Picture

Parts 1 and 2 of this series were about making GPU simulation accessible to researchers. SimGen is about making physics simulation accessible to everyone. The throughline is the same belief: the bottleneck in robotics and simulation isn't compute or algorithms. It's access.

The prompt-to-creation pattern proved that for images and video. There's no reason physics should be different. The laws of nature are the most interesting creative constraint we have — and right now, almost nobody gets to play with them.

That's what SimGen is for.

---

*SimGen is open source at [github.com/Haptic-AI/simgen](https://github.com/Haptic-AI/simgen). If you'd like to be part of the first 100 creators, reach out at [hapticlabs.ai](https://hapticlabs.ai).*
