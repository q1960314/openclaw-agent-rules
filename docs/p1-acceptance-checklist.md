# P1 Worker + OpenCode 验收检查清单

> 任务ID: P1-DOC-001  
> 用途: 供 test-expert 执行验收，供 coder 自检查  
> 原则: 每个检查项必须有客观通过标准，禁止主观判定

---

## 使用说明

### 验收流程
```
Phase 1 完成 → Test-Expert 执行 Section A → 全部通过 → 进入 Phase 2
Phase 2 完成 → Test-Expert 执行 Section B → 全部通过 → 进入 Phase 3
Phase 3 完成 → Test-Expert 执行 Section C → 全部通过 → 进入 Phase 4
Phase 4 完成 → Test-Expert 执行 Section D → 全部通过 → P1 完成
```

### 检查项标记
- `[ ]` - 未开始
- `[~]` - 进行中
- `[?]` - 待确认
- `[x]` - 已通过（附证据）
- `[!]` - 失败（附原因）

---

## Section A: 基础设施核心（Phase 1）

### A.1 协议数据结构

#### A.1.1 Task 数据结构
| 检查项 | 通过标准 | 证据 | 状态 |
|--------|----------|------|------|
| A.1.1.1 | Task 类可实例化，包含所有必需字段 | 单元测试通过 | [ ] |
| A.1.1.2 | Task 可序列化为 JSON，无字段丢失 | 序列化前后对比 | [ ] |
| A.1.1.3 | Task 可从 JSON 反序列化，类型正确 | 反序列化测试 | [ ] |
| A.1.1.4 | task_id 格式符合 TASK-{YYYYMMDD}-{NNN} | 正则验证 | [ ] |
| A.1.1.5 | status 只能是预定义枚举值 | 非法值拒绝测试 | [ ] |

#### A.1.2 Claim 数据结构
| 检查项 | 通过标准 | 证据 | 状态 |
|--------|----------|------|------|
| A.1.2.1 | Claim 类可实例化，包含所有必需字段 | 单元测试通过 | [ ] |
| A.1.2.2 | Claim 包含有效期字段 expires_at | 字段存在检查 | [ ] |
| A.1.2.3 | Claim 签名可验证（SHA256） | 签名验证测试 | [ ] |
| A.1.2.4 | 过期 Claim 被拒绝 | 过期拒绝测试 | [ ] |

#### A.1.3 Artifact 数据结构
| 检查项 | 通过标准 | 证据 | 状态 |
|--------|----------|------|------|
| A.1.3.1 | Artifact 类可实例化，包含所有必需字段 | 单元测试通过 | [ ] |
| A.1.3.2 | Artifact 支持 file/json/log/diff 类型 | 类型枚举测试 | [ ] |
| A.1.3.3 | Artifact 校验和可计算（SHA256） | 校验和测试 | [ ] |

#### A.1.4 Verdict 数据结构
| 检查项 | 通过标准 | 证据 | 状态 |
|--------|----------|------|------|
| A.1.4.1 | Verdict 类可实例化，包含所有必需字段 | 单元测试通过 | [ ] |
| A.1.4.2 | Verdict 包含 findings 列表 | 字段存在检查 | [ ] |
| A.1.4.3 | Verdict 签名可验证 | 签名验证测试 | [ ] |

### A.2 任务队列系统

| 检查项 | 通过标准 | 证据 | 状态 |
|--------|----------|------|------|
| A.2.1 | TaskQueue 可创建新任务 | create_task 返回 task_id | [ ] |
| A.2.2 | TaskQueue 可查询待办任务列表 | list_pending 返回列表 | [ ] |
| A.2.3 | TaskQueue 可按角色筛选待办 | list_pending(role='coder') 生效 | [ ] |
| A.2.4 | TaskQueue 可更新任务状态 | update_status 后状态变更 | [ ] |
| A.2.5 | TaskQueue 状态变更写入历史 | status.json 包含历史记录 | [ ] |
| A.2.6 | TaskQueue 支持任务领取 | claim_task 生成 claim.json | [ ] |
| A.2.7 | 已领取任务不在待办列表 | list_pending 排除已领取 | [ ] |
| A.2.8 | TaskQueue 支持 claim 释放 | release_claim 后任务回到待办 | [ ] |

### A.3 Claim 管理器

