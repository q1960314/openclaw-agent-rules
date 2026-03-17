# Master Agent 执行保障工具

## 📋 已创建的实际工具（不是文档，是可执行代码）

| 工具 | 用途 | 位置 |
|------|------|------|
| **validate-report.py** | 验证汇报格式（5 要素检查） | `./validate-report.py <汇报文本>` |
| **dispatch-task.py** | 分派任务（自动添加要求和固定 label） | `./dispatch-task.py <agent> <任务>` |
| **midtask-check.py** | 中途检查（5 分钟后） | `./midtask-check.py <session> <agent>` |
| **verify-config.py** | 验证配置是否正确 | `./verify-config.py` |

## 🔧 实际修改的配置文件

| 文件 | 修改内容 |
|------|---------|
| `config.json` | 添加 enforcement 配置（汇报验证、中途检查、固定 label） |
| `AGENTS.md` | 添加"发现错误并修复"思维要求 |

## 📝 使用示例

### 1. 分派任务
```bash
./dispatch-task.py test-expert "阶段 0.2 - 15 个接口测试"
```

### 2. 验证汇报
```bash
./validate-report.py "接口测试失败：返回空数据"
# 输出：❌ 缺少问题现象、原因分析...
```

### 3. 中途检查
```bash
./midtask-check.py agent:master:subagent:xxx test-expert
```

### 4. 验证配置
```bash
./verify-config.py
# 输出：✅ 所有配置验证通过
```

## ✅ 这次是真正落地的

- ✅ 修改了实际配置文件（config.json）
- ✅ 创建了可执行脚本（4 个 Python 工具）
- ✅ 添加了自动验证机制
- ✅ 不是只写文档

---

**最后更新：** 2026-03-12 14:28
