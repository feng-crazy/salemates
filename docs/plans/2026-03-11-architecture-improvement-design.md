# SaleMates AI 架构改进设计方案

**日期**: 2026-03-11
**状态**: 设计完成，待实现
**作者**: 设计讨论

---

## 一、背景与问题

### 1.1 当前架构问题

通过对代码的深入分析，发现以下关键问题：

1. **安全系统组件未完全集成**: GuardrailManager、ConfidenceRouter、HumanHandoffManager 虽然已实现，但未在 AgentLoop 中真正调用
2. **方法论与Tool断层**: SPIN/FAB/BANT 的 SKILL.md 存在，但缺乏自动触发机制
3. **README与代码不同步**: 多个模块标注"0%"完成度，但实际已有完整实现

### 1.2 组件实现状态

| 组件 | 文件 | 代码行数 | Loop集成状态 |
|------|------|---------|-------------|
| GuardrailManager | guardrails.py | 699 | ❌ 未调用 |
| EmotionFuse | emotion_fuse.py | 433 | ✅ 已调用 |
| ConfidenceRouter | confidence_router.py | 314 | ❌ 未初始化 |
| HumanHandoffManager | human_handoff.py | 717 | ❌ 未调用 |
| SalesStageStateMachine | state_machine.py | 323 | ❌ 未集成 |

---

## 二、设计决策

### 2.1 安全检查位置

**决策：双向检查（输入侧 + 输出侧）**

```
输入侧：
- EmotionFuse 情绪熔断判断
- 置信度预评估

输出侧：
- GuardrailManager 检查响应内容
- 价格/合同/功能/竞品 四类围栏
```

**原因**：
- 输入侧可快速拦截高风险场景（愤怒客户、敏感关键词）
- 输出侧可防止AI生成违规内容（超授权报价、合同承诺）
- 双重保护确保安全边界

### 2.2 方法论集成方式

**决策：提示词注入**

根据当前销售阶段（Discovery/Presentation/Negotiation），自动将 SPIN/FAB/BANT 方法论指令注入到系统提示词中，LLM 自然遵循方法论进行对话。

**原因**：
- 最优雅，不改变现有架构
- LLM 已有足够能力理解和遵循方法论
- 便于迭代调整方法论内容

---

## 三、架构改进方案

### 3.1 改进后的 AgentLoop 流程

```
AgentLoop._process_message()
    │
    ├── Phase 1: 输入分析
    │   ├── IntentRecognizer → 意图识别
    │   └── EmotionAnalyzer → 情绪分析
    │
    ├── Phase 2: 输入安全检查 (Input Guards)
    │   └── EmotionFuse.check()
    │       └── requires_human? → 直接转人工
    │
    ├── Phase 3: 置信度预评估
    │   └── ConfidenceRouter.estimate()
    │       ├── LOW (<60%) → 直接转人工
    │       ├── MEDIUM (60-85%) → 生成草稿，人工审核
    │       └── HIGH (>85%) → 正常处理
    │
    ├── Phase 4: LLM处理 + 方法论注入
    │   ├── SalesStageStateMachine.get_stage()
    │   ├── MethodologyPromptInjector.inject() → 系统提示词
    │   └── _run_agent_loop() → LLM → Tools
    │
    ├── Phase 5: 输出安全检查 (Output Guards)
    │   └── GuardrailManager.check(response)
    │       ├── BLOCK → 阻止发送，转人工
    │       ├── REVIEW → 标记需复核
    │       └── WARNING → 记录日志，允许发送
    │
    └── Phase 6: 响应发送 / 人工交接
```

### 3.2 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         全渠道接入层                             │
│  飞书 │ 钉钉 │ 企业微信 │ Telegram │ Slack │ WhatsApp           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────┼─────────────────────────────────────┐
│                    网关层 │                                      │
│              HTTP Gateway Server                                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────┼─────────────────────────────────────┐
│                    AgentLoop (改进版)                            │
│                                                                  │
│  Phase 1: 输入分析                                               │
│  ┌─────────────┐  ┌─────────────┐                               │
│  │   Intent    │  │   Emotion   │                               │
│  │ Recognizer  │  │  Analyzer   │                               │
│  └─────────────┘  └─────────────┘                               │
│                                                                  │
│  Phase 2: 输入安全检查 (Input Guards)                            │
│  ┌─────────────┐                                                │
│  │ EmotionFuse │ → requires_human? → 转人工                     │
│  └─────────────┘                                                │
│                                                                  │
│  Phase 3: 置信度预评估                                           │
│  ┌─────────────────┐                                            │
│  │ ConfidenceRouter│ → LOW → 转人工                             │
│  │                 │ → MEDIUM → 草稿审核                         │
│  └─────────────────┘ → HIGH → 正常处理                          │
│                                                                  │
│  Phase 4: LLM处理 + 方法论注入                                   │
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │ SalesStage      │ →  │ Methodology     │ → 系统提示词         │
│  │ StateMachine    │    │ PromptInjector  │                     │
│  └─────────────────┘    └─────────────────┘                     │
│                           │                                      │
│                    ┌──────┴──────┐                               │
│                    │     LLM     │                               │
│                    └──────┬──────┘                               │
│                           │                                      │
│                    ┌──────┴──────┐                               │
│                    │    Tools    │                               │
│                    └─────────────┘                               │
│                                                                  │
│  Phase 5: 输出安全检查 (Output Guards)                           │
│  ┌─────────────────┐                                            │
│  │ GuardrailManager│ → BLOCK → 阻止,转人工                      │
│  │   - Price       │ → REVIEW → 标记复核                        │
│  │   - Contract    │ → WARNING → 日志,允许                      │
│  │   - Feature     │                                            │
│  │   - Competitor  │                                            │
│  └─────────────────┘                                            │
│                                                                  │
│  Phase 6: 人工交接 (按需)                                        │
│  ┌─────────────────┐                                            │
│  │ HumanHandoff    │ - Feishu卡片通知                           │
│  │ Manager         │ - 暂停自动回复                              │
│  │                 │ - 完整上下文传递                            │
│  └─────────────────┘                                            │
└──────────────────────────────────────────────────────────────────┘
                            │
                     ┌──────┴──────┐
                     │   响应发送   │
                     └─────────────┘
