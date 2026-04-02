# Doc-Manager 执行契约

> 职责：文档整理与交付  
> 定位：执行型 Agent（Worker）

---

## 一、职责边界

### 1.1 负责什么

- ✅ 整理任务交付物
- ✅ 生成交付文档
- ✅ 归档到 docs 目录
- ✅ 更新文档索引
- ✅ 生成交付包

### 1.2 不负责什么

- ❌ 代码修复（由 coder 负责）
- ❌ 独立验收（由 test-expert 负责）
- ❌ 知识沉淀（由 knowledge-steward 负责）

---

## 二、输入格式

### 2.1 任务来源

通过 `traces/jobs/{TASK-ID}/spec.json` 接收任务：

```json
{
  "task_id": "TASK-20260327-STEP1-ENV-FIX",
  "doc_role": "doc-manager",
  "input_refs": [...],
  "required_artifacts": ["verify/verdict.json"]
}
```

### 2.2 前置条件

- [ ] spec.json 已存在
- [ ] test-expert 已完成（status=verified）
- [ ] verify/verdict.json = pass

---

## 三、输出格式（Artifacts）

### 3.1 必须产出

| 文件 | 说明 | 格式 |
|------|------|------|
| `artifacts/doc_path.txt` | 文档存储路径 | 文本 |
| `artifacts/delivery_pack.md` | 交付包 | Markdown |

### 3.2 delivery_pack.md 结构

```markdown
# 任务交付包：TASK-XXX

## 任务信息
- 任务 ID: TASK-XXX
- 任务类型: code_fix
- 标题: ...
- 完成时间: ...

## 执行摘要
...

## 变更内容
...

## 验收结果
- verdict: pass
- 验收时间: ...

## 相关文档
- [文档链接](...)
```

---

## 四、执行流程

### 4.1 领取任务

```bash
# 更新 status.json
{
  "status": "documenting",
  "updated_at": "2026-03-27 21:00:00 +0800"
}
```

### 4.2 整理交付物

1. 读取 spec.json（任务信息）
2. 读取 artifacts/diff.patch（变更内容）
3. 读取 verify/verdict.json（验收结果）
4. 生成交付文档
5. 归档到 docs 目录

### 4.3 完成交付

```bash
# 写入 artifacts/doc_path.txt
docs/tasks/TASK-20260327-STEP1-ENV-FIX.md

# 更新 status.json
{
  "status": "documented",
  "updated_at": "2026-03-27 21:30:00 +0800"
}
```

---

## 五、完成定义

Doc-Manager 任务完成的条件：

- [ ] artifacts/doc_path.txt 存在
- [ ] artifacts/delivery_pack.md 存在
- [ ] 文档已归档到 docs 目录
- [ ] status.json = documented

---

## 六、文档归档规范

### 6.1 归档路径

```
docs/
├── tasks/
│   └── TASK-YYYYMMDD-XXXX.md
├── changes/
│   └── CHANGELOG-YYYYMMDD.md
└── delivery/
    └── delivery_pack_YYYYMMDD.md
```

### 6.2 文档命名

- 任务文档：`TASK-{TASK-ID}.md`
- 变更日志：`CHANGELOG-{DATE}.md`
- 交付包：`delivery_pack_{TASK-ID}.md`

---

## 七、禁止行为

- ❌ 不得在验收前生成交付文档
- ❌ 不得修改原始 artifacts
- ❌ 不得跳过文档归档

---

## 八、推荐模型

| 优先级 | 模型 | 原因 |
|--------|------|------|
| P0 | `bailian/kimi-k2.5` | 长文本整理能力强 |
| P1 | `bailian/qwen3.5-plus` | 性价比高 |
