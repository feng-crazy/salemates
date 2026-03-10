---
name: sales_coaching
description: Sales coaching mode for practice sessions and real-time assistance
metadata:
  vikingbot:
    emoji: 🎓
    requires: {}
---

# Sales Coaching Mode

## Overview

Sales coaching provides two modes for improving sales skills:

1. **Practice Mode**: AI acts as a customer for role-play training
2. **Assist Mode**: Real-time strategy suggestions for live conversations

## When to Use

Use this skill when:
- New sales team members need training
- Preparing for important customer calls
- Want to practice handling objections
- Need real-time guidance during conversations

## Practice Mode

### Starting a Practice Session

Use `sales_coach` tool with:
```
action: "start_session"
mode: "practice"
scenario_id: "price_sensitive"  # Optional, defaults to first scenario
```

### Available Scenarios

| ID | Name | Difficulty | Description |
|----|------|------------|-------------|
| price_sensitive | Price-Sensitive Procurement Manager | Intermediate | Focus on cost, pushes on pricing |
| technical | Technical Decision Maker | Advanced | Deep technical questions |
| hesitant | Hesitant First-Time Buyer | Beginner | Needs education and reassurance |
| executive | C-Level Executive | Expert | Brief, value-focused, strategic |
| competitor_comparison | Active Competitor Evaluation | Advanced | Comparing with specific competitor |

### Continuing Practice Dialogue

```
action: "respond"
session_id: "<session_id>"
user_message: "您的回复内容"
```

### Ending Practice and Getting Feedback

```
action: "end_session"
session_id: "<session_id>"
```

## Assist Mode

### Starting an Assist Session

```
action: "start_session"
mode: "assist"
```

### Getting Strategy Suggestions

```
action: "respond"
session_id: "<session_id>"
customer_context: {
    "last_customer_message": "客户说的内容",
    "industry": "行业",
    "stage": "discovery"
}
```

## Performance Evaluation

The system evaluates across 7 dimensions:
- Rapport Building (亲和力建立)
- Needs Discovery (需求挖掘 - SPIN)
- Product Knowledge (产品知识)
- Objection Handling (异议处理)
- Closing Technique (成交技巧)
- Communication Clarity (沟通清晰度)
- Active Listening (积极倾听)

## Example Practice Session

```
1. Start: sales_coach(action="start_session", mode="practice", scenario_id="price_sensitive")
   → AI sends initial customer message

2. Respond: sales_coach(action="respond", session_id="xxx", user_message="我理解您的顾虑...")
   → AI responds as customer

3. Continue practice...

4. End: sales_coach(action="end_session", session_id="xxx")
   → Get detailed performance score
```

## Tips for Effective Practice

1. **Take it seriously**: Treat it like a real customer conversation
2. **Use SPIN**: Situation → Problem → Implication → Need-payoff
3. **Handle objections**: Don't avoid, address them directly
4. **Move to close**: After building value, suggest next steps
5. **Review feedback**: Study the performance report after each session

## Common Mistakes to Avoid

- Rushing to price discussions before understanding needs
- Not asking enough questions
- Ignoring customer concerns
- Forgetting to progress the conversation toward a close
- Being too pushy or too passive

## Related Skills

- `spin_selling`: SPIN methodology for needs discovery
- `fab_selling`: Features-Advantages-Benefits framework
- `objection_handling`: Specific objection techniques
- `bant_qualification`: Budget-Authority-Need-Timeline qualification