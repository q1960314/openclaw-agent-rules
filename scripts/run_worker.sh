#!/bin/bash
# Worker 架构启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

case "$1" in
    master)
        echo "🚀 启动 Master 调度器..."
        python3 master_dispatcher.py "${@:2}"
        ;;
    coder)
        echo "🔧 启动 Coder Worker..."
        python3 worker_base.py coder
        ;;
    test)
        echo "🧪 启动 Test-Expert Worker..."
        python3 worker_base.py test-expert
        ;;
    doc)
        echo "📄 启动 Doc-Manager Worker..."
        python3 worker_base.py doc-manager
        ;;
    knowledge)
        echo "📚 启动 Knowledge-Steward Worker..."
        python3 worker_base.py knowledge-steward
        ;;
    status)
        echo "📊 任务队列状态:"
        python3 -c "
from task_queue import TaskQueue
q = TaskQueue()
pending = q.list_pending()
print(f'待处理任务：{len(pending)}')
for t in pending:
    print(f'  - {t.task_id} → {t.owner_role}')
"
        ;;
    create-test)
        echo "📋 创建测试任务..."
        python3 -c "
from task_queue import create_task
success = create_task(
    task_id='TASK-$(date +%Y%m%d)-TEST-001',
    task_type='code_fix',
    title='测试 Worker 架构',
    owner_role='coder',
    validator_role='test-expert',
    input_refs=['scripts/workflow_run_opencode.py'],
    required_artifacts=['diff.patch', 'changed_files.json', 'run.log'],
    success_criteria=['测试成功']
)
print('任务创建:', '✅ 成功' if success else '❌ 失败')
"
        ;;
    help|*)
        echo "用法：$0 {master|coder|test|doc|knowledge|status|create-test}"
        echo ""
        echo "命令:"
        echo "  master <需求>  - 启动 Master 调度器并处理需求"
        echo "  coder          - 启动 Coder Worker"
        echo "  test           - 启动 Test-Expert Worker"
        echo "  doc            - 启动 Doc-Manager Worker"
        echo "  knowledge      - 启动 Knowledge-Steward Worker"
        echo "  status         - 查看任务队列状态"
        echo "  create-test    - 创建测试任务"
        echo ""
        echo "示例:"
        echo "  $0 master '修复 workflow_run_opencode.py 中的命令路径问题'"
        echo "  $0 coder"
        echo "  $0 status"
        ;;
esac