| 检查项 | 通过标准 | 证据 | 状态 |
|--------|----------|------|------|
| A.3.1 | ClaimManager 可创建 claim | create_claim 返回有效 claim | [ ] |
| A.3.2 | Claim 包含 worker_id + worker_role | 字段完整检查 | [ ] |
| A.3.3 | Claim 有效期默认为 30 分钟 | 时间差验证 | [ ] |
| A.3.4 | ClaimManager 可验证 claim 有效性 | validate_claim 返回布尔 | [ ] |
| A.3.5 | 过期 claim 验证失败 | 过期 claim 返回 False | [ ] |
| A.3.6 | ClaimManager 可释放 claim | release_claim 删除 claim 文件 | [ ] |
| A.3.7 | 同一任务禁止重复 claim | 重复 claim 被拒绝 | [ ] |

### A.4 产物管理器

| 检查项 | 通过标准 | 证据 | 状态 |
|--------|----------|------|------|
| A.4.1 | ArtifactManager 可写入文本产物 | write_text 生成文件 | [ ] |
| A.4.2 | ArtifactManager 可写入 JSON 产物 | write_json 生成文件 | [ ] |
| A.4.3 | ArtifactManager 可写入二进制产物 | write_binary 生成文件 | [ ] |
| A.4.4 | 产物自动计算 SHA256 校验和 | 校验和字段非空 | [ ] |
| A.4.5 | 产物元数据包含创建时间 | created_at 字段存在 | [ ] |
| A.4.6 | ArtifactManager 可读取产物 | read_artifact 返回内容 | [ ] |
| A.4.7 | ArtifactManager 可验证产物完整性 | 校验和不匹配返回 False | [ ] |
| A.4.8 | 产物存储在 {task_dir}/artifacts/ 下 | 路径检查 | [ ] |

### A.5 状态管理器

| 检查项 | 通过标准 | 证据 | 状态 |
|--------|----------|------|------|
| A.5.1 | StatusManager 可更新任务状态 | update_status 写入 status.json | [ ] |
| A.5.2 | 状态变更记录包含时间戳 | timestamp 字段存在 | [ ] |
| A.5.3 | 状态变更记录包含变更原因 | message 字段可选 | [ ] |
| A.5.4 | 状态历史可追溯（倒序列表） | 历史记录数量 > 1 | [ ] |
| A.5.5 | 非法状态流转被拒绝 | 无效流转抛出异常 | [ ] |
| A.5.6 | 支持状态：queued → claimed → running → completed → verified | 完整流转测试 | [ ] |
| A.5.7 | 支持失败状态：running → failed | 失败流转测试 | [ ] |
| A.5.8 | 支持重试状态：failed → queued | 重试流转测试 | [ ] |

### A.6 目录结构

| 检查项 | 通过标准 | 证据 | 状态 |
|--------|----------|------|------|
| A.6.1 | 目录结构符合设计文档 | tree 命令输出比对 | [ ] |
| A.6.2 | 任务目录自动创建 | create_task 生成目录 | [ ] |
| A.6.3 | 产物目录自动创建 | write_artifact 生成目录 | [ ] |
| A.6.4 | 日志目录自动创建 | Worker 启动生成目录 | [ ] |

---

## Section B: Worker 实现（Phase 2）

### B.1 WorkerBase 抽象类

| 检查项 | 通过标准 | 证据 | 状态 |
|--------|----------|------|------|
| B.1.1 | WorkerBase 不能直接实例化 | 抽象类实例化抛出异常 | [ ] |
| B.1.2 | 子类必须实现所有抽象方法 | 未实现方法无法实例化 | [ ] |
| B.1.3 | Worker 初始化设置 role 属性 | role 字段非空 | [ ] |
| B.1.4 | Worker 初始化设置 worker_id | worker_id 唯一且非空 | [ ] |
| B.1.5 | initialize() 返回 bool | 返回值类型检查 | [ ] |
| B.1.6 | shutdown() 正常执行无异常 | 调用测试 | [ ] |

### B.2 CoderWorker 示例实现

