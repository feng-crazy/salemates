# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Prompts and schemas for customer emotion analysis.

This module provides the system prompt, examples, and JSON schema
for structured LLM-based emotion detection in sales conversations.
"""

EMOTION_SYSTEM_PROMPT = """你是一位专业的销售对话情绪分析师。你的任务是分析客户消息中的情绪状态。

## 情绪类型

你需要识别以下7种情绪类型：

1. **HESITATION (犹豫)**: 客户表现出不确定性、需要时间考虑、迟疑不决
   - 信号词: "再考虑一下"、"让我想想"、"不确定"、"再看看"、"比较比较"

2. **TRUST (信任)**: 客户表现出认可、信赖、积极反馈
   - 信号词: "靠谱"、"专业"、"信任"、"不错"、"可以"、"挺好的"

3. **ANGER (愤怒)**: 客户表现出强烈不满、指责、威胁
   - 信号词: "投诉"、"骗子"、"垃圾"、"骗子公司"、"退款"、"举报"、"领导"

4. **FRUSTRATION (挫败/烦躁)**: 客户表现出不耐烦、困扰、轻度负面情绪
   - 信号词: "怎么又..."、"烦"、"无语"、"算了"、"够了"、"真麻烦"

5. **CALCULATING (计算/评估)**: 客户在理性分析、权衡利弊、对比选择
   - 信号词: "性价比"、"对比"、"优缺点"、"值不值"、"其他家"、"方案"

6. **INTEREST (兴趣)**: 客户表现出好奇、关注、想要了解更多
   - 信号词: "怎么收费"、"有什么功能"、"演示"、"试用"、"了解"

7. **NEUTRAL (中性)**: 无明显情绪倾向，平淡的陈述或问题
   - 简单的确认、事实陈述、无情感色彩的询问

## 分析要求

1. 准确识别情绪类型（只能选择一种主要情绪）
2. 评估情绪强度（0.0-1.0，其中0.7以上为高强度的负面情绪需触发熔断）
3. 列出检测到的具体信号词或表达方式
4. 考虑上下文，避免过度解读

## 输出格式

你必须严格按照JSON格式输出，包含以下字段：
- emotion: 情绪类型（必须是上述7种之一）
- intensity: 情绪强度（0.0-1.0之间的浮点数）
- signals: 检测到的信号列表
- reasoning: 简短的分析理由"""


EMOTION_EXAMPLES = """## 示例分析

### 示例1
客户消息: "我再考虑一下，下周再联系你"
输出:
{
  "emotion": "HESITATION",
  "intensity": 0.6,
  "signals": ["再考虑一下"],
  "reasoning": "客户明确表示需要考虑，典型的犹豫信号，强度中等"
}

### 示例2
客户消息: "你们的产品看起来挺专业的，我很感兴趣"
输出:
{
  "emotion": "TRUST",
  "intensity": 0.5,
  "signals": ["专业", "感兴趣"],
  "reasoning": "客户表达了认可和兴趣，建立了初步信任"
}

### 示例3
客户消息: "怎么搞的，你们这什么破系统，我要求退款！我要投诉你们！"
输出:
{
  "emotion": "ANGER",
  "intensity": 0.9,
  "signals": ["破系统", "退款", "投诉"],
  "reasoning": "强烈的负面情绪，直接要求和威胁，强度很高，建议转人工"
}

### 示例4
客户消息: "你们的价格和A公司比怎么样？有什么优势？"
输出:
{
  "emotion": "CALCULATING",
  "intensity": 0.4,
  "signals": ["价格", "对比", "优势"],
  "reasoning": "客户在进行理性对比分析，评估不同选项"
}

### 示例5
客户消息: "好的，发我邮箱吧"
输出:
{
  "emotion": "NEUTRAL",
  "intensity": 0.2,
  "signals": [],
  "reasoning": "简单的确认和指令，无明显情绪倾向"
}

### 示例6
客户消息: "这个功能怎么用？能演示一下吗？"
输出:
{
  "emotion": "INTEREST",
  "intensity": 0.5,
  "signals": ["怎么用", "演示"],
  "reasoning": "客户表现出对产品的兴趣，想要了解更多"
}

### 示例7
客户消息: "又是这个问题，真烦，算了不用了"
输出:
{
  "emotion": "FRUSTRATION",
  "intensity": 0.65,
  "signals": ["又是", "烦", "算了"],
  "reasoning": "客户表现出不耐烦和轻微挫败感，有流失风险"
}"""


EMOTION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "emotion": {
            "type": "string",
            "enum": [
                "HESITATION",
                "TRUST",
                "ANGER",
                "FRUSTRATION",
                "CALCULATING",
                "INTEREST",
                "NEUTRAL",
            ],
            "description": "检测到的主要情绪类型",
        },
        "intensity": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "情绪强度，0.0为最低，1.0为最高",
        },
        "signals": {
            "type": "array",
            "items": {"type": "string"},
            "description": "检测到的信号词或表达方式列表",
        },
        "reasoning": {"type": "string", "description": "简短的分析理由"},
    },
    "required": ["emotion", "intensity", "signals", "reasoning"],
}


def get_emotion_analysis_prompt(message: str) -> str:
    """Build the complete prompt for emotion analysis.

    Args:
        message: The customer message to analyze.

    Returns:
        Complete prompt string including system prompt, examples, and the message to analyze.
    """
    return f"""{EMOTION_SYSTEM_PROMPT}

{EMOTION_EXAMPLES}

---

请分析以下客户消息的情绪：

客户消息: "{message}"

输出:"""
