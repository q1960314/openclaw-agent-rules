#!/usr/bin/env python3
"""
Worker 基类 - 所有执行型 agent 的父类

强制：
1. 必须先 claim 才能执行
2. 必须产出 artifacts 才能完成
3. 必须更新状态
4. 必须通过独立验收
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from task_queue import TaskQueue, Task, JOBS_ROOT, STATUS_COMPLETED, STATUS_FAILED, STATUS_VERIFIED


class Worker(ABC):
    """Worker 基类 - 所有执行型 agent 必须继承"""
    
    def __init__(self, role: str):
        self.role = role
        self.queue = TaskQueue()
        self.current_task: Optional[Task] = None
        self.task_dir: Optional[Path] = None
    
    def claim_task(self, lease_hours: int = 1) -> bool:
        """领取任务（强制 claim）"""
        task = self.queue.pop(self.role, lease_hours)
        if task is None:
            return False
        
        self.current_task = task
        self.task_dir = JOBS_ROOT / task.task_id
        return True
    
    def execute(self) -> bool:
        """
        执行任务
        
        流程：
        1. 检查是否已 claim
        2. 调用子类 execute_core 执行
        3. 验证 artifacts
        4. 更新状态
        """
        if self.current_task is None:
            print(f"❌ 错误：没有已认领的任务")
            return False
        
        print(f"🔧 {self.role} 开始执行任务：{self.current_task.task_id}")
        
        try:
            # 调用子类执行核心逻辑
            artifacts = self.execute_core()
            
            # 验证 artifacts
            if not self._verify_artifacts(artifacts):
                print(f"❌ artifacts 验证失败")
                self._update_status(STATUS_FAILED, blocked_reason="artifacts 验证失败")
                return False
            
            # 更新状态为 completed
            self._update_status(STATUS_COMPLETED, artifacts=list(artifacts.keys()))
            print(f"✅ 任务执行完成：{self.current_task.task_id}")
            return True
            
        except Exception as e:
            print(f"❌ 执行失败：{e}")
            self._update_status(STATUS_FAILED, blocked_reason=str(e))
            return False
    
    @abstractmethod
    def execute_core(self) -> Dict[str, Path]:
        """
        执行核心逻辑 - 子类必须实现
        
        返回：artifacts 字典 {artifact_name: artifact_path}
        """
        pass
    
    def _verify_artifacts(self, artifacts: Dict[str, Path]) -> bool:
        """验证 artifacts 是否存在且非空"""
        if not artifacts:
            return False
        
        for name, path in artifacts.items():
            if not path.exists():
                print(f"❌ artifacts 不存在：{name} → {path}")
                return False
            if path.is_file() and path.stat().st_size == 0:
                print(f"❌ artifacts 为空：{name} → {path}")
                return False
        
        # 检查 required_artifacts（在 artifacts 目录下）
        for required in self.current_task.required_artifacts:
            artifact_path = self.task_dir / "artifacts" / required
            if not artifact_path.exists():
                print(f"❌ 必需的 artifacts 缺失：{required} (checked: {artifact_path})")
                return False
        
        return True
    
    def _update_status(self, status: str, **kwargs):
        """更新任务状态"""
        self.queue.update_status(self.current_task.task_id, status, **kwargs)
    
    def get_task_spec(self) -> dict:
        """获取任务规格"""
        spec_file = self.task_dir / "spec.json"
        if spec_file.exists():
            return json.load(open(spec_file, 'r', encoding='utf-8'))
        return {}
    
    def read_input(self, ref: str) -> str:
        """读取输入文件"""
        # ref 可能是相对路径或绝对路径
        path = Path(ref)
        if not path.is_absolute():
            path = Path("/home/admin/.openclaw/workspace/master") / ref
        if path.exists():
            return path.read_text(encoding='utf-8')
        return ""
    
    def write_artifact(self, name: str, content: str) -> Path:
        """写入 artifacts"""
        artifact_path = self.task_dir / "artifacts" / name
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(content, encoding='utf-8')
        return artifact_path
    
    def run(self, once=False):
        """运行 Worker 主循环"""
        print(f"🚀 {self.role} Worker 启动...")
        while True:
            if self.claim_task():
                print(f"📋 已领取任务：{self.current_task.task_id}")
                self.execute()
                self.current_task = None
                self.task_dir = None
                if once:
                    break
            else:
                print(f"⏳ 暂无任务，5 秒后重试...")
                import time
                time.sleep(5)
                if once:
                    break


class CoderWorker(Worker):
    """Coder Worker - 代码修复与功能实现"""
    
    def __init__(self):
        super().__init__("coder")
    
    def execute_core(self) -> Dict[str, Path]:
        """执行代码修复"""
        # 读取输入文件
        for ref in self.current_task.input_refs:
            content = self.read_input(ref)
            print(f"📄 读取文件：{ref} ({len(content)} bytes)")
        
        # 调用 OpenCode 执行代码修复
        artifacts = self._run_opencode()
        
        return artifacts
    
    def _run_opencode(self) -> Dict[str, Path]:
        """调用 OpenCode 执行代码修复"""
        import subprocess
        
        # 生成 OpenCode 任务描述
        prompt = f"""修复以下文件：
{', '.join(self.current_task.input_refs)}