```

### 3.3 方法论注入设计

```python
class MethodologyPromptInjector:
    """根据销售阶段注入方法论提示词"""
    
    STAGE_METHODOLOGY_MAP = {
        SalesStage.DISCOVERY: {
            "primary": "SPIN",
            "instructions": """
## SPIN Selling Framework (Discovery Stage)

Focus on understanding the customer's situation through:

1. **Situation Questions**: Understand current state
   - "Can you tell me about your current process for...?"
   - "How does your team currently handle...?"

2. **Problem Questions**: Identify challenges
   - "What challenges do you face with...?"
   - "Where do you see the biggest bottlenecks?"

3. **Implication Questions**: Explore consequences
   - "How does this affect your team's productivity?"
   - "What happens if this isn't addressed?"

4. **Need-Payoff Questions**: Envision solution
   - "How would solving this impact your business?"

DO NOT jump to pricing or solution presentation at this stage.
"""
        },
        SalesStage.PRESENTATION: {
            "primary": "FAB",
            "instructions": """
## FAB Framework (Presentation Stage)

Structure your solution presentation:

1. **Features**: What the product does
2. **Advantages**: What the feature does
3. **Benefits**: Why it matters to the customer

Connect each feature to the customer's stated pain points.
"""
        },
        SalesStage.NEGOTIATION: {
            "primary": "BANT",
            "instructions": """
## BANT Qualification (Negotiation Stage)

Verify the deal qualification:

1. **Budget**: "Has budget been allocated?"
2. **Authority**: "Who else needs to approve?"
3. **Need**: "On a scale of 1-10, how critical is this?"
4. **Timeline**: "What's your target implementation date?"

Address objections with value, not discounts.
"""
        }
    }
```

---

## 四、实现计划

### 4.1 优先级与工作量

| 优先级 | 改动项 | 文件 | 工作量 | 依赖 |
|-------|-------|------|-------|-----|
| P0 | 在loop中集成GuardrailManager | loop.py | 小 | 无 |
| P0 | 在loop中集成ConfidenceRouter | loop.py | 小 | 无 |
| P0 | 新增_handle_handoff方法 | loop.py | 中 | 无 |
| P1 | 新增MethodologyPromptInjector | strategies/injector.py | 中 | 无 |
| P1 | 在loop中跟踪SalesStage | loop.py | 中 | 无 |
| P2 | 集成HumanHandoffManager | loop.py | 中 | P0 |
| P2 | 更新README反映真实状态 | README.md | 小 | 无 |

### 4.2 关键代码改动

**loop.py 改动点：**

```python
# 1. __init__ 中新增初始化
self.confidence_router = ConfidenceRouter()  # 新增
self.handoff_manager = HumanHandoffManager(...)  # 新增
self.methodology_injector = MethodologyPromptInjector()  # 新增

# 2. _process_message 中新增 Phase 3, 5
# 按照上述流程实现

# 3. 新增 _handle_handoff 方法
async def _handle_handoff(
    self, 
    trigger: HandoffTrigger, 
    context: dict
) -> OutboundMessage:
    """统一的人工交接处理"""
    ...
```

---

## 五、验收标准

### 5.1 功能验收

- [ ] GuardrailManager 在 LLM 输出后检查响应内容
- [ ] ConfidenceRouter 根据置信度路由到不同处理路径
- [ ] EmotionFuse 正确触发情绪熔断
- [ ] HumanHandoffManager 发送 Feishu 通知
- [ ] MethodologyPromptInjector 根据阶段注入方法论
- [ ] SalesStageStateMachine 跟踪阶段变化

### 5.2 测试场景

1. **情绪熔断测试**: 发送"我要投诉"，验证是否转人工
2. **价格围栏测试**: AI尝试给出超授权折扣，验证是否被阻止
3. **置信度路由测试**: 低置信度场景验证是否转人工
4. **方法论注入测试**: 验证不同阶段系统提示词是否正确

---

## 六、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 双向检查增加延迟 | 用户体验 | 并行执行安全检查 |
| 误判导致频繁转人工 | 人工负担 | 基于生产数据校准阈值 |
| 方法论注入效果不稳定 | 销售效果 | 监控对话质量，迭代优化 |

---

## 七、参考资源

- [AI Agent Human Handoff Research](https://zylos.ai/research/2026-01-30-ai-agent-human-handoff)
- [Agent Governance Patterns](https://a21.ai/agent-governance-patterns-policy-as-code-for-live-systems/)
- [AI Guardrails Production Guide](https://myengineeringpath.dev/genai-engineer/ai-guardrails/)
- [Nevron Human Handoff Implementation](https://github.com/axioma-ai-labs/nevron/blob/main/src/metacognition/human_handoff.py)