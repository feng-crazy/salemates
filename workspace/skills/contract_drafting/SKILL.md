---
name: contract_drafting
description: Intelligent contract drafting with compliance checking and risk assessment
metadata:
  vikingbot:
    emoji: 📝
    requires: {}
---

# Contract Drafting Skill

## Overview

智能合同起草工具，支持：
- 基于模板自动生成合同
- 风险合规预审
- 条款动态适配
- 电子签集成（stub）

## When to Use

Use when:
- 客户进入 NEGOTIATION 阶段
- 需要起草销售合同
- 需要检查合同风险
- 客户要求条款确认

## Contract Types

1. **service_agreement** - 服务协议
2. **nda** - 保密协议
3. **sales_contract** - 销售合同

## Usage

### Generate Contract

```
Use the draft_contract tool with:
- customer_name: 客户名称
- contract_type: 合同类型
- negotiation_summary: 谈判摘要
- total_value: 合同金额
- check_compliance: 是否检查合规 (默认 true)
```

### Compliance Check

The tool automatically checks for:
- Missing required clauses
- Prohibited terms
- Risk patterns
- Compliance score (0-100)

## Compliance Rules

### Required Clauses
- 终止条款 (Termination)
- 付款条款 (Payment Terms)
- 责任限制 (Limitation of Liability)
- 保密条款 (Confidentiality)
- 适用法律 (Governing Law)
- 争议解决 (Dispute Resolution)

### Prohibited Terms
- 无限责任 (Unlimited Liability)
- 单方修改权 (Unilateral Modification)
- 单方终止权 (Unilateral Termination)
- 自动续约无通知 (Auto-renewal without Notice)
- 过度惩罚条款 (Excessive Penalties)

## Risk Levels

| Level | Score | Action |
|-------|-------|--------|
| LOW | 80-100 | 可直接发送 |
| MEDIUM | 50-79 | 建议人工审核 |
| HIGH | 20-49 | 必须人工审核 |
| CRITICAL | 0-19 | 需法务介入 |

## E-Signature Integration

After contract approval, use the e-signature integration:
```
esignature.send_for_signature(contract_id, signers)
```

Currently returns mock URL for testing.

## Example Workflow

1. **Negotiation Complete**:
   - 客户确认购买意向
   - 收集谈判结果（价格、条款、交付时间）

2. **Draft Contract**:
   ```
   draft_contract(
     customer_name="Acme Corp",
     contract_type="sales_contract",
     negotiation_summary={...},
     total_value=500000
   )
   ```

3. **Review Compliance Issues**:
   - Check missing_clauses
   - Review prohibited_found
   - Assess compliance_score

4. **Resolve Issues**:
   - Add missing clauses
   - Modify prohibited terms
   - Re-check compliance

5. **Send for Signature**:
   - Use e-signature integration
   - Track signing status

## Important Rules

1. **Always check compliance** before sending to customer
2. **Do not skip** high-risk issues
3. **Document** any custom clause additions
4. **Escalate** critical risk contracts to legal team

## Integration with Sales Pipeline

- **NEGOTIATION** stage: Draft contract after price agreement
- **CLOSE** stage: Finalize and send for signature
- If compliance score < 50, stay in NEGOTIATION