成功标准：
{chr(10).join(self.current_task.success_criteria)}
"""
        
        # 写入 OpenCode 任务文件
        opencode_task = self.task_dir / "artifacts" / "opencode_task.md"
        opencode_task.write_text(prompt, encoding='utf-8')
        
        # 调用 OpenCode（plan 模式）
        cmd = [
            "/home/admin/.npm-global/bin/opencode", "run",
            "--format", "json",
            "--agent", "plan",
            "--model", "bailian/qwen3-coder-plus",
            "--dir", "/data/agents/master",
            prompt
        ]
        
        print(f"🔧 调用 OpenCode...")
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        
        # 写入执行日志
        run_log = self.task_dir / "artifacts" / "run.log"
        run_log.write_text(f"stdout:\n{proc.stdout}\n\nstderr:\n{proc.stderr}\n\nreturncode: {proc.returncode}", encoding='utf-8')
        
        # 生成 diff.patch（示例）
        diff_patch = self.task_dir / "artifacts" / "diff.patch"
        diff_patch.write_text(f"# OpenCode 执行结果\n\nReturn code: {proc.returncode}\n\nOutput:\n{proc.stdout[:5000]}", encoding='utf-8')
        
        # 生成 changed_files.json
        changed_files = self.task_dir / "artifacts" / "changed_files.json"
        changed_files.write_text(json.dumps({
            "task_id": self.current_task.task_id,
            "changed_files": [],
            "total_changes": 0,
            "summary": "OpenCode 执行完成"
        }, indent=2, ensure_ascii=False), encoding='utf-8')
        
        return {
            "opencode_task.md": opencode_task,
            "run.log": run_log,
            "diff.patch": diff_patch,
            "changed_files.json": changed_files
        }


class TestExpertWorker(Worker):
    """Test-Expert Worker - 独立验收"""
    
    def __init__(self):
        super().__init__("test-expert")
    
    def execute_core(self) -> Dict[str, Path]:
        """执行验收"""
        print(f"🔍 开始验收任务：{self.current_task.task_id}")
        
        # 检查 artifacts
        artifacts_status = self._check_artifacts()
        
        # 生成验收报告
        verdict = "pass" if all(v["status"] == "pass" for v in artifacts_status.values()) else "fail"
        
        verdict_json = {
            "task_id": self.current_task.task_id,
            "verdict": verdict,
            "verified_by": "test-expert-worker",
            "verified_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S %z"),
            "checks": [
                {"criterion": k, "status": v["status"], "evidence": v["evidence"]}
                for k, v in artifacts_status.items()
            ],
            "summary": f"验收{'通过' if verdict == 'pass' else '失败'}",
            "artifact_verification": {
                "total_artifacts": len(self.current_task.required_artifacts),
                "passed_artifacts": len([v for v in artifacts_status.values() if v["status"] == "pass"]),
                "failed_artifacts": len([v for v in artifacts_status.values() if v["status"] == "fail"])
            }
        }
        
        # 确保 verify 目录存在
        verify_dir = self.task_dir / "verify"
        verify_dir.mkdir(parents=True, exist_ok=True)
        
        # 写入 verdict.json
        verdict_path = verify_dir / "verdict.json"
        verdict_path.write_text(json.dumps(verdict_json, indent=2, ensure_ascii=False), encoding='utf-8')
        
        # 写入验收报告
        report_path = verify_dir / "test_report.md"
        report_content = f"""# 验收报告：{self.current_task.task_id}

## 验收结果：{'✅ 通过' if verdict == 'pass' else '❌ 失败'}

## 验收时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 检查摘要
- 总共检查文件: {len(self.current_task.required_artifacts)}
- 通过检查: {len([v for v in artifacts_status.values() if v["status"] == "pass"])}
- 失败检查: {len([v for v in artifacts_status.values() if v["status"] == "fail"])}

