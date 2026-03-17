# 进程锁机制集成说明

## 阶段 1.2：确保只有一个抓取进程运行

### 实现目标
防止同时启动多个数据抓取进程，避免资源竞争和数据冲突。

### 实现方案

#### 1. 独立模块：`process_lock.py`
创建了独立的进程锁模块，包含 `ProcessLock` 类：

```python
from process_lock import ProcessLock

# 创建锁实例
lock = ProcessLock(lock_file='/tmp/fetch_data.lock')

# 获取锁（非阻塞）
if lock.acquire():
    # 成功获取锁，执行业务逻辑
    try:
        # ... 你的代码 ...
    finally:
        lock.release()  # 释放锁
else:
    # 获取锁失败，已有其他进程在运行
    print("已有其他进程在运行，退出")
    sys.exit(1)
```

#### 2. 核心特性

**✅ 排他锁（非阻塞）**
- 使用 `fcntl.flock()` 实现文件锁
- `LOCK_EX | LOCK_NB`：排他锁 + 非阻塞模式
- 获取锁失败立即返回 `False`，不等待

**✅ 进程信息记录**
- 锁文件中记录 PID 和时间戳
- 方便调试和排查问题

**✅ 自动释放**
- 进程正常退出时自动释放锁
- 进程异常终止时操作系统会自动释放文件锁
- 兜底机制：`finally` 块确保锁释放

**✅ 日志集成**
- 支持传入 logger 对象
- 无 logger 时使用 print 降级输出

### 3. 集成位置

#### `fetch_data_optimized.py` 主函数

```python
def main():
    # 【阶段 1.2：进程锁机制】
    process_lock = ProcessLock(lock_file='/tmp/fetch_data.lock')
    if not process_lock.acquire():
        print("❌ 无法启动：已有其他抓取进程在运行")
        sys.exit(1)
    
    try:
        # ... 主程序逻辑 ...
    except KeyboardInterrupt:
        # ... 异常处理 ...
    finally:
        # 【兜底】确保锁最终被释放
        process_lock.release()
```

### 4. 验收标准

#### ✅ 测试场景 1：单进程正常运行
```bash
python3 fetch_data_optimized.py
# 输出：✅ 进程锁已获取 (PID: xxx)
# 程序正常运行
```

#### ✅ 测试场景 2：双进程竞争
```bash
# 终端 1
python3 fetch_data_optimized.py
# 输出：✅ 进程锁已获取 (PID: xxx)

# 终端 2（同时启动）
python3 fetch_data_optimized.py
# 输出：❌ 无法获取进程锁，已有其他进程在运行 (PID: xxx)
# 程序立即退出
```

#### ✅ 测试场景 3：进程退出后锁自动释放
```bash
# 终端 1
python3 fetch_data_optimized.py
# 按 Ctrl+C 退出
# 输出：✅ 进程锁已释放 (PID: xxx)

# 终端 2（再次启动）
python3 fetch_data_optimized.py
# 输出：✅ 进程锁已获取 (PID: xxx)
# 程序正常运行
```

### 5. 测试验证

运行测试脚本验证所有功能：
```bash
cd /home/admin/.openclaw/agents/master
python3 test_process_lock.py
```

**测试结果：**
```
✅ 进程锁功能测试 - 通过
✅ 并发进程测试 - 通过
🎉 所有测试通过！进程锁机制已就绪
```

### 6. 文件清单

| 文件 | 说明 |
|------|------|
| `process_lock.py` | 进程锁独立模块（新增） |
| `fetch_data_optimized.py` | 主程序（已集成进程锁） |
| `test_process_lock.py` | 测试脚本（新增） |

### 7. 注意事项

#### ⚠️ 锁文件位置
- 默认：`/tmp/fetch_data.lock`
- 可自定义：`ProcessLock(lock_file='/path/to/lock')`

#### ⚠️ 手动清理
如果程序异常终止导致锁未释放，可手动删除：
```bash
rm /tmp/fetch_data.lock
```

#### ⚠️ 多用户环境
- `/tmp` 目录是所有用户共享的
- 如需隔离，可使用用户专属目录：
  ```python
  lock_file = f'/tmp/fetch_data_{os.getuid()}.lock'
  ```

### 8. 技术原理

#### fcntl.flock() 文件锁
```python
fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
```

- `LOCK_EX`：排他锁（独占锁）
- `LOCK_NB`：非阻塞（立即返回）
- `LOCK_UN`：解锁（释放锁）

#### 锁的自动释放
- 文件描述符关闭时自动释放
- 进程终止时操作系统自动关闭所有文件描述符
- 即使程序崩溃，锁也会被释放

### 9. 交付状态

- ✅ 进程锁模块代码完成
- ✅ 集成到主代码完成
- ✅ 单元测试通过
- ✅ 并发测试通过
- ✅ 语法检查通过

### 10. 时限

- 预计：20 分钟
- 实际：已完成

---

**合规提示：** 本内容仅为量化研究回测使用，不构成任何投资建议，投资有风险，入市需谨慎
