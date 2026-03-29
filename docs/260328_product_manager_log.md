# 2026-03-28 — Product Manager Log

## What are we actually building?

**A creative simulation IDE.** Not a physics tool — a *creative tool that happens to use physics*. Think of it like:

- **Midjourney** = prompt → image → iterate → perfect image
- **SimGen** = prompt → physics simulation → iterate → perfect scene

The product is: **an iterative creative canvas where physics is the medium, not the interface.** The creator never thinks about gravity or damping — they think about *how the scene feels*. "More dramatic." "Slower." "Make it float." "More weight." And the system translates that into physics under the hood.

## What makes this different from just running MuJoCo

1. **The iteration memory** — every like/dislike trains the system toward YOUR aesthetic. After 50 ratings, it knows you prefer dramatic over subtle, slow over fast, etc.
2. **Physics is abstracted away** — you say "make it heavier" not "increase gravity to 15 m/s²"
3. **The climb** — you can keep refining a single scene through dozens of iterations until it's exactly right, and the system remembers every step

## The moat

The "lessons" you're saving aren't just ratings — they're building a **preference model** for your creative style. That's the moat. After 100 creators each do 50 generations, you'll have a dataset of creative-intent → physics-params that no one else has.

## The core UX problem

The physics being "in the way" is actually the core UX problem to solve: **how to make the gap between creative intent and physics parameters invisible.** The environment presets and the vary flow are steps toward that. The next steps would be things like:

- "Make this heavier" as a follow-up prompt (natural language param adjustment)
- Sliders that say "Drama" and "Speed" not "damping" and "timestep"
- Side-by-side before/after when iterating

---

## The anti-Midjourney insight (2026-03-28)

SimGen is NOT "Midjourney for physics." It's the **opposite** in a critical way:

**Midjourney lets you dream without limits.** You can create impossible things — floating cities, 12-armed creatures, physics-defying architecture. Reality is thrown out the window.

**SimGen is grounded in reality.** The whole point is that the simulation follows the laws of physics. You can jump, but you can't jump 7 feet. If you weigh 180lbs, you can probably jump 2.5 feet. Gravity is real. Mass matters. Time is honest.

The creative spectrum is:

```
Midjourney                                              SimGen
(pure imagination)                               (grounded reality)
"anything is possible"                    "what's possible is beautiful"
no physics rules                          physics IS the creative medium
```

The magic is: **making reality feel playful.** Creators get to explore what's *actually possible* in interesting ways, without needing a physics degree. The system says "yes, and here's what that looks like" — but never "yes" to something that would break the real world.

### Two user personas, one feedback loop

**1. The Creator (end user)**
- Submits prompts, iterates, rates results
- Wants to make playful, interesting simulations that follow the rules of physics
- Should never see MuJoCo XML, gravity constants, or damping coefficients
- Their job: describe what they want to see, vote on what's good, keep iterating
- Constrained by reality: "a person jumping" → the system knows a human can jump ~2-3 feet, not 20 feet
- The spectrum of space, time, and gravity is the creative canvas — not infinite imagination

**2. The Admin / Model Owner (us)**
- Collects all lessons from all creators across all sessions
- Aggregates voting data: which prompts + which params = upvotes?
- Uses the aggregate data to improve the model:
  - Better default params for common prompts
  - Tighter physics constraints that match creator expectations
  - New templates based on what creators keep asking for but can't get
  - Fine-tuned prompt parsing that maps creative language → physically accurate configs
- The outcome: each generation of the model makes it EASIER for creators to get physically realistic simulations from simple prompts

### The flywheel

```
Creators prompt & rate
        ↓
Feedback data accumulates
        ↓
Admin analyzes patterns
        ↓
Model improves (better defaults, tighter constraints, new templates)
        ↓
Creators get better results from simpler prompts
        ↓
More creators use the tool
        ↓
More feedback data
        ↓
(repeat)
```

### What "physics as guardrails" means in practice

The AI prompt parser isn't just translating creative intent into params — it's also the **physics referee**. It should:

- Know that a 180lb human can't jump 7 feet
- Know that a pendulum on Earth can't swing in slow motion without changing something physical
- Offer creative alternatives when a request breaks physics: "You can't jump that high on Earth, but here's what it looks like on the Moon"
- Never generate params that produce physically impossible or nonsensical simulations

