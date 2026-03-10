"""Sales Coach Tool for practice and assist modes.

This tool provides:
- Practice mode: AI acts as customer for sales training
- Assist mode: Real-time strategy suggestions for live conversations
"""

from typing import Any, Optional

from loguru import logger

from salemates.agent.coaching import (
    DEFAULT_SCENARIOS,
    CoachingMode,
    CoachingSession,
    PerformanceEvaluator,
    PracticeScenario,
)
from salemates.agent.tools.base import Tool, ToolContext


class SalesCoachTool(Tool):
    """Tool for sales coaching with practice and assist modes.

    In PRACTICE mode, the AI acts as the customer, responding to the
    salesperson's messages and maintaining the role throughout the session.

    In ASSIST mode, the AI provides strategic suggestions for handling
    real customer conversations.

    Attributes:
        _sessions: Active coaching sessions by session ID.
        _evaluator: Performance evaluator for scoring sessions.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, CoachingSession] = {}
        self._evaluator = PerformanceEvaluator()

    @property
    def name(self) -> str:
        return "sales_coach"

    @property
    def description(self) -> str:
        return (
            "Sales coaching tool for training and assistance. "
            "Modes: 'practice' (AI acts as customer for training), "
            "'assist' (AI suggests strategy for real conversations). "
            "Use 'start_session' to begin, 'respond' to continue dialogue, "
            "'end_session' to finish and get performance feedback."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform",
                    "enum": [
                        "start_session",
                        "respond",
                        "end_session",
                        "list_scenarios",
                        "get_scenario",
                        "get_session_status",
                    ],
                },
                "mode": {
                    "type": "string",
                    "description": "Coaching mode (for start_session)",
                    "enum": ["practice", "assist"],
                },
                "scenario_id": {
                    "type": "string",
                    "description": "Scenario ID for practice mode (e.g., 'price_sensitive', 'technical')",
                },
                "session_id": {
                    "type": "string",
                    "description": "Session ID for ongoing sessions",
                },
                "user_message": {
                    "type": "string",
                    "description": "Salesperson's message (for respond action)",
                },
                "customer_context": {
                    "type": "object",
                    "description": "Context for assist mode (customer info, conversation history)",
                },
            },
            "required": ["action"],
        }

    async def execute(self, tool_context: ToolContext, **kwargs: Any) -> str:
        action = kwargs.get("action")

        try:
            if action == "start_session":
                return await self._start_session(kwargs)
            elif action == "respond":
                return await self._respond(kwargs)
            elif action == "end_session":
                return await self._end_session(kwargs)
            elif action == "list_scenarios":
                return self._list_scenarios()
            elif action == "get_scenario":
                return self._get_scenario(kwargs.get("scenario_id"))
            elif action == "get_session_status":
                return self._get_session_status(kwargs.get("session_id"))
            else:
                return f"Error: Unknown action: {action}"
        except Exception as e:
            logger.exception(f"Sales coach tool error: {e}")
            return f"Error executing {action}: {str(e)}"

    async def _start_session(self, kwargs: dict[str, Any]) -> str:
        mode_str = kwargs.get("mode", "practice")
        mode = CoachingMode(mode_str)
        scenario_id = kwargs.get("scenario_id")

        session = CoachingSession(mode=mode)

        if mode == CoachingMode.PRACTICE:
            scenario = self._find_scenario(scenario_id)
            if not scenario:
                return self._list_scenarios() + "\n\n请指定一个有效的 scenario_id 开始练习。"

            session.scenario_id = scenario.id
            session.scenario = scenario

            session.customer_context = {
                "name": f"{scenario.customer_persona}",
                "company": f"{scenario.industry}公司",
                "personality": scenario.personality_traits,
                "objections_remaining": list(scenario.common_objections),
                "stage": "greeting",
            }

            session.add_turn("customer", scenario.initial_message)

            self._sessions[session.id] = session

            return (
                f"🎯 开始销售练习会话\n"
                f"会话ID: {session.id}\n"
                f"场景: {scenario.name}\n"
                f"难度: {scenario.difficulty.value}\n"
                f"客户角色: {scenario.customer_persona}\n\n"
                f"--- 客户消息 ---\n{scenario.initial_message}\n\n"
                f"请作为销售人员回复客户。使用 'respond' 动作继续对话。"
            )

        else:
            customer_context = kwargs.get("customer_context", {})
            session.customer_context = customer_context
            self._sessions[session.id] = session

            return (
                f"💡 开始销售辅助会话\n"
                f"会话ID: {session.id}\n\n"
                f"请告诉我客户的当前情况或消息，我将提供策略建议。"
                f"使用 'respond' 动作并提供 'customer_context' 获取建议。"
            )

    async def _respond(self, kwargs: dict[str, Any]) -> str:
        session_id = kwargs.get("session_id")
        user_message = kwargs.get("user_message")

        if not session_id:
            return "Error: session_id is required"

        session = self._sessions.get(session_id)
        if not session:
            return f"Error: Session {session_id} not found. Please start a new session."

        if not session.is_active:
            return "Error: This session has ended. Please start a new session."

        if session.mode == CoachingMode.PRACTICE:
            return self._handle_practice_response(session, user_message)
        else:
            return self._handle_assist_response(session, kwargs)

    def _handle_practice_response(self, session: CoachingSession, user_message: str) -> str:
        if not user_message:
            return "Error: user_message is required in practice mode"

        session.add_turn("salesperson", user_message)

        scenario = session.scenario
        if not scenario:
            return "Error: Scenario not found for this session."

        customer_response = self._generate_customer_response(session, scenario)
        session.add_turn("customer", customer_response)

        return (
            f"--- 客户回复 ---\n{customer_response}\n\n"
            f"💡 提示: 使用 'respond' 继续对话，或 'end_session' 结束练习并获取评分。"
        )

    def _generate_customer_response(
        self, session: CoachingSession, scenario: PracticeScenario
    ) -> str:
        import random

        sp_turns = [t for t in session.dialogue_history if t.role == "salesperson"]
        last_sp_message = sp_turns[-1].content if sp_turns else ""

        context = session.customer_context
        stage = context.get("stage", "greeting")

        if stage == "greeting":
            if any(q in last_sp_message for q in ["？", "吗", "什么", "怎么"]):
                context["stage"] = "exploring"
                pain_point = (
                    random.choice(scenario.pain_points)
                    if scenario.pain_points
                    else "我们的工作流程需要改进"
                )
                return f"{pain_point}。不过我也在考虑其他方案，你们相比其他供应商有什么优势？"
            return "嗯，我明白。不过我还是有点担心，毕竟这是我们第一次尝试这类方案。"

        if stage == "exploring":
            if any(obj in last_sp_message for obj in ["价格", "成本", "费用", "预算"]):
                context["stage"] = "pricing"
                return f"价格方面...我们预算大概{scenario.budget_range or '需要确认'}。说实话，你们的价格比我们预想的高一些。能给个折扣吗？"

            if any(obj in last_sp_message for obj in ["竞品", "其他", "对比", "区别"]):
                objection = (
                    random.choice(scenario.common_objections)
                    if scenario.common_objections
                    else "你们的优势确实不错，但我需要再比较一下。"
                )
                return objection

            if len(sp_turns) >= 3:
                context["stage"] = "deciding"
                return "听起来你们的产品确实不错。我需要和团队讨论一下。下一步我们应该怎么推进？"

            return "这一点我理解。但我们目前用的方案也还可以，换新系统的成本不低..."

        if stage == "pricing":
            if any(sig in last_sp_message for sig in ["价值", "ROI", "回报", "效果"]):
                return "价值我能理解...让我再考虑一下。能发一份详细的方案给我吗？我可以和老板汇报。"
            return "嗯，我需要再算算整体成本。这个价格确实有点超出预算了。"

        if stage == "deciding":
            if any(sig in last_sp_message for sig in ["下一步", "方案", "演示", "试用"]):
                context["stage"] = "closing"
                return "好的，那先准备一份方案吧。大概什么时候能给我？"
            return "让我想想...这个问题比较重要，我需要更多时间考虑。"

        if stage == "closing":
            return "好的，我会仔细看一下方案。有任何问题我再联系你。"

        return "我还需要再了解一下..."

    def _handle_assist_response(self, session: CoachingSession, kwargs: dict[str, Any]) -> str:
        customer_context = kwargs.get("customer_context", {})
        user_message = kwargs.get("user_message", "")

        if customer_context:
            session.customer_context.update(customer_context)

        ctx = session.customer_context
        customer_message = ctx.get("last_customer_message", user_message)

        suggestions = self._generate_assist_suggestions(customer_message, ctx)

        session.add_turn("salesperson", user_message, {"suggestions": suggestions})

        return suggestions

    def _generate_assist_suggestions(self, customer_message: str, context: dict[str, Any]) -> str:
        suggestions = []
        customer_message_lower = customer_message.lower() if customer_message else ""

        price_keywords = ["价格", "贵", "便宜", "成本", "预算", "折扣", "优惠"]
        if any(kw in customer_message_lower for kw in price_keywords):
            suggestions.append(
                "💡 **价格异议处理建议**:\n"
                "1. 不要立即降价，先强调价值\n"
                "2. 使用 FAB 话术: 功能→优势→利益\n"
                "3. 示例: '我理解价格是重要考量。我们的产品虽然初期投入较高，但能帮您节省XX%的运营成本...'"
            )

        competitor_keywords = ["竞品", "其他", "对比", "区别", "他们"]
        if any(kw in customer_message_lower for kw in competitor_keywords):
            suggestions.append(
                "💡 **竞品对比建议**:\n"
                "1. 不贬低竞品，强调自身优势\n"
                "2. 聚焦客户需求，而非产品对比\n"
                "3. 示例: '每个方案都有其优势。根据您的需求XX，我们的优势在于...'"
            )

        hesitation_keywords = ["考虑", "等等", "再看看", "商量", "不确定"]
        if any(kw in customer_message_lower for kw in hesitation_keywords):
            suggestions.append(
                "💡 **犹豫处理建议**:\n"
                "1. 使用 SPIN 提问了解真正顾虑\n"
                "2. 问题示例: '完全理解，您主要在考虑哪方面呢？是价格、功能还是其他？'\n"
                "3. 探索影响: '如果这个问题不解决，对您接下来的计划会有什么影响？'"
            )

        technical_keywords = ["技术", "架构", "API", "安全", "性能", "集成"]
        if any(kw in customer_message_lower for kw in technical_keywords):
            suggestions.append(
                "💡 **技术问题处理建议**:\n"
                "1. 展示专业知识，但避免过于技术化\n"
                "2. 将技术特性转化为业务价值\n"
                "3. 示例: '我们的API响应时间在100ms以内，这意味着您的团队可以...'"
            )

        if not suggestions:
            suggestions.append(
                "💡 **通用销售建议**:\n"
                "1. 继续使用 SPIN 方法挖掘需求\n"
                "2. 确认理解: '让我确认一下，您的主要需求是...'\n"
                "3. 推进对话: '基于我们的讨论，您觉得下一步怎么做比较合适？'"
            )

        suggestions.append("\n📚 推荐技能: spin_selling, fab_selling, objection_handling")

        return "\n\n".join(suggestions)

    async def _end_session(self, kwargs: dict[str, Any]) -> str:
        session_id = kwargs.get("session_id")

        if not session_id:
            return "Error: session_id is required"

        session = self._sessions.get(session_id)
        if not session:
            return f"Error: Session {session_id} not found."

        session.end_session()

        if session.mode == CoachingMode.PRACTICE:
            score = self._evaluator.evaluate(session)
            return (
                f"📊 练习结束！\n\n"
                f"{score.get_summary()}\n\n"
                f"--- 对话记录 ---\n{session.get_dialogue_summary()}"
            )
        else:
            return (
                f"辅助会话已结束。\n会话ID: {session_id}\n对话轮数: {len(session.dialogue_history)}"
            )

    def _list_scenarios(self) -> str:
        lines = ["📋 可用的练习场景:\n"]
        for scenario in DEFAULT_SCENARIOS:
            lines.append(
                f"• {scenario.id}: {scenario.name}\n"
                f"  难度: {scenario.difficulty.value} | 行业: {scenario.industry}\n"
                f"  描述: {scenario.description}\n"
            )
        lines.append("使用 'start_session' 并指定 scenario_id 开始练习。")
        return "\n".join(lines)

    def _get_scenario(self, scenario_id: Optional[str]) -> str:
        if not scenario_id:
            return "Error: scenario_id is required"

        scenario = self._find_scenario(scenario_id)
        if not scenario:
            return f"Error: Scenario '{scenario_id}' not found. Use 'list_scenarios' to see available scenarios."

        return (
            f"📋 场景详情: {scenario.name}\n\n"
            f"ID: {scenario.id}\n"
            f"描述: {scenario.description}\n"
            f"客户角色: {scenario.customer_persona}\n"
            f"行业: {scenario.industry}\n"
            f"难度: {scenario.difficulty.value}\n\n"
            f"性格特点: {', '.join(scenario.personality_traits)}\n"
            f"常见异议: {', '.join(scenario.common_objections[:3])}...\n"
            f"决策因素: {', '.join(scenario.decision_criteria)}\n"
            f"预算范围: {scenario.budget_range or '未指定'}\n"
            f"时间线: {scenario.timeline or '未指定'}\n"
        )

    def _get_session_status(self, session_id: Optional[str]) -> str:
        if not session_id:
            return "Error: session_id is required"

        session = self._sessions.get(session_id)
        if not session:
            return f"Error: Session {session_id} not found."

        status = "活跃" if session.is_active else "已结束"
        return (
            f"📊 会话状态\n\n"
            f"会话ID: {session_id}\n"
            f"模式: {session.mode.value}\n"
            f"状态: {status}\n"
            f"场景: {session.scenario.name if session.scenario else 'N/A'}\n"
            f"对话轮数: {len(session.dialogue_history)}\n"
            f"开始时间: {session.started_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        )

    def _find_scenario(self, scenario_id: Optional[str]) -> Optional[PracticeScenario]:
        if not scenario_id:
            return DEFAULT_SCENARIOS[0] if DEFAULT_SCENARIOS else None

        for scenario in DEFAULT_SCENARIOS:
            if scenario.id == scenario_id:
                return scenario
        return None
