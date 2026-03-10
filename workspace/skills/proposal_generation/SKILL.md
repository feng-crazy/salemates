---
name: proposal_generation
description: Generate professional sales proposals with ROI analysis and A/B testing support
metadata:
  vikingbot:
    emoji: 📄
    requires: {}
    tools:
      - generate_proposal
---

# Proposal Generation Skill

## Overview

This skill enables the agent to generate professional, customized sales proposals with:
- **ROI Analysis**: Automatic calculation of return on investment metrics
- **A/B Testing**: Three proposal versions (A, B, C) for testing effectiveness
- **Tiered Solutions**: Support for Basic, Professional, and Enterprise tiers
- **Custom Sections**: Add customer-specific content

## When to Use

Use this skill when:
- Customer is in PRESENTATION or NEGOTIATION stage
- Customer requests a formal proposal
- You need to quantify the value proposition
- Testing different messaging approaches

## Tool: generate_proposal

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| customer_name | string | Yes | Customer name |
| product_tier | string | Yes | Basic, Professional, or Enterprise |
| include_roi | boolean | No | Include ROI analysis (default: true) |
| version | string | No | A, B, or C (default: A) |
| investment_amount | number | No | Total investment in CNY |
| annual_savings | number | No | Expected annual savings |
| time_saved_hours | number | No | Hours saved per month |
| pain_points | array | No | Customer pain points to address |
| custom_sections | array | No | Additional sections |

### Version Variants

| Version | Focus | Best For |
|---------|-------|----------|
| **A** | Standard | Formal RFP responses, established enterprises |
| **B** | Value-focused | Cost-conscious buyers, SMBs |
| **C** | ROI-focused | CFO/finance stakeholders, data-driven buyers |

## Usage Examples

### Basic Proposal (Version A)

```json
{
  "customer_name": "TechCorp Inc.",
  "product_tier": "Professional"
}
```

### Proposal with ROI Analysis (Version C)

```json
{
  "customer_name": "TechCorp Inc.",
  "product_tier": "Enterprise",
  "version": "C",
  "investment_amount": 120000,
  "annual_savings": 180000,
  "time_saved_hours": 50,
  "pain_points": [
    "Manual data entry taking 10+ hours/week",
    "Lack of real-time reporting",
    "Integration challenges with existing systems"
  ]
}
```

### Value-Focused Proposal (Version B)

```json
{
  "customer_name": "TechCorp Inc.",
  "product_tier": "Professional",
  "version": "B",
  "pain_points": [
    "Team collaboration inefficiencies",
    "Limited visibility into project status"
  ],
  "custom_sections": [
    {
      "title": "Implementation Timeline",
      "content": "Week 1: Setup\nWeek 2: Training\nWeek 3: Go-live"
    }
  ]
}
```

## ROI Calculation

The tool automatically calculates:

1. **ROI Percentage**: `(Annual Benefit - Investment) / Investment × 100`
2. **Payback Period**: `Investment / (Annual Benefit / 12)` months
3. **Time Value**: `Hours Saved × 12 × Hourly Rate`

### Default Hourly Rate

¥200/hour (configurable)

## Best Practices

### DO:
- ✅ Include specific numbers when available (savings, hours saved)
- ✅ Match version to customer type
- ✅ Add custom sections for unique requirements
- ✅ Include pain points to show solution relevance

### DON'T:
- ❌ Skip ROI for enterprise deals
- ❌ Use Version C for early-stage conversations
- ❌ Forget to follow up after sending proposal

## Integration Workflow

1. **Discovery Stage**: Gather pain points, budget, timeline
2. **Presentation Stage**: Generate initial proposal (Version A or B)
3. **Negotiation Stage**: Refine with specific ROI data (Version C)
4. **Follow-up**: Track response and iterate

## Common Scenarios

### Scenario 1: Customer asks for pricing

```
Customer: "Can you send me a quote?"

Agent Action:
1. Generate proposal with Version A
2. Include relevant tier based on customer size
3. Send proposal document
```

### Scenario 2: Customer wants to see ROI

```
Customer: "What's the return on investment?"

Agent Action:
1. Generate proposal with Version C
2. Include investment_amount, annual_savings
3. Highlight payback period in conversation
```

### Scenario 3: A/B testing messaging

```
Strategy: Send different versions to similar customers

Day 1: Send Version A to Customer A
Day 1: Send Version B to Customer B
Day 1: Send Version C to Customer C

Measure: Which version gets better response rate?
```

## Output Format

All proposals return formatted Markdown ready for:
- Email attachment
- Document generation (PDF)
- Chat display
- CRM storage