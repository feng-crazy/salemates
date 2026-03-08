# Copyright (c) 2026 SalesMate Team
# SPDX-License-Identifier: Apache-2.0

"""Mock customer data for testing SalesMate"""

# Sample customer conversations
SAMPLE_CONVERSATIONS = [
    {
        "conversation_id": "conv_001",
        "customer_name": "张总",
        "company": "某科技公司",
        "stage": "discovery",
        "messages": [
            {
                "role": "customer",
                "content": "你好，我想了解一下你们的产品",
                "timestamp": "2026-03-08T10:00:00Z",
            },
            {
                "role": "agent",
                "content": "您好！很高兴为您介绍。我们的产品是一套智能销售解决方案...",
                "timestamp": "2026-03-08T10:00:05Z",
            },
            {
                "role": "customer",
                "content": "我现在用的系统操作太复杂了，团队很多人不会用",
                "timestamp": "2026-03-08T10:01:00Z",
            },
        ],
        "detected_intent": "product_inquiry",
        "detected_emotion": "neutral",
        "bant_qualification": {"budget": None, "authority": True, "need": True, "timeline": None},
    },
    {
        "conversation_id": "conv_002",
        "customer_name": "李经理",
        "company": "某制造企业",
        "stage": "negotiation",
        "messages": [
            {
                "role": "customer",
                "content": "能再便宜一点吗？别的供应商报价比你们低20%",
                "timestamp": "2026-03-08T14:00:00Z",
            },
            {
                "role": "agent",
                "content": "我理解您关注成本。让我分享一下我们的ROI分析...",
                "timestamp": "2026-03-08T14:00:10Z",
            },
        ],
        "detected_intent": "price_negotiation",
        "detected_emotion": "hesitant",
        "bant_qualification": {
            "budget": "50-100万",
            "authority": True,
            "need": True,
            "timeline": "Q2",
        },
    },
    {
        "conversation_id": "conv_003",
        "customer_name": "王总监",
        "company": "某金融机构",
        "stage": "presentation",
        "messages": [
            {
                "role": "customer",
                "content": "我们需要一套能对接现有CRM的系统",
                "timestamp": "2026-03-08T16:00:00Z",
            },
            {
                "role": "customer",
                "content": "数据安全是我们最看重的一点",
                "timestamp": "2026-03-08T16:01:00Z",
            },
        ],
        "detected_intent": "requirements_clarification",
        "detected_emotion": "interested",
        "bant_qualification": {
            "budget": "100万以上",
            "authority": True,
            "need": True,
            "timeline": "Q3",
        },
    },
]

# Sample product knowledge base
PRODUCT_KB = {
    "features": [
        {
            "name": "智能客户识别",
            "description": "基于NLP自动识别客户意图和情绪",
            "category": "core",
        },
        {
            "name": "多渠道接入",
            "description": "支持飞书、钉钉、企业微信等主流平台",
            "category": "integration",
        },
        {"name": "销售阶段管理", "description": "自动化销售漏斗和阶段转换", "category": "sales"},
        {"name": "知识库问答", "description": "基于企业文档的智能问答", "category": "core"},
    ],
    "pricing_tiers": [
        {
            "name": "基础版",
            "price": "999/月",
            "features": ["基础客服", "飞书接入", "知识库(100条)"],
        },
        {
            "name": "专业版",
            "price": "2999/月",
            "features": ["全部基础功能", "多渠道接入", "知识库(无限制)", "销售分析"],
        },
        {
            "name": "企业版",
            "price": "面议",
            "features": ["全部专业功能", "私有化部署", "专属客服", "定制开发"],
        },
    ],
}

# Sample objection handling patterns
OBJECTION_PATTERNS = {
    "price_too_high": {
        "keywords": ["贵", "太贵", "便宜", "价格"],
        "response_strategy": "focus_on_roi",
        "templates": [
            "我理解您对成本的关注。让我分享一个数据：我们客户平均ROI是300%...",
            "相比节省的成本，购买我们的解决方案实际上是省钱...",
        ],
    },
    "need_more_time": {
        "keywords": ["考虑", "商量", "再看看", "不急"],
        "response_strategy": "spin_probing",
        "templates": [
            "完全理解您需要时间考虑。您最关注的是哪些方面？",
            "方便了解一下您还在考虑其他选择吗？",
        ],
    },
    "competitor_comparison": {
        "keywords": ["别人", "竞品", "别的", "XX家"],
        "response_strategy": "differentiation",
        "templates": [
            "每个方案都有自己的优势。您最看重哪些方面？",
            "如果您方便的话，可以分享竞品的哪些特点更吸引您吗？",
        ],
    },
}