This is the key difference from image generation: **the output has to be truthful.** A simulation that looks cool but violates physics is a bug, not a feature.

### The 100-creator marketing activation

Goal: get 100 creators prompting and rating to:
1. Validate that the UX is intuitive enough for non-technical users
2. Collect a critical mass of preference data (100 creators × 50 generations = 5,000 rated simulations)
3. Identify the top 10 prompts/scenes that creators keep trying to make — these become the first "polished" templates
4. Find the UX friction points before scaling further

---

## Addendum: What was built on 2026-03-28

This section documents the evolution of the codebase during this session so that any future LLM or contributor can understand how the product got to its current state and why each decision was made.

### Evolution timeline

**Starting point (from 2026-03-27):**
- Basic FastAPI backend + Next.js frontend
- Claude API parses prompts → picks from 5 MuJoCo XML templates → renders 4 MP4 videos
- In-memory state, no persistence
- Thumbs up/down buttons existed but did nothing useful (stored in a Python dict, lost on restart)
- Templates: pendulum, bouncing_ball, robot_arm, cartpole, humanoid
- No feedback loop, no learning, no iteration

### Change 1: SQLite persistence + feedback loop

**Files:** `backend/db.py` (new), `backend/main.py` (rewritten)

**What:** Replaced in-memory dicts with SQLite database (`simgen.db`). Every generation, simulation, and rating is now persisted across restarts.

**Why:** Thumbs up/down was meaningless without persistence. The entire product vision depends on accumulating creator preferences over time.

**Schema:**
- `generations` table: id, prompt, template, description, created_at
- `simulations` table: id, generation_id, label, template, params (JSON), video_path, rating, rated_at

### Change 2: Feedback wired into prompt parser

**Files:** `backend/prompt_parser.py` (rewritten)

**What:** Before each Claude API call, the system queries the DB for top-rated and downvoted simulations. These are injected into Claude's system prompt as few-shot examples under "Learning from creator feedback."

**Why:** This is the core learning mechanism. Claude sees what the creator liked/disliked and biases future generations accordingly. No fine-tuning needed — it's in-context learning from the preference history.

**How it works:**
```
Creator thumbs-up "Weightless Serenity" (gravity=1.0, damping=1.0)
        ↓
Next prompt: Claude's system prompt includes:
"### Liked: 'Weightless Serenity' — {gravity: 1.0, damping: 1.0}"
        ↓
Claude generates new configs biased toward low gravity, high damping
```

### Change 3: Stats endpoint + insights panel

**Files:** `backend/main.py` (GET /stats), `frontend/components/stats-panel.tsx` (new)

**What:** Dashboard showing total generations, ratings, per-template performance (upvote %), top-rated param combos, and unmatched prompts (all 4 sims downvoted).

**Why:** The admin persona needs visibility into what's working. Also gives creators a sense that their feedback matters ("Learning from 12 ratings").

### Change 4: Environment presets

**Files:** `backend/environments.py` (new), `frontend/components/environment-selector.tsx` (new)

**What:** Six named environments: Earth, Moon, Mars, Mercury, Jupiter, Zero-G. Each defines gravity, damping, and air density. Selectable with one click in the UI.

**Why:** Creators shouldn't type "gravity=1.62". They should click "Moon." Environments are the creative canvas — Earth constrains, Moon liberates, Jupiter grounds. The environment IS the creative tool, not a parameter.

**Environments:**
| Name | Gravity | Creative use |
|------|---------|-------------|
| Earth | 9.81 | Grounded reality — the default |
| Moon | 1.62 | Floating, graceful, slow falls |
| Mars | 3.72 | Between Earth and Moon |
| Mercury | 3.70 | Similar to Mars, no atmosphere |
| Jupiter | 24.79 | Heavy, fast, crushing |
| Zero-G | 0.01 | Weightlessness, space |

### Change 5: Physics guardrails

**Files:** `backend/physics_rules.py` (new), `backend/prompt_parser.py` (updated system prompt)

**What:** A comprehensive real-world physics knowledge base injected into Claude's system prompt. Includes human body facts (jump height, mass, force thresholds), pendulum physics, ball elasticity values, robot arm speeds, and cartpole stability rules.

**Why:** This is what makes SimGen different from Midjourney. The AI is both a creative director AND a physics referee. When a creator asks for something impossible, it doesn't refuse — it gets as close as possible and suggests alternatives (e.g., "Try Moon for more float time").

