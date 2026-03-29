# SimGen Compute Vision

## The Ask: 8x H100s at ~$17K/month

**Breakdown:**
- 4 for inference (serving 60 concurrent creatives at ~30 prompts/min with 30s GPU-time each)
- 2 for continuous RLHF/DPO training from the preference feedback
- 2 for headroom/eval

**The flywheel:** more creatives → more thumbs up/down data → better model → more users.

Positioned as the minimum viable compute to keep the loop spinning.

## Phased Scaling

```
Phase 1: 1 GPU   (current — prototype, single user)
Phase 2: 4 GPUs  (100-creator activation, parallel inference)
Phase 3: 8 GPUs  (production — inference + continuous training)
Phase 4: 16 GPUs (scale — multi-tenant, real-time rendering)
```

## Comparable Architectures

- **GenSim2** — automated robot task generation using LLMs + simulation
- **DreamFusion** — text-to-3D using score distillation
- **MuJoCo Playground** — GPU-accelerated RL training for robotics

## Cost Projection

~$136K through month 12:
- Months 1-3: 1 GPU (~$2K/mo) = $6K
- Months 4-6: 4 GPUs (~$8K/mo) = $24K
- Months 7-9: 8 GPUs (~$17K/mo) = $51K
- Months 10-12: 8-16 GPUs (~$17-34K/mo) = $55K

## What the Compute Enables

### Inference (4 GPUs)
- MuJoCo simulation + MJX batched rendering
- 30s per 4-video generation (current: 2-4 min)
- 60 concurrent creative sessions
- ~30 prompts/minute throughput

### Training (2 GPUs)
- Continuous RLHF/DPO from creator feedback
- Train new locomotion policies as creators request them
- Fine-tune prompt → physics parameter mapping
- A/B test model improvements against creator preferences

### Headroom (2 GPUs)
- Eval pipeline for model quality
- Staging environment for new policies before production
- Burst capacity for high-traffic periods
