# P1 Worker + OpenCode 落地计划

> 任务ID: P1-DOC-001  
> 目标: 最小闭环基础设施，支撑 Agent Worker 化与 OpenCode 融入生态循环系统  
> 状态: 基线文档（待 coder 落地）

---

## 一、文档定位与约束

### 1.1 核心原则（强制）
| 原则 | 说明 |
|------|------|
| **最小闭环** | P1 只实现基础设施，不实现业务逻辑 |
| **Worker 化** | 所有 Agent 必须通过 Worker 基类派生，禁止直接实例化 |
| **OpenCode 融入** | OpenCode 作为执行引擎之一，纳入生态循环，非独立系统 |
| **硬约束** | claim + artifacts + 独立验收，缺一不可 |

### 1.2 与现有系统的关系
```
现有生态 (sessions_send)          P1 Worker 架构
     ↓                                  ↓
  软约束通信                      硬约束任务队列
  可选 claim                      强制 claim
  可选 artifacts                  强制 artifacts
  自检验收                        独立 verifier 验收
     ↓                                  ↓
   并行运行                    逐步迁移，最终统一
```

---

## 二、最小闭环基础设施架构

### 2.1 核心组件清单（P1 必须实现）

```
scripts/p1/
├── core/                          # 基础设施核心
│   ├── __init__.py
│   ├── task_queue.py             # 任务队列（文件系统实现）
│   ├── worker_base.py            # Worker 抽象基类
│   ├── artifact_manager.py       # 产物管理器
│   ├── status_manager.py         # 状态管理器
│   └── claim_manager.py          # 任务领取管理
│
├── protocols/                     # 协议定义
│   ├── __init__.py
│   ├── task_schema.py            # Task 数据结构
│   ├── claim_schema.py           # Claim 数据结构
│   ├── status_schema.py          # Status 数据结构
│   ├── artifact_schema.py        # Artifact 数据结构
│   └── verdict_schema.py         # 验收结果结构
│
├── workers/                       # Worker 实现（P1 只实现基类 + 1 个示例）
│   ├── __init__.py
│   ├── coder_worker.py           # Coder Worker（示例实现）
│   └── test_expert_worker.py     # Test-Expert Worker（示例实现）
│
├── engines/                       # 执行引擎（OpenCode 接入点）
│   ├── __init__.py
│   ├── base_engine.py            # 引擎抽象接口
│   └── opencode_engine.py        # OpenCode 引擎实现
│
└── master_dispatcher.py          # Master 调度器（轻量版）
```

### 2.2 关键数据结构（必须落地）

#### Task Schema
```python
@dataclass
class Task:
    task_id: str                    # TASK-{YYYYMMDD}-{NNN}
    task_type: str                  # code_fix | doc_update | test_run
    title: str                      # 简短描述
    owner_role: str                 # coder | test-expert | doc-manager
    validator_role: str             # 独立验收者
    input_refs: List[str]           # 输入文件路径列表
    required_artifacts: List[str]   # 必须产物清单
    success_criteria: List[str]     # 验收标准
    status: TaskStatus              # queued | claimed | running | completed | verified | failed
    created_at: str                 # ISO 8601
    claim_info: Optional[Claim]     # 领取信息
    artifacts: List[Artifact]       # 产物列表
    verdict: Optional[Verdict]      # 验收结果
```

#### Claim Schema
```python
@dataclass
class Claim:
    task_id: str
    worker_id: str                  # worker 实例标识
    worker_role: str                # 角色类型
    claimed_at: str                 # ISO 8601
    expires_at: str                 # claim 有效期（默认 30 分钟）
    signature: str                  # 防篡改签名（简单哈希）
```

#### Artifact Schema
```python
@dataclass
class Artifact:
    name: str                       # 产物名称
    path: str                       # 相对路径（基于 task 目录）
    type: str                       # file | json | log | diff
    size: int                       # 字节数
    checksum: str                   # SHA256
    created_at: str                 # ISO 8601
    metadata: Dict[str, Any]        # 扩展元数据
```

#### Verdict Schema
```python
@dataclass
class Verdict:
    task_id: str
    validator_role: str             # 验收者角色
    passed: bool                    # 是否通过
    score: Optional[float]          # 评分（可选）
    findings: List[str]             # 发现的问题
    verified_at: str                # ISO 8601
    signature: str                  # 防篡改签名
```

---

## 三、Worker 基类设计（coder 落地指南）

