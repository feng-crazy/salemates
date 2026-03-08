## 1. 项目启动与运行 (How to Run)
- **一键启动**：
  - 执行 `docker-compose up --build` 后，所有服务（App, DB, VectorStore）应在 2 分钟内就绪。
  - 提供 `make dev` 命令支持本地热重载开发。
- **配置向导**：
  - 首次运行需自动生成 `.env.example`，并提示用户填写飞书 App ID/Secret 和 LLM Key。
  - 提供脚本 `init_kb.sh` 用于初始化示例产品知识库。

## 2. 功能验证矩阵 (Functional Verification)

| 测试模块 | 测试场景 (Input) | 预期行为 (Expected Output) | 验证方法 |
| :--- | :--- | :--- | :--- |
| **基础连接** | 发送任意文本给飞书 Bot | 1. 秒级收到 ACK。2. 2 秒内收到回复。3. 控制台打印完整 Agent 思考日志。 | 人工观察 + 日志检查 |
| **意图识别** | "你们比 A 公司贵多了" | 1. 识别 Intent=`OBJECTION_PRICE`。2. 识别 Emotion=`NEGATIVE`。3. 触发 `ObjectionHandler` 技能。 | 检查 Log 中的 `Reasoning` 字段 |
| **RAG 准确性** | "你们支持私有化部署吗？" (知识库中有明确答案) | 1. 检索到相关文档片段。2. 回答包含具体参数。3. **严禁**编造不支持的功能。 | 比对知识库原文 |
| **RAG 防幻觉** | "你们有火星服务器节点吗？" (知识库中无此信息) | 1. 检索结果为空或低置信度。2. 回答："目前暂未覆盖该区域，您可以..." 3. **不**胡编乱造。 | 人工判断回复合理性 |
| **销售策略** | "我再考虑一下" (处于种草阶段) | 1. 识别为 `HESITATION`。2. 触发 `SPIN` 技能，反问痛点。3. **不**直接发送报价单。 | 检查是否生成追问话术 |
| **主动跟进** | 模拟用户 24 小时未回复 | 1. 定时任务触发。2. 自动发送一条个性化关怀消息（引用上次话题）。 | 等待定时器触发或手动加速时间测试 |
| **状态流转** | 完成一轮完整对话（从问候到预约） | `SalesStage` 从 `NEW` 依次变更为 `DISCOVERING` -> `PROPOSING` -> `CLOSING`。 | 查询 Redis/DB 中的状态字段 |

## 3. 输入输出示例 (I/O Examples)

### 场景：处理价格异议
- **Input (User)**: "感觉有点贵，隔壁 X 家才卖 5000。"
- **Internal Process (Log)**:
  ```json
  {
    "step": "Reason",
    "intent": "PRICE_OBJECTION",
    "emotion": "CALCULATING",
    "selected_skills": ["RetrieveCompetitorInfo", "GenerateFABValue"],
    "strategy": "Avoid direct discount. Highlight unique ROI."
  }
  ```
- **Output (Bot)**: "完全理解您的考量，毕竟预算很重要。不过 X 家的方案通常不包含 [核心功能 A] 和 [售后服务 B]，这两项单独购买通常需要 3000 元。我们的价格虽然高一点，但能帮您每年节省 [具体成本]，实际上 ROI 更高。您最看重的是哪方面的投入产出比呢？"

### 场景：主动跟进
- **Trigger**: Timer (LastContact > 24h && Stage == 'PROPOSING')
- **Output (Bot)**: "李总您好，昨天提到的那个 [痛点解决方案] 案例，我刚好找到一个和您行业非常相似的成功故事，发给您参考一下？[链接/卡片]"

## 4. 非功能性指标 (Non-Functional Requirements)
- **响应延迟**: P95 < 2.0 秒 (不含 LLM 生成时间，指系统调度开销)。
- **并发能力**: 支持至少 50 QPS 的消息吞吐 without dropping messages。
- **资源占用**: 空闲状态下，容器内存占用 < 256MB。
- **稳定性**: 连续运行 48 小时无 Panic，无内存泄漏。

## 5. 交付物清单 (Deliverables Checklist)
- [ ] 完整的 Python 源代码仓库 (基于 OpenViking/bot)。
- [ ] `docker-compose.yml` 及所有 Dockerfile。
- [ ] `Makefile` (包含 build, run, test, lint 命令)。
- [ ] `testdata/` 目录 (包含模拟的飞书回调 JSON 和测试用例)。
- [ ] `README.md` (包含架构图、环境配置、技能扩展指南)。
- [ ] **Demo 录屏或日志文件**：展示一次完整的、符合“销冠”人设的多轮对话过程。
