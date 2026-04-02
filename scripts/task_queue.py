#!/usr/bin/env python3
"""
任务队列系统 - Worker 架构核心

所有执行型 agent 都通过任务队列接收任务，强制 claim，强制产出，强制验收。
"""

import json
import fcntl
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict

# 任务根目录
JOBS_ROOT = Path("/home/admin/.openclaw/workspace/master/traces/jobs")
QUEUE_FILE = JOBS_ROOT / "queue.jsonl"
LOCK_FILE = JOBS_ROOT / "queue.lock"

# 任务状态
STATUS_QUEUED = "queued"
STATUS_CLAIMED = "claimed"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_VERIFIED = "verified"
STATUS_FAILED = "failed"
STATUS_FINALIZED = "finalized"


@dataclass
class Task:
    task_id: str
    task_type: str
    title: str
    owner_role: str
    validator_role: str
    input_refs: List[str]
    required_artifacts: List[str]
    success_criteria: List[str]
    status: str = STATUS_QUEUED
    claimed_by: Optional[str] = None
    claimed_at: Optional[str] = None
    lease_until: Optional[str] = None
    attempt: int = 0
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S %z")
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class TaskQueue:
    """任务队列 - 线程安全的任务管理"""
    
    def __init__(self, queue_file: Path = QUEUE_FILE, lock_file: Path = LOCK_FILE):
        self.queue_file = queue_file
        self.lock_file = lock_file
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)
        self.lock_file.touch(exist_ok=True)
    
    def _acquire_lock(self):
        """获取文件锁"""
        self._lock_fd = open(self.lock_file, 'w')
        fcntl.flock(self._lock_fd.fileno(), fcntl.LOCK_EX)
    
    def _release_lock(self):
        """释放文件锁"""
        fcntl.flock(self._lock_fd.fileno(), fcntl.LOCK_UN)
        self._lock_fd.close()
    
    def push(self, task: Task) -> bool:
        """推送任务到队列"""
        self._acquire_lock()
        try:
            with open(self.queue_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(task.to_dict(), ensure_ascii=False) + '\n')
            # 同时创建任务目录和 spec.json
            task_dir = JOBS_ROOT / task.task_id
            task_dir.mkdir(parents=True, exist_ok=True)
            
            spec = {
                "task_id": task.task_id,
                "task_type": task.task_type,
                "title": task.title,
                "owner_role": task.owner_role,
                "validator_role": task.validator_role,
                "input_refs": task.input_refs,
                "required_artifacts": task.required_artifacts,
                "success_criteria": task.success_criteria,
                "created_at": task.created_at
            }
            with open(task_dir / "spec.json", 'w', encoding='utf-8') as f:
                json.dump(spec, f, indent=2, ensure_ascii=False)
            
            # 初始化 claim.json
            claim = {
                "task_id": task.task_id,
                "claimed_by": None,
                "claimed_at": None,
                "lease_until": None,
                "attempt": 0,
                "status": "unclaimed"
            }
            with open(task_dir / "claim.json", 'w', encoding='utf-8') as f:
                json.dump(claim, f, indent=2, ensure_ascii=False)
            
            # 初始化 status.json
            status = {
                "task_id": task.task_id,
                "status": STATUS_QUEUED,
                "retry_count": 0,
                "blocked_reason": None,
                "next_retry_at": None,
                "updated_at": task.created_at
            }
            with open(task_dir / "status.json", 'w', encoding='utf-8') as f:
                json.dump(status, f, indent=2, ensure_ascii=False)
            
            # 创建 artifacts 目录
            (task_dir / "artifacts").mkdir(exist_ok=True)
            (task_dir / "verify").mkdir(exist_ok=True)
            (task_dir / "approval").mkdir(exist_ok=True)
            
            return True
        finally:
            self._release_lock()
    
    def pop(self, role: str, lease_hours: int = 1) -> Optional[Task]:
        """从队列领取任务（强制 claim）"""
        self._acquire_lock()
        try:
            if not self.queue_file.exists():
                return None
            
            tasks = []
            with open(self.queue_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        tasks.append(json.loads(line))
            
            # 查找可领取的任务
            now = datetime.now()
            for i, task_data in enumerate(tasks):
                task = Task.from_dict(task_data)
                
                # 检查角色匹配
                if task.owner_role != role:
                    continue
                
                # 检查状态
                if task.status not in [STATUS_QUEUED, STATUS_FAILED]:
                    continue
                
                # 检查租约（如果已被认领但未超时，不能领取）
                if task.claimed_by and task.lease_until:
                    lease_until = datetime.fromisoformat(task.lease_until)
                    if now < lease_until:
                        continue
                
                # 领取任务
                task.claimed_by = role
                task.claimed_at = now.strftime("%Y-%m-%d %H:%M:%S %z")
                task.lease_until = (now + timedelta(hours=lease_hours)).isoformat()
                task.attempt += 1
                task.status = STATUS_CLAIMED
                
                # 更新队列文件
                tasks[i] = task.to_dict()
                with open(self.queue_file, 'w', encoding='utf-8') as f:
                    for t in tasks:
                        f.write(json.dumps(t, ensure_ascii=False) + '\n')
                
                # 更新 claim.json
                claim = {
                    "task_id": task.task_id,
                    "claimed_by": role,
                    "claimed_at": task.claimed_at,
                    "lease_until": task.lease_until,
                    "attempt": task.attempt,
                    "status": "claimed"
                }
                task_dir = JOBS_ROOT / task.task_id
                with open(task_dir / "claim.json", 'w', encoding='utf-8') as f:
                    json.dump(claim, f, indent=2, ensure_ascii=False)
                
                # 更新 status.json
                status = {
                    "task_id": task.task_id,
                    "status": STATUS_RUNNING,
                    "retry_count": task.attempt - 1,
                    "blocked_reason": None,
                    "next_retry_at": None,
                    "updated_at": task.claimed_at
                }
                with open(task_dir / "status.json", 'w', encoding='utf-8') as f:
                    json.dump(status, f, indent=2, ensure_ascii=False)
                
                return task
            
            return None
        finally:
            self._release_lock()
    
    def update_status(self, task_id: str, status: str, **kwargs):
        """更新任务状态"""
        self._acquire_lock()
        try:
            if not self.queue_file.exists():
                return
            
            tasks = []
            with open(self.queue_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        tasks.append(json.loads(line))
            
            for i, task_data in enumerate(tasks):
                if task_data.get("task_id") == task_id:
                    tasks[i]["status"] = status
                    tasks[i].update(kwargs)
                    break
            
            with open(self.queue_file, 'w', encoding='utf-8') as f:
                for t in tasks:
                    f.write(json.dumps(t, ensure_ascii=False) + '\n')
            
            # 同时更新 status.json
            task_dir = JOBS_ROOT / task_id
            status_file = task_dir / "status.json"
            if status_file.exists():
                status_data = json.load(open(status_file, 'r', encoding='utf-8'))
                status_data["status"] = status
                status_data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S %z")
                status_data.update(kwargs)
                with open(status_file, 'w', encoding='utf-8') as f:
                    json.dump(status_data, f, indent=2, ensure_ascii=False)
        finally:
            self._release_lock()
    
    def list_pending(self, role: str = None) -> List[Task]:
        """列出待处理任务"""
        if not self.queue_file.exists():
            return []
        
        tasks = []
        with open(self.queue_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    task_data = json.loads(line)
                    task = Task.from_dict(task_data)
                    if task.status in [STATUS_QUEUED, STATUS_FAILED]:
                        if role is None or task.owner_role == role:
                            tasks.append(task)
        return tasks


# 快捷函数
def create_task(
    task_id: str,
    task_type: str,
    title: str,
    owner_role: str,
    validator_role: str,
    input_refs: List[str],
    required_artifacts: List[str],
    success_criteria: List[str]
) -> bool:
    """创建任务并推送到队列"""
    queue = TaskQueue()
    task = Task(
        task_id=task_id,
        task_type=task_type,
        title=title,
        owner_role=owner_role,
        validator_role=validator_role,
        input_refs=input_refs,
        required_artifacts=required_artifacts,
        success_criteria=success_criteria
    )
    return queue.push(task)


def claim_task(role: str, lease_hours: int = 1) -> Optional[Task]:
    """领取任务"""
    queue = TaskQueue()
    return queue.pop(role, lease_hours)