### 3.1 抽象基类方法清单

```python
class WorkerBase(ABC):
    """
    所有 Worker 必须继承的抽象基类
    P1 必须实现的方法用 [P1] 标注
    """

    # === 属性 ===
    role: str                       # Worker 角色标识
    worker_id: str                  # 实例唯一 ID
    current_task: Optional[Task]    # 当前任务

    # === 生命周期方法 [P1] ===
    @abstractmethod
    def __init__(self, role: str): pass

    @abstractmethod
    def initialize(self) -> bool: pass  # 初始化检查

    @abstractmethod
    def shutdown(self) -> None: pass    # 优雅关闭

    # === 任务管理方法 [P1] ===
    @abstractmethod
    def poll_task(self) -> Optional[Task]: pass  # 轮询待办任务

    @abstractmethod
    def claim_task(self, task_id: str) -> bool: pass  # 领取任务（硬约束）

    @abstractmethod
    def release_claim(self) -> bool: pass  # 释放 claim（超时/失败）

    # === 执行方法 [P1] ===
    @abstractmethod
    def execute(self) -> bool: pass  # 主执行入口

    @abstractmethod
    def execute_core(self) -> Dict[str, Any]: pass  # 子类实现具体逻辑

    # === 产物管理方法 [P1] ===
    @abstractmethod
    def write_artifact(self, name: str, content: Any, artifact_type: str) -> bool: pass

    @abstractmethod
    def validate_artifacts(self) -> bool: pass  # 检查 required_artifacts

    # === 状态管理方法 [P1] ===
    @abstractmethod
    def update_status(self, status: TaskStatus, message: str = "") -> bool: pass

    @abstractmethod
    def report_failure(self, error: str, retryable: bool = False) -> bool: pass

    # === 引擎调用方法 [P1] ===
    @abstractmethod
    def invoke_engine(self, engine_name: str, params: Dict) -> Dict: pass  # 调用 OpenCode 等引擎
```

### 3.2 Worker 执行流程（状态机）

```
[Idle] → poll_task() → [Polling]
                         ↓ (发现任务)
              claim_task() → [Claimed]
                                ↓ (成功)
              update_status(RUNNING) → [Running]
                                           ↓
                          execute_core() → [Running]
                                           ↓
                    write_artifact() → [Running]
                                           ↓
                validate_artifacts() → [Running]
                                           ↓ (通过)
              update_status(COMPLETED) → [Completed]
                                              ↓
                                 (等待 verifier)
                                              ↓
              verdict received → [Verified] / [Failed]
```

---

## 四、OpenCode 引擎接入设计

### 4.1 引擎抽象接口

```python
class ExecutionEngine(ABC):
    """执行引擎抽象基类"""

    name: str
    version: str

    @abstractmethod
    def is_available(self) -> bool: pass  # 检查引擎是否可用

    @abstractmethod
    def execute(self, task: Task, context: Dict) -> EngineResult: pass

    @abstractmethod
    def parse_output(self, raw_output: str) -> Dict[str, Any]: pass

    @abstractmethod
    def generate_artifacts(self, result: EngineResult) -> List[Artifact]: pass
```

### 4.2 OpenCode 引擎实现要点

```python
class OpenCodeEngine(ExecutionEngine):
    """
    OpenCode 执行引擎实现
    将 OpenCode 融入生态循环，而非独立运行
    """

    name = "opencode"
    version = "1.0"

    def execute(self, task: Task, context: Dict) -> EngineResult:
        """
        调用 OpenCode CLI 执行代码任务

        关键参数：
        - --format json: 结构化输出
        - --agent plan: 使用 planning 模式
        - --model: 从 task.metadata 读取或默认
        - --dir: 工作目录（从 input_refs 推断）
        """
        pass

    def parse_output(self, raw_output: str) -> Dict[str, Any]:
        """
        解析 OpenCode JSON 输出
        提取：文件变更、执行日志、结果摘要
        """
        pass

    def generate_artifacts(self, result: EngineResult) -> List[Artifact]:
        """
        将 OpenCode 输出转换为标准 Artifact
        必须生成：
        1. diff.patch - 代码变更
        2. changed_files.json - 变更文件列表
        3. run.log - 执行日志
        """
        pass
```

### 4.3 OpenCode 与生态循环集成点

```
┌─────────────────────────────────────────────────────────┐
│                   生态循环系统                            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