# AGENTS.md: workspace/skills

Agent skills - reusable capabilities loaded as markdown files.

---

## OVERVIEW

Skills define specialized knowledge and behaviors for the agent. Each skill is a markdown file with instructions that get loaded into the agent's context.

---

## STRUCTURE

```
workspace/skills/
├── README.md                    # Skills documentation
├── spin_selling/                # SPIN sales methodology
│   └── SKILL.md
├── fab_selling/                 # FAB sales methodology
│   └── SKILL.md
├── bant_qualification/          # BANT lead qualification
│   └── SKILL.md
├── objection_handling/          # Sales objection handling
│   └── SKILL.md
├── summarize/                   # Summarization skill
│   └── SKILL.md
├── github/                      # GitHub integration
│   └── SKILL.md
├── opencode/                    # OpenCode integration
│   ├── SKILL.md
│   ├── opencode_utils.py
│   └── list_sessions.py
├── cron/                        # Cron job skill
│   └── SKILL.md
├── tmux/                        # TMux skill
│   ├── SKILL.md
│   └── scripts/
├── weather/                     # Weather skill
│   └── SKILL.md
├── github-proxy/                # GitHub proxy
│   ├── SKILL.md
│   └── scripts/
└── skill-creator/               # Skill creation helper
    └── SKILL.md
```

---

## WHERE TO LOOK

| Skill | Directory | Purpose |
|-------|-----------|---------|
| SPIN Selling | `spin_selling/` | Situation, Problem, Implication, Need-payoff |
| FAB Selling | `fab_selling/` | Features, Advantages, Benefits |
| BANT | `bant_qualification/` | Budget, Authority, Need, Timeline |
| Objection Handling | `objection_handling/` | Handle sales objections |
| Summarize | `summarize/` | Content summarization |
| GitHub | `github/` | GitHub operations |
| OpenCode | `opencode/` | OpenCode integration |
| Cron | `cron/` | Scheduled tasks |
| TMux | `tmux/` | TMux operations |
| Weather | `weather/` | Weather queries |
| Skill Creator | `skill-creator/` | Create new skills |

---

## SKILL FORMAT

Each skill is a `SKILL.md` file:

```markdown
# Skill: SPIN Selling

## Purpose
Guide sales conversations using SPIN methodology.

## When to Use
- Customer shows hesitation
- Need to uncover pain points
- Building value proposition

## Instructions
1. **S**ituation: Ask about current state
2. **P**roblem: Identify challenges
3. **I**mplication: Explore consequences
4. **N**eed-payoff: Highlight solution value

## DO NOT
- Rush to pricing
- Skip stages
- Use generic questions
```

---

## LOADING SKILLS

```python
from salesmate.agent.skills import SkillsLoader

loader = SkillsLoader(workspace_path)
skills = loader.load_skills()  # Returns list of skill content
```

---

## CREATING A NEW SKILL

1. Create directory: `workspace/skills/my_skill/`
2. Create `SKILL.md`:
   - Purpose and when to use
   - Step-by-step instructions
   - DO NOT section
   - Examples (optional)
3. Add helper scripts if needed (Python, shell)

---

## ANTI-PATTERNS

- **NEVER** include setup/testing procedures in SKILL.md
- **NEVER** create auxiliary docs - only SKILL.md needed
- **NEVER** make skills too large - keep focused