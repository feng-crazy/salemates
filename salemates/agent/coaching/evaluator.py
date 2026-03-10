"""Performance evaluator and default practice scenarios for sales coaching.

This module provides:
- DEFAULT_SCENARIOS: Predefined customer scenarios for training
- PerformanceEvaluator: Evaluates salesperson performance in practice sessions
"""

from salemates.agent.coaching.models import (
    CoachingSession,
    DialogueTurn,
    PerformanceScore,
    PracticeScenario,
    ScenarioDifficulty,
)

DEFAULT_SCENARIOS: list[PracticeScenario] = [
    PracticeScenario(
        id="price_sensitive",
        name="Price-Sensitive Procurement Manager",
        description="A procurement manager focused primarily on cost reduction. Will push hard on pricing and compare with cheaper alternatives.",
        customer_persona="Procurement Manager",
        industry="Manufacturing",
        difficulty=ScenarioDifficulty.INTERMEDIATE,
        initial_message="你好，我看了你们的产品介绍。坦白说，价格比我们预期的高了不少。我们之前用的供应商价格只有你们的一半。你们能给我一个理由为什么我应该选择你们吗？",
        personality_traits=["cost-focused", "direct", "skeptical", "detail-oriented"],
        common_objections=[
            "你们的价格太高了",
            "我们预算有限",
            "竞争对手的价格更便宜",
            "能不能再优惠一点？",
            "我需要和老板申请更多预算",
        ],
        decision_criteria=["price", "ROI", "payment terms", "total cost of ownership"],
        budget_range="¥30,000 - ¥50,000",
        timeline="Q2",
        pain_points=[
            "current vendor quality issues",
            "need better support",
            "integration challenges",
        ],
        competitors_considering=["竞品A (低价)", "竞品B (性价比)"],
    ),
    PracticeScenario(
        id="technical",
        name="Technical Decision Maker",
        description="A technical lead who wants to understand the technical details. Will ask deep questions about architecture, security, and integration.",
        customer_persona="Technical Director",
        industry="Technology",
        difficulty=ScenarioDifficulty.ADVANCED,
        initial_message="你好，我在评估几个解决方案。我需要了解你们的技术架构。你们是如何处理数据安全的？API的可用性如何？我们现有系统是微服务架构，你们能支持无缝集成吗？",
        personality_traits=["analytical", "detail-oriented", "skeptical", "well-informed"],
        common_objections=[
            "你们的技术架构不够现代化",
            "安全性方面有什么认证？",
            "我们需要的定制功能你们支持吗？",
            "性能测试数据有吗？",
            "技术支持响应时间是多少？",
        ],
        decision_criteria=[
            "security",
            "scalability",
            "integration",
            "API quality",
            "documentation",
        ],
        budget_range="¥100,000 - ¥200,000",
        timeline="Q1",
        pain_points=["current system performance issues", "security concerns", "need better API"],
        competitors_considering=["竞品C (技术领先)", "竞品D (开源方案)"],
    ),
    PracticeScenario(
        id="hesitant",
        name="Hesitant First-Time Buyer",
        description="A business owner who has never purchased this type of solution before. Needs education and reassurance.",
        customer_persona="Small Business Owner",
        industry="Retail",
        difficulty=ScenarioDifficulty.BEGINNER,
        initial_message="你好，我是朋友推荐来的。说实话，我对这类产品不太了解。你能简单介绍一下你们能帮我解决什么问题吗？我担心投资了之后用不起来...",
        personality_traits=["cautious", "relationship-focused", "value-seeking", "risk-averse"],
        common_objections=[
            "我不确定我们是否真的需要这个",
            "我担心学不会怎么用",
            "万一效果不好怎么办？",
            "有没有成功案例可以参考？",
            "能先试用一下吗？",
        ],
        decision_criteria=["ease of use", "support", "proven results", "risk reduction"],
        budget_range="¥10,000 - ¥30,000",
        timeline="灵活",
        pain_points=["manual processes", "time consuming tasks", "missing opportunities"],
        competitors_considering=["保持现状", "Excel/手动方案"],
    ),
    PracticeScenario(
        id="executive",
        name="C-Level Executive",
        description="A C-level executive who cares about strategic value and ROI. Will be brief and expect concise, value-focused answers.",
        customer_persona="CEO/CFO",
        industry="Finance",
        difficulty=ScenarioDifficulty.EXPERT,
        initial_message="我只有10分钟。你的团队说你们能帮我们提升运营效率。我关心的是：投入产出比是多少？实施周期多长？有什么风险？",
        personality_traits=["time-conscious", "strategic", "results-oriented", "decisive"],
        common_objections=[
            "这个投资回报周期太长了",
            "我们没有足够的内部资源支持实施",
            "风险控制措施是什么？",
            "我需要看到更具体的业务案例",
        ],
        decision_criteria=[
            "ROI",
            "strategic alignment",
            "risk",
            "implementation timeline",
            "executive support",
        ],
        budget_range="¥200,000+",
        timeline="本季度",
        pain_points=["operational inefficiency", "competitive pressure", "digital transformation"],
        competitors_considering=["竞品E (企业级)", "竞品F (定制方案)"],
    ),
    PracticeScenario(
        id="competitor_comparison",
        name="Active Competitor Evaluation",
        description="A prospect who is actively comparing you with a specific competitor. Will ask direct comparison questions.",
        customer_persona="IT Manager",
        industry="Healthcare",
        difficulty=ScenarioDifficulty.ADVANCED,
        initial_message="我们正在评估几个方案，包括你们和竞品X。说实话，他们的方案看起来也很不错，而且价格更有竞争力。你们相比他们有什么优势？",
        personality_traits=["analytical", "thorough", "fair", "experienced"],
        common_objections=[
            "竞品X的功能比你们多",
            "他们的客户案例更有说服力",
            "价格差距太大了",
            "他们的实施周期更短",
        ],
        decision_criteria=[
            "feature comparison",
            "total cost",
            "vendor stability",
            "implementation support",
        ],
        budget_range="¥80,000 - ¥120,000",
        timeline="下季度",
        pain_points=["current system limitations", "compliance requirements", "team adoption"],
        competitors_considering=["竞品X"],
    ),
]