| 检查项 | 通过标准 | 证据 | 状态 |
|--------|----------|------|------|
| B.2.1 | CoderWorker 继承自 WorkerBase | 继承关系检查 | [ ] |
| B.2.2 | CoderWorker role = "coder" | 属性值检查 | [ ] |
| B.2.3 | poll_task() 返回待办任务 | 有任务时返回 Task | [ ] |
| B.2.4 | poll_task() 无任务返回 None | 无任务时返回 None | [ ] |
| B.2.5 | claim_task() 成功写入 claim.json | claim 文件存在 | [ ] |
| B.2.6 | claim_task() 失败返回 False | 已被领取时返回 False | [ ] |
| B.2.7 | execute() 调用 execute_core() | 调用链验证 | [ ] |
| B.2.8 | execute_core() 返回产物字典 | 返回值类型检查 | [ ] |
| B.2.9 | write_artifact() 生成产物文件 | artifacts 目录有文件 | [ ] |
| B.2.10 | validate_artifacts() 检查 required_artifacts | 缺失产物返回 False | [ ] |
| B.2.11 | update_status() 更新状态 | status.json 状态变更 | [ ] |
| B.2.12 | report_failure() 记录失败 | status 变为 failed | [ ] |

### B.3 TestExpertWorker 示例实现

| 检查项 | 通过标准 | 证据 | 状态 |
|--------|----------|------|------|
| B.3.1 | TestExpertWorker 继承自 WorkerBase | 继承关系检查 | [ ] |
| B.3.2 | TestExpertWorker role = "test-expert" | 属性值检查 | [ ] |
| B.3.3 | 可领取待验收任务 | claim_task 成功 | [ ] |
| B.3.4 | 验收时读取 artifacts 目录 | 产物读取验证 | [ ] |
| B.3.5 | 验收时检查 success_criteria | 标准比对逻辑 | [ ] |
| B.3.6 | 验收通过生成 verdict.json | verdict 文件存在 | [ ] |
| B.3.7 | verdict 包含 passed 字段 | 布尔值检查 | [ ] |
| B.3.8 | verdict 包含 findings 列表 | 列表存在 | [ ] |
| B.3.9 | verdict 签名可验证 | 签名验证通过 | [ ] |

### B.4 Worker CLI 入口

| 检查项 | 通过标准 | 证据 | 状态 |
|--------|----------|------|------|
| B.4.1 | run_worker.py 支持 coder 参数 | `python run_worker.py coder` 启动 | [ ] |
| B.4.2 | run_worker.py 支持 test-expert 参数 | `python run_worker.py test-expert` 启动 | [ ] |
| B.4.3 | Worker 进程持续运行监听任务 | 进程存活 > 30 秒 | [ ] |
| B.4.4 | Worker 可优雅关闭（SIGTERM） | 收到信号后退出 | [ ] |
| B.4.5 | Worker 日志输出到文件 | logs/ 目录有日志 | [ ] |

---

## Section C: OpenCode 引擎（Phase 3）

### C.1 引擎抽象接口

| 检查项 | 通过标准 | 证据 | 状态 |
|--------|----------|------|------|
| C.1.1 | ExecutionEngine 不能直接实例化 | 抽象类实例化抛出异常 | [ ] |
| C.1.2 | is_available() 返回 bool | 返回值类型检查 | [ ] |
| C.1.3 | execute() 接收 Task 和 context | 参数类型检查 | [ ] |
| C.1.4 | execute() 返回 EngineResult | 返回值类型检查 | [ ] |
| C.1.5 | parse_output() 返回 Dict | 返回值类型检查 | [ ] |
| C.1.6 | generate_artifacts() 返回 List[Artifact] | 返回值类型检查 | [ ] |

### C.2 OpenCode 引擎实现

| 检查项 | 通过标准 | 证据 | 状态 |
|--------|----------|------|------|
| C.2.1 | OpenCodeEngine 继承自 ExecutionEngine | 继承关系检查 | [ ] |
| C.2.2 | OpenCodeEngine name = "opencode" | 属性值检查 | [ ] |
| C.2.3 | is_available() 检查 opencode CLI 存在 | 路径检查 | [ ] |
| C.2.4 | is_available() CLI 不存在返回 False | 模拟不存在场景 | [ ] |
| C.2.5 | execute() 构建正确命令行参数 | 命令行参数检查 | [ ] |
| C.2.6 | execute() 包含 --format json | 参数存在检查 | [ ] |
| C.2.7 | execute() 包含 --agent plan | 参数存在检查 | [ ] |
| C.2.8 | execute() 指定工作目录 --dir | 参数存在检查 | [ ] |
| C.2.9 | execute() 调用成功返回结果 | 成功执行测试 | [ ] |
| C.2.10 | execute() 调用失败返回错误 | 失败处理测试 | [ ] |
| C.2.11 | parse_output() 能解析 OpenCode JSON | JSON 解析测试 | [ ] |
| C.2.12 | parse_output() 能处理无效 JSON | 异常处理测试 | [ ] |