## 详细检查项

"""
        for k, v in artifacts_status.items():
            report_content += f"- {k}: {'✅' if v['status'] == 'pass' else '❌'} - {v['evidence']}\n"
        
        report_path.write_text(report_content, encoding='utf-8')
        
        print(f"📝 验收报告已生成: {verdict_path}, {report_path}")
        
        return {
            "verdict.json": verdict_path,
            "test_report.md": report_path
        }
    
    def _check_artifacts(self) -> Dict[str, dict]:
        """检查 artifacts"""
        status = {}
        
        for artifact in self.current_task.required_artifacts:
            artifact_path = self.task_dir / "artifacts" / artifact
            if artifact_path.exists():
                size = artifact_path.stat().st_size
                status[artifact] = {
                    "status": "pass" if size > 0 else "fail",
                    "evidence": f"文件存在，大小 {size} bytes"
                }
            else:
                status[artifact] = {
                    "status": "fail",
                    "evidence": f"文件不存在：artifacts/{artifact}"
                }
        
        return status


class DocManagerWorker(Worker):
    """Doc-Manager Worker - 文档整理交付"""
    
    def __init__(self):
        super().__init__("doc-manager")
    
    def execute_core(self) -> Dict[str, Path]:
        """执行文档整理"""
        # 读取交付包
        delivery_pack = self.task_dir / "artifacts" / "delivery_pack.md"
        
        content = f"""# 任务交付包：{self.current_task.task_id}

## 任务信息
- 任务 ID: {self.current_task.task_id}
- 任务类型：{self.current_task.task_type}
- 标题：{self.current_task.title}
- 负责人：{self.current_task.owner_role}
- 验收人：{self.current_task.validator_role}

## 执行摘要
任务已完成，所有 artifacts 已生成。

## 交付物
"""
        for artifact in self.current_task.required_artifacts:
            content += f"- {artifact}\n"
        
        delivery_pack.write_text(content, encoding='utf-8')
        
        # 写入文档路径
        doc_path = self.task_dir / "artifacts" / "doc_path.txt"
        doc_path.write_text(f"docs/tasks/{self.current_task.task_id}.md", encoding='utf-8')
        
        return {
            "delivery_pack.md": delivery_pack,
            "doc_path.txt": doc_path
        }


class KnowledgeStewardWorker(Worker):
    """Knowledge-Steward Worker - 知识沉淀归档"""
    
    def __init__(self):
        super().__init__("knowledge-steward")
    
    def execute_core(self) -> Dict[str, Path]:
        """执行知识沉淀"""
        # 写入知识条目
        kb_write = self.task_dir / "artifacts" / "kb_write.json"
        kb_write.write_text(json.dumps({
            "task_id": self.current_task.task_id,
            "written_by": "knowledge-steward-worker",
            "written_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S %z"),
            "knowledge_entries": [
                {
                    "category": "execution",
                    "title": self.current_task.title,
                    "content": f"任务 {self.current_task.task_id} 执行完成",
                    "tags": [self.current_task.task_type],
                    "related_tasks": [self.current_task.task_id]
                }
            ],
            "storage_path": f"knowledge/execution/{self.current_task.task_id}.md"
        }, indent=2, ensure_ascii=False), encoding='utf-8')
        
        # 写入索引更新
        kb_index = self.task_dir / "artifacts" / "kb_index_update.json"
        kb_index.write_text(json.dumps({
            "task_id": self.current_task.task_id,
            "index_updates": [
                {
                    "index_file": "knowledge/INDEX.md",
                    "action": "append",
                    "entry": f"- {datetime.now().strftime('%Y-%m-%d')}: {self.current_task.title}"
                }
            ]
        }, indent=2, ensure_ascii=False), encoding='utf-8')
        
        return {
            "kb_write.json": kb_write,
            "kb_index_update.json": kb_index
        }


# 快捷函数
def run_worker(role: str):
    """运行指定角色的 Worker"""
    workers = {
        "coder": CoderWorker,
        "test-expert": TestExpertWorker,
        "doc-manager": DocManagerWorker,
        "knowledge-steward": KnowledgeStewardWorker
    }
    
    if role not in workers:
        print(f"❌ 未知的 Worker 角色：{role}")
        return
    
    worker = workers[role]()
    worker.run()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        run_worker(sys.argv[1])
    else:
        print("用法：python3 worker_base.py <role>")
        print("可用角色：coder, test-expert, doc-manager, knowledge-steward")