class PerformanceEvaluator:
    """Evaluates salesperson performance in practice sessions.

    Analyzes dialogue history and provides scores across multiple
    dimensions of sales effectiveness.
    """

    def __init__(self) -> None:
        """Initialize the performance evaluator."""
        self._question_patterns = [
            "？",
            "吗？",
            "呢？",
            "什么",
            "怎么",
            "如何",
            "为什么",
            "哪些",
            "能否",
            "可以",
        ]
        self._closing_signals = [
            "签约",
            "合同",
            "付款",
            "下一步",
            "什么时候",
            "开始",
            "确定",
            "成交",
            "购买",
        ]
        self._empathy_markers = [
            "理解",
            "明白",
            "确实",
            "这很重要",
            "我完全",
            "您说得对",
            "您提到的",
        ]

    def evaluate(self, session: CoachingSession) -> PerformanceScore:
        """Evaluate a coaching session and return performance metrics.

        Args:
            session: The coaching session to evaluate.

        Returns:
            PerformanceScore with detailed metrics and feedback.
        """
        salesperson_turns = [t for t in session.dialogue_history if t.role == "salesperson"]

        if not salesperson_turns:
            return PerformanceScore(
                overall_score=0.0,
                session_id=session.id,
                strengths=[],
                areas_for_improvement=["No salesperson responses to evaluate"],
                specific_feedback=["The salesperson did not respond during the session."],
            )

        rapport_score = self._evaluate_rapport(salesperson_turns)
        discovery_score = self._evaluate_needs_discovery(salesperson_turns)
        knowledge_score = self._evaluate_product_knowledge(salesperson_turns)
        objection_score = self._evaluate_objection_handling(salesperson_turns, session)
        closing_score = self._evaluate_closing(salesperson_turns)
        clarity_score = self._evaluate_clarity(salesperson_turns)
        listening_score = self._evaluate_active_listening(session)

        weights = {
            "rapport": 0.15,
            "discovery": 0.2,
            "knowledge": 0.15,
            "objection": 0.15,
            "closing": 0.15,
            "clarity": 0.1,
            "listening": 0.1,
        }

        overall_score = (
            rapport_score * weights["rapport"]
            + discovery_score * weights["discovery"]
            + knowledge_score * weights["knowledge"]
            + objection_score * weights["objection"]
            + closing_score * weights["closing"]
            + clarity_score * weights["clarity"]
            + listening_score * weights["listening"]
        )

        strengths = self._identify_strengths(
            rapport_score,
            discovery_score,
            knowledge_score,
            objection_score,
            closing_score,
            clarity_score,
            listening_score,
        )
        improvements = self._identify_improvements(
            rapport_score,
            discovery_score,
            knowledge_score,
            objection_score,
            closing_score,
            clarity_score,
            listening_score,
        )
        feedback = self._generate_feedback(
            salesperson_turns, rapport_score, discovery_score, objection_score, closing_score
        )
        recommended_skills = self._recommend_skills(discovery_score, objection_score, closing_score)

        return PerformanceScore(
            overall_score=overall_score,
            rapport_building=rapport_score,
            needs_discovery=discovery_score,
            product_knowledge=knowledge_score,
            objection_handling=objection_score,
            closing_technique=closing_score,
            communication_clarity=clarity_score,
            active_listening=listening_score,
            strengths=strengths,
            areas_for_improvement=improvements,
            specific_feedback=feedback,
            recommended_skills=recommended_skills,
            session_id=session.id,
        )

    def _evaluate_rapport(self, turns: list[DialogueTurn]) -> float:
        """Evaluate rapport building based on empathy and personalization."""
        if not turns:
            return 0.0

        empathy_count = 0
        personalization_count = 0

        for turn in turns:
            content = turn.content.lower()
            for marker in self._empathy_markers:
                if marker in content:
                    empathy_count += 1
                    break

        first_turn = turns[0].content if turns else ""
        if any(marker in first_turn.lower() for marker in self._empathy_markers):
            personalization_count = 1

        empathy_score = min(empathy_count / len(turns), 1.0)
        return empathy_score * 0.8 + personalization_count * 0.2

    def _evaluate_needs_discovery(self, turns: list[DialogueTurn]) -> float:
        """Evaluate needs discovery based on questioning technique (SPIN)."""
        if not turns:
            return 0.0

        question_count = 0
        for turn in turns:
            for pattern in self._question_patterns:
                if pattern in turn.content:
                    question_count += 1
                    break

        question_ratio = question_count / len(turns)
        ideal_ratio = 0.4
        if question_ratio >= ideal_ratio:
            return min(question_ratio / ideal_ratio, 1.0)
        return question_ratio / ideal_ratio

    def _evaluate_product_knowledge(self, turns: list[DialogueTurn]) -> float:
        """Evaluate product knowledge based on feature mentions and accuracy."""
        if not turns:
            return 0.0

        feature_indicators = ["功能", "特点", "支持", "可以", "能够", "提供"]
        mention_count = 0
        for turn in turns:
            for indicator in feature_indicators:
                if indicator in turn.content:
                    mention_count += 1
                    break

        return min(mention_count / max(len(turns), 1), 1.0)

    def _evaluate_objection_handling(
        self, turns: list[DialogueTurn], session: CoachingSession
    ) -> float:
        """Evaluate objection handling based on addressing customer concerns."""
        if not turns or not session.scenario:
            return 0.5

        scenario_objections = session.scenario.common_objections
        addressed_count = 0

        for objection in scenario_objections:
            objection_keywords = [w for w in objection if len(w) > 1][:3]
            for turn in turns:
                if any(kw in turn.content for kw in objection_keywords):
                    addressed_count += 1
                    break

        if not scenario_objections:
            return 0.7
        return addressed_count / len(scenario_objections)

    def _evaluate_closing(self, turns: list[DialogueTurn]) -> float:
        """Evaluate closing technique based on commitment-seeking behavior."""
        if not turns:
            return 0.0

        closing_count = 0
        for turn in turns:
            for signal in self._closing_signals:
                if signal in turn.content:
                    closing_count += 1
                    break

        if len(turns) < 3:
            return min(closing_count * 0.3, 0.5)

        last_turns = turns[-2:] if len(turns) >= 2 else turns
        has_closing_attempt = any(
            any(signal in t.content for signal in self._closing_signals) for t in last_turns
        )

        base_score = min(closing_count / len(turns), 0.6)
        closing_bonus = 0.4 if has_closing_attempt else 0.0
        return min(base_score + closing_bonus, 1.0)

    def _evaluate_clarity(self, turns: list[DialogueTurn]) -> float:
        """Evaluate communication clarity based on message structure."""
        if not turns:
            return 0.0

        clarity_scores = []
        for turn in turns:
            content = turn.content
            score = 1.0

            if len(content) > 500:
                score -= 0.2
            if content.count("，") > 5:
                score -= 0.1
            if content.count("。") < 1 and len(content) > 50:
                score -= 0.1

            clarity_scores.append(max(score, 0.5))

        return sum(clarity_scores) / len(clarity_scores)

    def _evaluate_active_listening(self, session: CoachingSession) -> float:
        """Evaluate active listening based on responding to customer points."""
        customer_turns = [t for t in session.dialogue_history if t.role == "customer"]
        salesperson_turns = [t for t in session.dialogue_history if t.role == "salesperson"]

        if not customer_turns or not salesperson_turns:
            return 0.5

        response_relevance = 0
        for i, cust_turn in enumerate(customer_turns):
            if i + 1 <= len(salesperson_turns):
                sp_turn = (
                    salesperson_turns[i] if i < len(salesperson_turns) else salesperson_turns[-1]
                )
                cust_words = set(w for w in cust_turn.content if len(w) > 1)
                overlap = sum(1 for w in cust_words if w in sp_turn.content)
                if overlap > 0:
                    response_relevance += 1

        return min(response_relevance / len(customer_turns), 1.0) if customer_turns else 0.5

    def _identify_strengths(
        self,
        rapport: float,
        discovery: float,
        knowledge: float,
        objection: float,
        closing: float,
        clarity: float,
        listening: float,
    ) -> list[str]:
        """Identify areas where the salesperson performed well."""
        strengths = []
        if rapport >= 0.7:
            strengths.append("良好的亲和力建立，能够与客户建立信任关系")
        if discovery >= 0.7:
            strengths.append("有效的需求挖掘，善于提问了解客户需求")
        if knowledge >= 0.7:
            strengths.append("扎实的产品知识，能够清晰介绍产品价值")
        if objection >= 0.7:
            strengths.append("出色的异议处理，能够有效化解客户顾虑")
        if closing >= 0.7:
            strengths.append("良好的成交技巧，能够推动对话达成目标")
        if clarity >= 0.8:
            strengths.append("清晰的表达能力，沟通简洁有力")
        if listening >= 0.7:
            strengths.append("优秀的倾听能力，能够准确回应客户要点")
        return strengths

    def _identify_improvements(
        self,
        rapport: float,
        discovery: float,
        knowledge: float,
        objection: float,
        closing: float,
        clarity: float,
        listening: float,
    ) -> list[str]:
        """Identify areas needing improvement."""
        improvements = []
        if rapport < 0.5:
            improvements.append("需要加强亲和力建立，尝试更多同理心表达")
        if discovery < 0.5:
            improvements.append("需要加强需求挖掘，多使用开放式问题")
        if knowledge < 0.5:
            improvements.append("需要加强产品知识，准备更详细的产品介绍")
        if objection < 0.5:
            improvements.append("需要加强异议处理能力，准备常见异议的回答")
        if closing < 0.5:
            improvements.append("需要加强成交技巧，主动引导下一步行动")
        if clarity < 0.6:
            improvements.append("需要提高沟通清晰度，避免过长或结构混乱的回答")
        if listening < 0.5:
            improvements.append("需要加强倾听能力，更关注客户的具体关注点")
        return improvements

    def _generate_feedback(
        self,
        turns: list[DialogueTurn],
        rapport: float,
        discovery: float,
        objection: float,
        closing: float,
    ) -> list[str]:
        """Generate specific actionable feedback."""
        feedback = []

        if discovery < 0.6:
            feedback.append(
                "建议使用SPIN方法论，先了解现状(S)、发现问题(P)、探索影响(I)、确认需求(N)"
            )
        if objection < 0.6:
            feedback.append("面对价格异议时，强调价值而非降价；面对功能异议时，用案例证明效果")
        if closing < 0.6 and len(turns) >= 3:
            feedback.append(
                "对话后期可以尝试总结价值并建议下一步行动，如'那我帮您准备一份方案，您看如何？'"
            )

        if len(turns) < 2:
            feedback.append("建议进行更深入的对话，充分展示您的销售技巧")
        elif len(turns) > 10:
            feedback.append("对话较长，注意把握节奏，适时推动下一步")

        return feedback

    def _recommend_skills(
        self,
        discovery: float,
        objection: float,
        closing: float,
    ) -> list[str]:
        """Recommend skills for the salesperson to study."""
        skills = []
        if discovery < 0.6:
            skills.append("spin_selling")
        if objection < 0.6:
            skills.append("objection_handling")
        if closing < 0.6:
            skills.append("fab_selling")
        return skills