### C.3 Artifact 生成

| 检查项 | 通过标准 | 证据 | 状态 |
|--------|----------|------|------|
| C.3.1 | 生成 diff.patch 产物 | 文件存在检查 | [ ] |
| C.3.2 | diff.patch 包含有效 diff 格式 | diff 格式验证 | [ ] |
| C.3.3 | 生成 changed_files.json 产物 | 文件存在检查 | [ ] |
| C.3.4 | changed_files.json 包含变更文件列表 | 字段内容检查 | [ ] |
| C.3.5 | 生成 run.log 产物 | 文件存在检查 | [ ] |
| C.3.6 | run.log 包含执行输出 | 内容非空检查 | [ ] |
| C.3.7 | 所有产物 Artifact 对象包含校验和 | checksum 字段非空 | [ ] |

### C.4 引擎与 Worker 集成

| 检查项 | 通过标准 | 证据 | 状态 |
|--------|----------|------|------|
| C.4.1 | CoderWorker.invoke_engine() 可调用 | 方法存在检查 | [ ] |
| C.4.2 | invoke_engine("opencode", ...) 成功 | 调用成功测试 | [ ] |
| C.4.3 | 引擎结果自动转为 artifacts | artifacts 目录有文件 | [ ] |
| C.4.4 | 引擎失败被捕获并报告 | report_failure 被调用 | [ ] |

---

## Section D: Master 调度器（Phase 4）

### D.1 MasterDispatcher

| 检查项 | 通过标准 | 证据 | 状态 |
|--------|----------|------|------|
| D.1.1 | dispatch() 创建任务并返回 task_id | 返回值非空 | [ ] |
| D.1.2 | 任务自动进入 pending 队列 | list_pending 包含新任务 | [ ] |
| D.1.3 | wake_worker() 发送唤醒信号 | 信号发送成功 | [ ] |
| D.1.4 | monitor_task() 轮询任务状态 | 状态变更被检测 | [ ] |
| D.1.5 | monitor_task() 任务完成时返回 | 非阻塞等待 | [ ] |
| D.1.6 | decide_next() 根据 verdict 决策 | passed=True 时继续 | [ ] |
| D.1.7 | decide_next() 失败时返回重试指令 | passed=False 时重试 | [ ] |

### D.2 端到端流程

| 检查项 | 通过标准 | 证据 | 状态 |
|--------|----------|------|------|
| D.2.1 | Master 创建代码修复任务 | task 创建成功 | [ ] |
| D.2.2 | CoderWorker 领取任务 | claim.json 生成 | [ ] |
| D.2.3 | CoderWorker 执行 OpenCode | run.log 生成 | [ ] |
| D.2.4 | CoderWorker 生成产物 | artifacts 目录非空 | [ ] |
| D.2.5 | CoderWorker 标记完成 | status=completed | [ ] |
| D.2.6 | TestExpertWorker 领取验收任务 | claim.json 生成 | [ ] |
| D.2.7 | TestExpertWorker 生成 verdict | verdict.json 生成 | [ ] |
| D.2.8 | Master 获取 verdict 并决策 | decide_next 返回 | [ ] |

### D.3 错误处理

| 检查项 | 通过标准 | 证据 | 状态 |
|--------|----------|------|------|
| D.3.1 | Worker 执行失败标记 failed | status=failed | [ ] |
| D.3.2 | Worker 超时自动释放 claim | claim 过期删除 | [ ] |
| D.3.3 | 失败任务可重试 | 重试后重新进入队列 | [ ] |
| D.3.4 | 错误信息写入日志 | log 文件包含错误 | [ ] |

---

## Section E: 综合验收

### E.1 代码质量

| 检查项 | 通过标准 | 证据 | 状态 |
|--------|----------|------|------|
| E.1.1 | 代码通过静态类型检查 | mypy 无错误 | [ ] |
| E.1.2 | 代码风格符合 PEP8 | flake8 无错误 | [ ] |
| E.1.3 | 核心方法有 docstring | 文档覆盖率 > 80% | [ ] |
| E.1.4 | 无硬编码路径 | 配置化检查 | [ ] |
| E.1.5 | 有基本单元测试 | 测试覆盖率 > 60% | [ ] |

