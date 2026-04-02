#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生态工作流引擎（MVP+）

新增：
1. live heartbeat / status 持续写出
2. 全局状态面板数据 latest_status / latest_cycles / events
3. 长任务执行中的可见性增强，避免前端看起来像“卡住”
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

CONFIG_PATH = Path("/home/admin/.openclaw/workspace/master/config/ecosystem_workflow.json")
HEARTBEAT_INTERVAL_SECONDS = 10
POLL_INTERVAL_SECONDS = 2


def available_cycle_types() -> list[str]:
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return sorted(list(json.load(f).get('cycle_types', {}).keys()))
    except Exception:
        return ['daily_research', 'weekly_health']


@dataclass
class StageResult:
    success: bool
    exit_code: int
    task_file: Path
    log_file: Path
    task_data: Dict[str, Any]


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class WorkflowError(Exception):
    pass


class WorkflowEngine:
    def __init__(self, config_path: Path = CONFIG_PATH):
        self.config_path = config_path
        self.config = self._load_json(config_path)
        self.paths = self.config["paths"]
        self.workspace_root = Path(self.paths["workspace_root"])
        self.codebase_root = Path(self.paths["codebase_root"])
        self.python_bin = Path(self.paths["python_bin"])
        self.trace_root = Path(self.paths["trace_root"])
        self.reports_root = Path(self.paths["reports_root"])
        self.lock_root = Path(self.paths["lock_root"])
        self.state_root = self.reports_root / "state"
        self.latest_status_path = self.state_root / "latest_status.json"
        self.latest_cycles_path = self.state_root / "latest_cycles.json"
        self.events_path = self.state_root / "events.jsonl"

        for path in [self.trace_root, self.reports_root, self.lock_root, self.state_root]:
            path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _load_json(path: Path) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _write_json(path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _append_jsonl(self, path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _cycle_def(self, cycle_type: str) -> Dict[str, Any]:
        cycle_def = self.config.get("cycle_types", {}).get(cycle_type)
        if not cycle_def:
            raise WorkflowError(f"未知循环类型: {cycle_type}")
        return cycle_def

    def _render_command(self, command: str, cycle_dir: Path) -> str:
        mapping = {
            "workspace_root": str(self.workspace_root),
            "codebase_root": str(self.codebase_root),
            "python_bin": str(self.python_bin),
            "trace_root": str(self.trace_root),
            "reports_root": str(self.reports_root),
            "lock_root": str(self.lock_root),
            "cycle_dir": str(cycle_dir),
        }
        return command.format(**mapping)

    def _latest_cycle_dir(self, cycle_type: str) -> Optional[Path]:
        base = self.trace_root / cycle_type
        if not base.exists():
            return None
        candidates = [p for p in base.iterdir() if p.is_dir()]
        if not candidates:
            return None
        return sorted(candidates, key=lambda p: p.name)[-1]

    def _cycle_meta_path(self, cycle_dir: Path) -> Path:
        return cycle_dir / "meta.json"

    def _cycle_log_path(self, cycle_dir: Path) -> Path:
        return cycle_dir / "logs" / "cycle.log"

    def _cycle_live_status_path(self, cycle_dir: Path) -> Path:
        return cycle_dir / "reports" / "live_status.json"

    def _cycle_heartbeat_path(self, cycle_dir: Path) -> Path:
        return cycle_dir / "reports" / "heartbeat.json"

    def _append_cycle_log(self, cycle_dir: Path, message: str) -> None:
        log_path = self._cycle_log_path(cycle_dir)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        line = f"[{now_iso()}] {message}\n"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)
        print(message)

    def _lock_path(self, cycle_type: str) -> Path:
        return self.lock_root / f"{cycle_type}.lock.json"

    def _emit_event(self, event_type: str, cycle_meta: Dict[str, Any], extra: Optional[Dict[str, Any]] = None) -> None:
        payload = {
            "event_type": event_type,
            "time": now_iso(),
            "cycle_id": cycle_meta.get("cycle_id"),
            "cycle_type": cycle_meta.get("cycle_type"),
            "status": cycle_meta.get("status"),
            "current_stage": cycle_meta.get("current_stage"),
        }
        if extra:
            payload.update(extra)
        self._append_jsonl(self.events_path, payload)

    def _update_latest_cycle_pointer(self, cycle_meta: Dict[str, Any]) -> None:
        data: Dict[str, Any] = {}
        if self.latest_cycles_path.exists():
            data = self._load_json(self.latest_cycles_path)
        data[cycle_meta["cycle_type"]] = {
            "cycle_id": cycle_meta.get("cycle_id"),
            "status": cycle_meta.get("status"),
            "current_stage": cycle_meta.get("current_stage"),
            "updated_at": cycle_meta.get("updated_at"),
            "cycle_dir": cycle_meta.get("paths", {}).get("cycle_dir"),
        }
        self._write_json(self.latest_cycles_path, data)

    def _publish_status(
        self,
        cycle_dir: Path,
        cycle_meta: Dict[str, Any],
        stage_status: Optional[str] = None,
        task_path: Optional[Path] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload: Dict[str, Any] = {
            "cycle_id": cycle_meta.get("cycle_id"),
            "cycle_type": cycle_meta.get("cycle_type"),
            "description": cycle_meta.get("description"),
            "status": cycle_meta.get("status"),
            "current_stage": cycle_meta.get("current_stage"),
            "stage_status": stage_status,
            "updated_at": cycle_meta.get("updated_at"),
            "trigger": cycle_meta.get("trigger"),
            "cycle_dir": cycle_meta.get("paths", {}).get("cycle_dir"),
        }
        if task_path:
            payload["task_file"] = str(task_path)
        if extra:
            payload.update(extra)

        self._write_json(self._cycle_live_status_path(cycle_dir), payload)
        self._write_json(self._cycle_heartbeat_path(cycle_dir), payload)
        self._write_json(self.latest_status_path, payload)
        self._update_latest_cycle_pointer(cycle_meta)

    def acquire_lock(self, cycle_type: str, cycle_id: str, force: bool = False) -> None:
        lock_path = self._lock_path(cycle_type)
        if lock_path.exists() and not force:
            existing = self._load_json(lock_path)
            raise WorkflowError(
                f"循环 {cycle_type} 已被锁定: cycle_id={existing.get('cycle_id')} pid={existing.get('pid')}"
            )
        payload = {
            "cycle_type": cycle_type,
            "cycle_id": cycle_id,
            "pid": os.getpid(),
            "locked_at": now_iso(),
        }
        self._write_json(lock_path, payload)

    def release_lock(self, cycle_type: str) -> None:
        lock_path = self._lock_path(cycle_type)
        if lock_path.exists():
            lock_path.unlink()

    def unlock(self, cycle_type: str) -> None:
        self.release_lock(cycle_type)
        print(f"已解除锁: {cycle_type}")

    def init_cycle(self, cycle_type: str, trigger: str = "manual") -> Path:
        cycle_def = self._cycle_def(cycle_type)
        cycle_id = f"{cycle_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        cycle_dir = self.trace_root / cycle_type / cycle_id
        for sub in ["tasks", "artifacts", "reports", "logs"]:
            (cycle_dir / sub).mkdir(parents=True, exist_ok=True)

        meta = {
            "cycle_id": cycle_id,
            "cycle_type": cycle_type,
            "description": cycle_def.get("description"),
            "trigger": trigger,
            "status": "initialized",
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "current_stage": None,
            "stages": [stage["id"] for stage in cycle_def.get("stages", [])],
            "approval": self.config.get("approval", {}),
            "notifications": self.config.get("notifications", {}),
            "paths": {
                "cycle_dir": str(cycle_dir),
                "codebase_root": str(self.codebase_root),
                "workspace_root": str(self.workspace_root),
            },
            "summary": {},
        }
        self._write_json(self._cycle_meta_path(cycle_dir), meta)
        self._append_cycle_log(cycle_dir, f"初始化循环: {cycle_id} ({cycle_type})")
        self._publish_status(cycle_dir, meta, stage_status="initialized")
        self._emit_event("cycle_initialized", meta)
        return cycle_dir

    def load_cycle_meta(self, cycle_dir: Path) -> Dict[str, Any]:
        return self._load_json(self._cycle_meta_path(cycle_dir))

    def save_cycle_meta(self, cycle_dir: Path, meta: Dict[str, Any]) -> None:
        meta["updated_at"] = now_iso()
        self._write_json(self._cycle_meta_path(cycle_dir), meta)

    def _stage_task_path(self, cycle_dir: Path, order: int, stage_id: str) -> Path:
        return cycle_dir / "tasks" / f"{order:02d}_{stage_id}.json"

    def run_stage(
        self,
        cycle_dir: Path,
        cycle_type: str,
        stage_def: Dict[str, Any],
        order: int,
        dry_run: bool = False,
    ) -> StageResult:
        stage_id = stage_def["id"]
        meta = self.load_cycle_meta(cycle_dir)
        meta["current_stage"] = stage_id
        meta["status"] = "running"
        self.save_cycle_meta(cycle_dir, meta)

        task_path = self._stage_task_path(cycle_dir, order, stage_id)
        log_path = cycle_dir / "logs" / f"{order:02d}_{stage_id}.log"
        retries = int(stage_def.get("retry", 0))
        timeout = int(stage_def.get("timeout_seconds", 300))
        raw_command = self._render_command(stage_def["command"], cycle_dir)

        task = {
            "task_id": f"{meta['cycle_id']}::{stage_id}",
            "cycle_id": meta["cycle_id"],
            "cycle_type": cycle_type,
            "stage": stage_id,
            "owner_agent": stage_def.get("owner"),
            "mode": stage_def.get("mode", "command"),
            "status": "queued",
            "timeout_seconds": timeout,
            "retry_limit": retries,
            "attempts": [],
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "command": raw_command,
            "log_file": str(log_path),
        }
        self._write_json(task_path, task)

        self._append_cycle_log(cycle_dir, f"开始阶段: {stage_id} | owner={stage_def.get('owner')}")
        self._publish_status(cycle_dir, meta, stage_status="queued", task_path=task_path)
        self._emit_event("stage_started", meta, {"stage": stage_id, "task_file": str(task_path)})

        if dry_run:
            task["status"] = "dry_run"
            task["updated_at"] = now_iso()
            task["attempts"].append({
                "attempt": 1,
                "started_at": now_iso(),
                "finished_at": now_iso(),
                "exit_code": 0,
                "result": "dry_run",
            })
            self._write_json(task_path, task)
            self._append_cycle_log(cycle_dir, f"阶段 dry-run 完成: {stage_id}")
            self._publish_status(cycle_dir, meta, stage_status="dry_run", task_path=task_path)
            self._emit_event("stage_completed", meta, {"stage": stage_id, "dry_run": True})
            return StageResult(True, 0, task_path, log_path, task)

        success = False
        exit_code = 1
        timed_out = False

        for attempt in range(1, retries + 2):
            started = now_iso()
            task["status"] = "running"
            task["updated_at"] = started
            self._write_json(task_path, task)
            meta = self.load_cycle_meta(cycle_dir)
            self._publish_status(
                cycle_dir,
                meta,
                stage_status="running",
                task_path=task_path,
                extra={"attempt": attempt, "timeout_seconds": timeout},
            )

            with open(log_path, "a", encoding="utf-8") as lf:
                lf.write(f"\n===== ATTEMPT {attempt} {started} =====\n")
                lf.flush()
                proc = subprocess.Popen(
                    raw_command,
                    cwd=str(self.workspace_root),
                    shell=True,
                    stdout=lf,
                    stderr=subprocess.STDOUT,
                    executable="/bin/bash",
                )
                start_ts = time.monotonic()
                last_heartbeat = 0.0

                while True:
                    exit_code = proc.poll()
                    elapsed = int(time.monotonic() - start_ts)
                    if elapsed - last_heartbeat >= HEARTBEAT_INTERVAL_SECONDS:
                        meta = self.load_cycle_meta(cycle_dir)
                        heartbeat_extra = {
                            "attempt": attempt,
                            "elapsed_seconds": elapsed,
                            "pid": proc.pid,
                            "timeout_seconds": timeout,
                            "log_file": str(log_path),
                        }
                        self._publish_status(
                            cycle_dir,
                            meta,
                            stage_status="running",
                            task_path=task_path,
                            extra=heartbeat_extra,
                        )
                        self._emit_event("stage_heartbeat", meta, {"stage": stage_id, **heartbeat_extra})
                        last_heartbeat = float(elapsed)

                    if exit_code is not None:
                        break

                    if elapsed >= timeout:
                        timed_out = True
                        proc.kill()
                        exit_code = -9
                        with open(log_path, "a", encoding="utf-8") as timeout_log:
                            timeout_log.write(f"\n[TIMEOUT] stage={stage_id} elapsed={elapsed}s timeout={timeout}s\n")
                        break

                    time.sleep(POLL_INTERVAL_SECONDS)

            finished = now_iso()
            attempt_payload = {
                "attempt": attempt,
                "started_at": started,
                "finished_at": finished,
                "exit_code": exit_code,
                "result": "timeout" if timed_out else ("success" if exit_code == 0 else "failed"),
            }
            task["attempts"].append(attempt_payload)
            task["updated_at"] = finished
            if exit_code == 0:
                success = True
                task["status"] = "completed"
                break
            task["status"] = "retrying" if attempt <= retries else "failed"
            self._write_json(task_path, task)
            self._append_cycle_log(cycle_dir, f"阶段失败: {stage_id} attempt={attempt} exit_code={exit_code}")
            meta = self.load_cycle_meta(cycle_dir)
            self._publish_status(
                cycle_dir,
                meta,
                stage_status=task["status"],
                task_path=task_path,
                extra={"attempt": attempt, "exit_code": exit_code, "timed_out": timed_out},
            )
            self._emit_event(
                "stage_failed_attempt",
                meta,
                {"stage": stage_id, "attempt": attempt, "exit_code": exit_code, "timed_out": timed_out},
            )
            if attempt <= retries:
                time.sleep(1)

        task["updated_at"] = now_iso()
        task["finished_at"] = now_iso()
        task["exit_code"] = exit_code
        meta = self.load_cycle_meta(cycle_dir)
        if success:
            task["status"] = "completed"
            self._append_cycle_log(cycle_dir, f"阶段完成: {stage_id}")
            self._publish_status(cycle_dir, meta, stage_status="completed", task_path=task_path)
            self._emit_event("stage_completed", meta, {"stage": stage_id, "exit_code": exit_code})
        else:
            task["status"] = "failed"
            self._publish_status(
                cycle_dir,
                meta,
                stage_status="failed",
                task_path=task_path,
                extra={"exit_code": exit_code, "timed_out": timed_out},
            )
            self._emit_event("stage_failed", meta, {"stage": stage_id, "exit_code": exit_code, "timed_out": timed_out})
        self._write_json(task_path, task)
        return StageResult(success, exit_code, task_path, log_path, task)

    def run_cycle(
        self,
        cycle_type: str,
        trigger: str = "manual",
        dry_run: bool = False,
        force_unlock: bool = False,
        stop_after: Optional[str] = None,
        only_stage: Optional[str] = None,
    ) -> Path:
        cycle_def = self._cycle_def(cycle_type)
        cycle_dir = self.init_cycle(cycle_type, trigger=trigger)
        cycle_id = cycle_dir.name
        self.acquire_lock(cycle_type, cycle_id, force=force_unlock)

        try:
            stages = cycle_def.get("stages", [])
            if only_stage:
                stages = [s for s in stages if s["id"] == only_stage]
                if not stages:
                    raise WorkflowError(f"循环 {cycle_type} 中不存在阶段: {only_stage}")

            for order, stage_def in enumerate(stages, start=1):
                result = self.run_stage(cycle_dir, cycle_type, stage_def, order, dry_run=dry_run)
                if not result.success:
                    meta = self.load_cycle_meta(cycle_dir)
                    meta["status"] = "failed"
                    meta["failed_stage"] = stage_def["id"]
                    meta["failed_task_file"] = str(result.task_file)
                    self.save_cycle_meta(cycle_dir, meta)
                    self._publish_status(cycle_dir, meta, stage_status="failed", task_path=result.task_file)
                    self._emit_event("cycle_failed", meta, {"failed_stage": stage_def["id"]})
                    raise WorkflowError(f"循环失败: stage={stage_def['id']} exit_code={result.exit_code}")
                if stop_after and stage_def["id"] == stop_after:
                    meta = self.load_cycle_meta(cycle_dir)
                    meta["status"] = "stopped_after_stage"
                    meta["stopped_stage"] = stage_def["id"]
                    self.save_cycle_meta(cycle_dir, meta)
                    self._publish_status(cycle_dir, meta, stage_status="stopped_after_stage", task_path=result.task_file)
                    self._emit_event("cycle_stopped", meta, {"stopped_stage": stage_def["id"]})
                    self._append_cycle_log(cycle_dir, f"按要求在阶段结束后停止: {stage_def['id']}")
                    return cycle_dir

            meta = self.load_cycle_meta(cycle_dir)
            meta["status"] = "completed" if not dry_run else "dry_run_completed"
            meta["current_stage"] = None
            self.save_cycle_meta(cycle_dir, meta)
            self._publish_status(cycle_dir, meta, stage_status="completed")
            self._emit_event("cycle_completed", meta)
            self._append_cycle_log(cycle_dir, f"循环完成: {meta['cycle_id']}")
            return cycle_dir
        finally:
            self.release_lock(cycle_type)

    def print_status(self, cycle_type: Optional[str] = None) -> None:
        if cycle_type:
            latest = self._latest_cycle_dir(cycle_type)
            if not latest:
                print(f"[{cycle_type}] 暂无循环记录")
                return
            live_path = self._cycle_live_status_path(latest)
            if live_path.exists():
                print(json.dumps(self._load_json(live_path), ensure_ascii=False, indent=2))
                return
            meta = self.load_cycle_meta(latest)
            print(json.dumps({
                "cycle_type": cycle_type,
                "latest_cycle": meta.get("cycle_id"),
                "status": meta.get("status"),
                "current_stage": meta.get("current_stage"),
                "updated_at": meta.get("updated_at"),
                "cycle_dir": str(latest),
            }, ensure_ascii=False, indent=2))
            return

        payload: Dict[str, Any] = {
            "latest_status": self._load_json(self.latest_status_path) if self.latest_status_path.exists() else None,
            "latest_cycles": self._load_json(self.latest_cycles_path) if self.latest_cycles_path.exists() else {},
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生态工作流引擎")
    sub = parser.add_subparsers(dest="cmd", required=True)

    cycle_choices = available_cycle_types()

    run_p = sub.add_parser("run", help="运行一个循环")
    run_p.add_argument("--cycle-type", required=True, choices=cycle_choices)
    run_p.add_argument("--trigger", default="manual")
    run_p.add_argument("--dry-run", action="store_true")
    run_p.add_argument("--force-unlock", action="store_true")
    run_p.add_argument("--stop-after")
    run_p.add_argument("--only-stage")

    init_p = sub.add_parser("init", help="仅初始化循环目录")
    init_p.add_argument("--cycle-type", required=True, choices=cycle_choices)
    init_p.add_argument("--trigger", default="manual")

    status_p = sub.add_parser("status", help="查看状态")
    status_p.add_argument("--cycle-type", choices=cycle_choices)

    unlock_p = sub.add_parser("unlock", help="解除循环锁")
    unlock_p.add_argument("--cycle-type", required=True, choices=cycle_choices)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    engine = WorkflowEngine()
    try:
        if args.cmd == "run":
            cycle_dir = engine.run_cycle(
                cycle_type=args.cycle_type,
                trigger=args.trigger,
                dry_run=args.dry_run,
                force_unlock=args.force_unlock,
                stop_after=args.stop_after,
                only_stage=args.only_stage,
            )
            print(f"循环输出目录: {cycle_dir}")
            return 0
        if args.cmd == "init":
            cycle_dir = engine.init_cycle(args.cycle_type, trigger=args.trigger)
            print(f"已初始化: {cycle_dir}")
            return 0
        if args.cmd == "status":
            engine.print_status(args.cycle_type)
            return 0
        if args.cmd == "unlock":
            engine.unlock(args.cycle_type)
            return 0
        raise WorkflowError(f"未知命令: {args.cmd}")
    except WorkflowError as e:
        print(f"[WORKFLOW ERROR] {e}", file=sys.stderr)
        return 2
    except subprocess.TimeoutExpired as e:
        print(f"[WORKFLOW TIMEOUT] {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