**Key design decisions:**
- Never refuse a prompt — always generate 4 variations
- 4-variation spectrum: Realistic → Cinematic → Stylized → Pushing Limits
- When physics are violated, explain in the description field and suggest environment switches
- One variation is allowed to be "cinematic license" — slightly beyond real — so creators can see the boundary

### Change 6: Vary / iterate endpoint

**Files:** `backend/main.py` (POST /vary), `backend/prompt_parser.py` (parse_prompt_with_base function)

**What:** "Iterate on this" button on each simulation card. Sends the liked simulation's params to Claude as a base, generates 4 new variations that are CLOSE to it (10-40% param variation, same template).

**Why:** This is the Midjourney V1/V2/V3/V4 workflow. Pick a winner, refine it. Without this, every generation starts from scratch. With it, creators can climb toward their perfect scene through dozens of iterations.

### Change 7: Flow Mode + prompt chaining

**Files:** `frontend/app/page.tsx` (major rewrite), `frontend/components/simulation-card.tsx` (updated), `frontend/components/simulation-grid.tsx` (updated)

**What:** After first generation, the app enters "Flow Mode":
- Hover any video → "Pick this one" overlay
- Clicking picks it: auto-upvotes AND generates 4 new variations
- Prompt bar switches to refinement mode ("make it slower", "more dramatic")
- Breadcrumb trail shows the full journey of prompts
- Undo button to backtrack one step
- Previous rounds fade to 50% opacity, latest round is prominent

**Why:** The original UX was: type prompt → wait → rate → type prompt again. Too many clicks, too slow. Flow Mode is: type once → pick → pick → pick → refine → pick. The creator stays in a creative flow state.

**The prompt chain:**
```
"a person stumbling" → [pick Variation 2] → "make it slower" → [pick Variation 1] → "add more weight" → ...
```
Each step is recorded. Undo pops the last step. The chain IS the creative journey.

### Change 8: 15-second videos

**Files:** `backend/templates.py` (sim_duration: 5.0 → 15.0 for all templates)

**What:** All simulations now render 15 seconds instead of 5.

**Why:** 5 seconds wasn't enough to see interesting physics play out. 15 seconds shows the full arc — a pendulum swinging and decaying, a humanoid falling and settling, a ball bouncing to rest. Tradeoff: generation takes ~3x longer (~45-90s for 4 videos).

### Current architecture (as of end of 2026-03-28)

```
frontend/ (Next.js 15, Tailwind)
  app/page.tsx              # Main page with Flow Mode, prompt chaining, undo
  components/
    prompt-input.tsx        # Adaptive prompt bar (initial vs refinement mode)
    simulation-grid.tsx     # 2x2 grid with flow mode support
    simulation-card.tsx     # Video card with "Pick this one" overlay
    feedback-buttons.tsx    # Thumbs up/down (wired to DB)
    environment-selector.tsx # Earth/Moon/Mars/etc pill buttons
    stats-panel.tsx         # Learning insights dashboard

backend/ (FastAPI, Python)
  main.py                   # Endpoints: /generate, /vary, /video, /feedback, /stats, /environments, /health
  prompt_parser.py          # Claude API with physics rules + feedback context + vary mode
  renderer.py               # MuJoCo headless → imageio MP4 (15 sec, 640x480, 30fps)
  db.py                     # SQLite persistence (generations, simulations, ratings)
  templates.py              # 5 template schemas with param ranges
  environments.py           # 6 environment presets (Earth, Moon, Mars, etc)
  physics_rules.py          # Real-world physics knowledge base for the AI referee
  templates/                # MuJoCo XML files (pendulum, bouncing_ball, robot_arm, cartpole, humanoid)

simgen.db                   # SQLite database (auto-created on first run)
```

### What's next (priorities for future sessions)

1. **Speed** — generation takes 45-90s. Need parallel rendering, GPU acceleration (H100), or shorter preview videos
2. **More templates** — creators will ask for things the 5 templates can't do. Need a system to add templates based on unmatched prompt data
3. **Multi-user** — current system is single-user. For the 100-creator activation, need user accounts and per-user preference models
4. **Fine-tuning** — once enough feedback data exists, fine-tune a model specifically for creative-intent → physics-params mapping
5. **Export** — creators need to download their favorite simulations as high-res video
6. **Prompt suggestions** — based on what's worked well for other creators, suggest prompts to new users
