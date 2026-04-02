#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return {}
    txt = path.read_text(encoding='utf-8').strip()
    return json.loads(txt) if txt else {}


def evaluate_backtest_metrics(metrics_payload: dict[str, Any], criteria: dict[str, Any]) -> dict[str, Any]:
    metrics = metrics_payload.get('metrics', {}) if isinstance(metrics_payload.get('metrics', {}), dict) else {}
    checks = []

    total_return = metrics.get('total_return')
    sharpe = metrics.get('sharpe_ratio')
    drawdown = metrics.get('max_drawdown')
    trades = metrics.get('total_trades')

    passed = True

    if 'min_total_return' in criteria:
        threshold = criteria['min_total_return']
        ok = total_return is not None and total_return >= threshold
        checks.append({'name': 'min_total_return', 'value': total_return, 'threshold': threshold, 'passed': ok})
        passed = passed and ok

    if 'min_sharpe_ratio' in criteria:
        threshold = criteria['min_sharpe_ratio']
        ok = sharpe is not None and sharpe >= threshold
        checks.append({'name': 'min_sharpe_ratio', 'value': sharpe, 'threshold': threshold, 'passed': ok})
        passed = passed and ok

    if 'max_drawdown' in criteria:
        threshold = criteria['max_drawdown']
        ok = drawdown is not None and drawdown <= threshold
        checks.append({'name': 'max_drawdown', 'value': drawdown, 'threshold': threshold, 'passed': ok})
        passed = passed and ok

    if 'min_total_trades' in criteria:
        threshold = criteria['min_total_trades']
        ok = trades is not None and trades >= threshold
        checks.append({'name': 'min_total_trades', 'value': trades, 'threshold': threshold, 'passed': ok})
        passed = passed and ok

    return {
        'mode': criteria.get('mode', 'backtest_thresholds'),
        'passed': passed,
        'checks': checks,
        'metrics': {
            'total_return': total_return,
            'sharpe_ratio': sharpe,
            'max_drawdown': drawdown,
            'total_trades': trades,
        },
        'philosophy': 'robustness_first',
    }


def evaluate_backtest_task(task_dir: str | Path, criteria: dict[str, Any]) -> dict[str, Any]:
    task_dir = Path(task_dir)
    metrics_payload = load_json(task_dir / 'artifacts' / 'backtest_metrics.json')
    return evaluate_backtest_metrics(metrics_payload, criteria)