### E.2 文档完整性

| 检查项 | 通过标准 | 证据 | 状态 |
|--------|----------|------|------|
| E.2.1 | README.md 包含快速开始 | 文件存在 | [ ] |
| E.2.2 | API 文档完整 | 核心类有文档 | [ ] |
| E.2.3 | 配置文档完整 | p1-worker.yaml 示例 | [ ] |
| E.2.4 | 部署文档完整 | 部署步骤可执行 | [ ] |

### E.3 性能基线

| 检查项 | 通过标准 | 证据 | 状态 |
|--------|----------|------|------|
| E.3.1 | 任务创建 < 100ms | 性能测试 | [ ] |
| E.3.2 | 任务领取 < 50ms | 性能测试 | [ ] |
| E.3.3 | Worker 启动 < 5s | 启动时间测试 | [ ] |
| E.3.4 | 内存占用 < 100MB | 内存监控 | [ ] |

### E.4 安全基线

| 检查项 | 通过标准 | 证据 | 状态 |
|--------|----------|------|------|
| E.4.1 | 无路径遍历漏洞 | 输入验证测试 | [ ] |
| E.4.2 | claim 签名防篡改 | 篡改检测测试 | [ ] |
| E.4.3 | verdict 签名防篡改 | 篡改检测测试 | [ ] |
| E.4.4 | 敏感信息不写入日志 | 日志扫描检查 | [ ] |

---

## 验收汇总

### Phase 1 汇总
| 类别 | 总项 | 通过 | 失败 | 跳过 |
|------|------|------|------|------|
| 协议数据结构 | 14 | 0 | 0 | 0 |
| 任务队列 | 8 | 0 | 0 | 0 |
| Claim 管理 | 7 | 0 | 0 | 0 |
| 产物管理 | 8 | 0 | 0 | 0 |
| 状态管理 | 8 | 0 | 0 | 0 |
| 目录结构 | 4 | 0 | 0 | 0 |
| **Phase 1 小计** | **49** | **0** | **0** | **0** |

### Phase 2 汇总
| 类别 | 总项 | 通过 | 失败 | 跳过 |
|------|------|------|------|------|
| WorkerBase | 6 | 0 | 0 | 0 |
| CoderWorker | 12 | 0 | 0 | 0 |
| TestExpertWorker | 9 | 0 | 0 | 0 |
| Worker CLI | 5 | 0 | 0 | 0 |
| **Phase 2 小计** | **32** | **0** | **0** | **0** |

### Phase 3 汇总
| 类别 | 总项 | 通过 | 失败 | 跳过 |
|------|------|------|------|------|
| 引擎抽象 | 6 | 0 | 0 | 0 |
| OpenCode 实现 | 12 | 0 | 0 | 0 |
| Artifact 生成 | 7 | 0 | 0 | 0 |
| 引擎集成 | 4 | 0 | 0 | 0 |
| **Phase 3 小计** | **29** | **0** | **0** | **0** |

### Phase 4 汇总
| 类别 | 总项 | 通过 | 失败 | 跳过 |
|------|------|------|------|------|
| MasterDispatcher | 7 | 0 | 0 | 0 |
| 端到端流程 | 8 | 0 | 0 | 0 |
| 错误处理 | 4 | 0 | 0 | 0 |
| **Phase 4 小计** | **19** | **0** | **0** | **0** |

### 综合汇总
| 类别 | 总项 | 通过 | 失败 | 跳过 |
|------|------|------|------|------|
| 功能验收 | 129 | 0 | 0 | 0 |
| 代码质量 | 5 | 0 | 0 | 0 |
| 文档完整性 | 4 | 0 | 0 | 0 |
| 性能基线 | 4 | 0 | 0 | 0 |
| 安全基线 | 4 | 0 | 0 | 0 |
| **总计** | **146** | **0** | **0** | **0** |

---

## 验收签字

| 角色 | 姓名 | 日期 | 签字 |
|------|------|------|------|
| 执行方（Coder） | | | |
| 验收方（Test-Expert） | | | |
| 审批方（Master） | | | |

---

**文档状态**: 基线已定，等待 Phase 1 完成后开始验收  
**维护者**: doc-manager / test-expert
