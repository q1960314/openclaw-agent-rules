#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unified decision engine for intake routing, optimization loops, governance, and demand analysis."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path('/home/admin/.openclaw/workspace/master')
RECENT_LEARNING_STATE = ROOT / 'reports' / 'worker-runtime' / 'state' / 'latest_recent_ecosystem_learning.json'

GENERIC_OBJECTIVE_PHRASES = {
    '优化一下', '优化下', '看看怎么改', '修一下', '修复一下', '改一下',
    'improve it', 'fix it', 'optimize it', 'make it better', 'review it',
}


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = re.sub(r'\s+', ' ', str(item)).strip(' -、,，;；。\n\t')
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def _split_objective(objective: str) -> list[str]:
    parts = re.split(r'[\n；;。|]+|(?:,\s*)|(?:，\s*)|(?:\band\b)|(?:\bthen\b)|(?:\bwith\b)', objective)
    return _dedupe(parts)


def _load_recent_learning_state() -> dict[str, Any]:
    if not RECENT_LEARNING_STATE.exists():
        return {}
    try:
        text = RECENT_LEARNING_STATE.read_text(encoding='utf-8').strip()
        return json.loads(text) if text else {}
    except Exception:
        return {}


def infer_recent_learning_context(intent: str, role: str) -> dict[str, Any]:
    payload = _load_recent_learning_state()
    if not payload:
        return {
            'available': False,
            'recent_task_count': 0,
            'dominant_expert_role': None,
            'adaptive_dominant_next_role': None,
            'focus_signals': [],
            'relevant_signal_counts': {},
            'sample_examples': [],
        }
    preferred_keys = {
        'strategy-expert': ['code_touchpoints', 'change_priority', 'factor_handoff', 'parameter_handoff', 'backtest_handoff', 'validation_priority'],
        'parameter-evolver': ['sensitivity_rationales', 'range_justification', 'metric_guardrails', 'code_touchpoints', 'change_priority', 'backtest_handoff'],
        'factor-miner': ['applicability_conditions', 'code_touchpoints', 'strategy_handoff', 'parameter_handoff', 'validation_priority'],
        'backtest-engine': ['backtest_handoff', 'validation_priority', 'metric_guardrails', 'range_justification'],
        'data-collector': ['code_touchpoints', 'validation_priority', 'backtest_handoff', 'change_priority'],
        'coder': ['code_touchpoints', 'change_priority', 'validation_priority', 'parameter_handoff', 'factor_handoff'],
    }
    signal_counts = payload.get('reusable_signal_counts', {}) or {}
    role_keys = preferred_keys.get(role, ['code_touchpoints', 'validation_priority', 'change_priority'])
    focus_counts = {key: signal_counts[key] for key in role_keys if key in signal_counts}
    focus_signals = sorted(focus_counts, key=lambda key: (-focus_counts[key], key))[:4]
    sample_examples = []
    for item in payload.get('recent_examples', [])[:3]:
        preview = item.get('signal_preview', {}) or {}
        filtered_preview = {key: preview[key] for key in focus_signals if key in preview}
        if filtered_preview:
            sample_examples.append({
                'task_id': item.get('task_id'),
                'role': item.get('role'),
                'objective': item.get('objective'),
                'signal_preview': filtered_preview,
            })
    return {
        'available': True,
        'recent_task_count': int(payload.get('recent_task_count', 0) or 0),
        'dominant_expert_role': payload.get('dominant_expert_role'),
        'adaptive_dominant_next_role': (payload.get('adaptive_loop_bridge', {}) or {}).get('dominant_next_role'),
        'focus_signals': focus_signals,
        'relevant_signal_counts': focus_counts,
        'sample_examples': sample_examples,
    }


def infer_recent_learning_guidance(recent_learning_context: dict[str, Any], role: str) -> list[str]:
    if not recent_learning_context.get('available'):
        return []
    guidance: list[str] = []
    recent_task_count = recent_learning_context.get('recent_task_count')
    dominant_expert_role = recent_learning_context.get('dominant_expert_role')
    adaptive_dominant_next_role = recent_learning_context.get('adaptive_dominant_next_role')
    focus_signals = recent_learning_context.get('focus_signals', []) or []
    if recent_task_count:
        guidance.append(
            f'最近已沉淀 {recent_task_count} 个专家样本；当前主导沉淀角色={dominant_expert_role}，adaptive 主导流向={adaptive_dominant_next_role}。'
        )
    if focus_signals:
        guidance.append('当前这类任务优先参考这些经验信号：' + '、'.join(focus_signals[:4]))
    sample_examples = recent_learning_context.get('sample_examples', []) or []
    for item in sample_examples[:2]:
        preview = item.get('signal_preview', {}) or {}
        preview_items: list[str] = []
        for key, values in preview.items():
            if isinstance(values, list) and values:
                preview_items.append(f'{key}:{values[0]}')
            if len(preview_items) >= 2:
                break
        if preview_items:
            guidance.append(
                f"参考样本 {item.get('task_id')} ({item.get('role')})：" + '；'.join(preview_items)
            )
    return _dedupe(guidance)


def classify_terminal_status(*, review_decision: str | None = None, retry_created: bool = False, stop_eval: dict[str, Any] | None = None, round_exhausted: bool = False) -> str:
    if review_decision == 'passed':
        return 'passed'
    if review_decision == 'manual_review_required':
        return 'manual_review_required'
    if retry_created and round_exhausted:
        return 'retry_exhausted'
    if retry_created:
        return 'retry_created'
    if stop_eval is not None:
        if stop_eval.get('passed'):
            return 'passed'
        if round_exhausted:
            return 'threshold_not_met'
    if review_decision in {'rejected', 'failed'}:
        return 'blocked'
    return 'manual_review_required'


def intake_type(objective: str) -> str:
    lower = objective.lower()
    if _contains_any(lower, ['ops', 'monitor', 'health', 'status', '运维', '监控', '健康检查']):
        return 'ops'
    if _contains_any(lower, ['data', 'snapshot', 'quality', 'parquet', '数据', '快照', '质量']):
        return 'data'
    if _contains_any(lower, ['factor', 'rankic', '因子']):
        return 'factor'
    if _contains_any(lower, ['parameter', 'params', 'threshold', 'window', '参数', '阈值', '调参']):
        return 'parameter'
    if _contains_any(lower, ['strategy', 'signal', '选股', '策略', '信号']):
        return 'strategy'
    if _contains_any(lower, ['sentiment', 'emotion', '舆情', '情绪']):
        return 'sentiment'
    if _contains_any(lower, ['finance', 'research', 'study', '研报', '研究', '金融']):
        return 'finance'
    if _contains_any(lower, ['backtest', '回测', '绩效', 'performance']):
        return 'backtest'
    return 'code'


def route_worker_role(objective: str) -> str:
    intent = intake_type(objective)
    mapping = {
        'ops': 'ops-monitor',
        'data': 'data-collector',
        'backtest': 'backtest-engine',
        'factor': 'factor-miner',
        'sentiment': 'sentiment-analyst',
        'finance': 'finance-learner',
        'parameter': 'parameter-evolver',
        'strategy': 'strategy-expert',
        'code': 'coder',
    }
    return mapping[intent]


def execution_mode(objective: str, role: str) -> str:
    lower = objective.lower()
    if role in {'strategy-expert', 'parameter-evolver', 'factor-miner', 'sentiment-analyst', 'finance-learner'}:
        return 'plan'
    if role in {'backtest-engine', 'data-collector', 'ops-monitor'}:
        return 'native'
    build_keywords = ['fix', 'bug', 'build', 'create', 'add', 'modify', 'update', 'write', '实现', '修复', '新增', '修改']
    plan_keywords = ['plan', 'review', 'diagnose', 'analysis', 'analyze', '方案', '分析', '评审', '诊断', '计划']
    if _contains_any(lower, build_keywords):
        return 'build'
    if _contains_any(lower, plan_keywords):
        return 'plan'
    return 'plan'


def auto_retry_allowed(role: str) -> bool:
    return role in {'ops-monitor', 'data-collector', 'backtest-engine'}


def infer_risk_tags(objective: str, role: str) -> list[str]:
    lower = objective.lower()
    tags: list[str] = []
    if _contains_any(lower, ['drawdown', '回撤', 'risk', '风控', '风险']):
        tags.append('drawdown_risk')
    if _contains_any(lower, ['data', 'parquet', 'snapshot', 'quality', '数据']):
        tags.append('data_quality_risk')
    if _contains_any(lower, ['optimize', 'parameter', 'factor', '调参', '因子', '优化']):
        tags.append('overfit_risk')
    if _contains_any(lower, ['build', 'fix', 'modify', 'write', '修复', '修改', '代码', 'patch']):
        tags.append('code_change_risk')
    if _contains_any(lower, ['config', '配置', '参数生效', '切换', '上线', '发布', 'restart', 'gateway']):
        tags.append('config_change_risk')
    if _contains_any(lower, ['trade', '实盘', '下单', '交易', 'buy', 'sell']):
        tags.append('manual_trade_risk')
    if role == 'backtest-engine':
        tags.append('backtest_bias_risk')
    return sorted(set(tags))


def infer_acceptance_hints(intent: str, role: str) -> list[str]:
    hints = {
        'code': ['必须生成真实改动证据', '必须通过 test-expert 验收'],
        'strategy': ['必须给出多方案或明确推荐路径', '必须说明验证路径'],
        'parameter': ['必须给出参数候选与边界', '必须说明验证优先级'],
        'factor': ['必须给出候选因子与研究建议', '必须说明验证方向'],
        'backtest': ['必须输出关键回测指标', '必须可用于 stop criteria 判断'],
        'data': ['必须输出数据质量结论', '必须给出可追踪快照/校验结果'],
        'ops': ['必须输出系统健康结论', '必须给出治理建议'],
        'finance': ['必须给出可落地研究启发', '必须避免空泛摘要'],
        'sentiment': ['必须给出情绪驱动与风险提示', '必须结构化总结'],
    }
    return hints.get(intent, [f'必须满足 {role} 的核心产物要求'])


def infer_main_objective(objective: str) -> str:
    clauses = _split_objective(objective)
    if clauses:
        return clauses[0]
    return objective.strip() or '完成当前任务'


def infer_sub_objectives(intent: str, role: str, objective: str) -> list[str]:
    clauses = _split_objective(objective)
    if len(clauses) > 1:
        return clauses[:4]

    defaults = {
        'code': [
            '定位需要修改的代码与影响范围',
            '产出最小必要改动',
            '保留验证与回滚线索',
        ],
        'strategy': [
            '拆解当前策略问题与目标',
            '给出可执行策略方案',
            '明确验证路径与风险边界',
        ],
        'parameter': [
            '识别关键参数与敏感区间',
            '提出候选参数与边界',
            '定义验证优先级与停止标准',
        ],
        'factor': [
            '提出候选因子与研究假设',
            '说明经济逻辑与失效场景',
            '定义验证建议与淘汰条件',
        ],
        'backtest': [
            '执行可复现回测',
            '输出关键绩效与风险指标',
            '给出阈值判断依据',
        ],
        'data': [
            '完成数据快照与质量检查',
            '识别缺口与异常分布',
            '输出可追踪质量结论',
        ],
        'ops': [
            '检查系统运行状态',
            '识别 stale / lease / heartbeat 异常',
            '输出治理建议',
        ],
        'finance': [
            '提炼研究结论',
            '给出可落地启发',
            '指出后续验证方向',
        ],
        'sentiment': [
            '汇总主要情绪驱动',
            '识别风险催化因素',
            '输出结构化判断',
        ],
    }
    return defaults.get(intent, [f'完成 {role} 专项任务'])


def infer_constraints(intent: str, role: str, objective: str, risk_tags: list[str]) -> list[str]:
    lower = objective.lower()
    constraints: list[str] = []
    if intent in {'strategy', 'parameter', 'factor', 'backtest'}:
        constraints.append('必须避免未来函数与样本泄漏')
        constraints.append('必须显式提示过拟合风险')
    if 'code_change_risk' in risk_tags:
        constraints.append('必须保留可追踪改动与回滚线索')
    if 'config_change_risk' in risk_tags:
        constraints.append('配置变更不得直接视为正式生效结果')
    if 'manual_trade_risk' in risk_tags:
        constraints.append('涉及实盘/交易/参数生效必须人工确认')
    if intent == 'data':
        constraints.append('必须输出结构化快照与质量检查结果')
    if intent == 'ops':
        constraints.append('必须输出治理建议，不得静默跳过异常')
    if role in {'strategy-expert', 'parameter-evolver', 'factor-miner', 'sentiment-analyst', 'finance-learner'}:
        constraints.append('默认先输出结构化方案，不做高风险直接改动')
    if _contains_any(lower, ['formal', '正式', 'release', '上线', 'publish', 'deploy']):
        constraints.append('正式发布前必须经过人工审批点')
    return _dedupe(constraints)


def infer_acceptance_criteria(intent: str, role: str) -> list[str]:
    criteria = {
        'code': ['有真实改动证据', '有结构化结果摘要', '可交给 test-expert 验收'],
        'strategy': ['有结构化策略分析', '有推荐路径', '有验证方案'],
        'parameter': ['有参数候选与边界', '有优先级说明', '有验证建议'],
        'factor': ['有因子候选', '有经济逻辑说明', '有验证建议'],
        'backtest': ['有回测指标', '有回测报告', '可用于 stop criteria 判断'],
        'data': ['有数据快照', '有数据质量结论', '有结果摘要'],
        'ops': ['有健康结论', '有治理建议', '有结果摘要'],
        'finance': ['有研究结论', '有可落地启发', '有结果摘要'],
        'sentiment': ['有情绪结论', '有驱动说明', '有风险提示'],
    }
    return criteria.get(intent, [f'满足 {role} 的核心验收要求'])


def infer_stop_criteria_hints(intent: str, risk_tags: list[str]) -> list[str]:
    hints: list[str] = []
    if intent in {'strategy', 'parameter', 'factor', 'backtest'}:
        hints.extend(['收益/夏普/回撤阈值需明确', '连续无改善时应停止继续优化'])
    if intent == 'data':
        hints.extend(['数据质量未达标时停止下游优化', '关键字段缺失时停止推进'])
    if intent == 'ops':
        hints.extend(['发现阻断级异常时停止自动推进', '需人工介入的问题应显式升级'])
    if 'manual_trade_risk' in risk_tags or 'config_change_risk' in risk_tags:
        hints.append('人工审批前不得视为正式完成')
    return _dedupe(hints)


def infer_clarification_questions(objective: str, intent: str, risk_tags: list[str]) -> list[str]:
    questions: list[str] = []
    stripped = objective.strip()
    lower = stripped.lower()
    if len(stripped) < 12 or lower in GENERIC_OBJECTIVE_PHRASES or stripped in GENERIC_OBJECTIVE_PHRASES:
        questions.append('你更看重收益、回撤、稳健性还是执行速度？')
    if intent in {'strategy', 'parameter', 'factor', 'backtest'} and not _contains_any(lower, ['sharpe', 'drawdown', 'return', '收益', '回撤', '胜率', '交易次数']):
        questions.append('本次优化的核心指标是什么？例如收益、回撤、夏普、交易次数。')
    if intent == 'code' and not _contains_any(lower, ['.py', '.ts', '.md', 'file', '文件', '模块', 'script']):
        questions.append('需要聚焦哪个文件、模块或功能范围？')
    if 'manual_trade_risk' in risk_tags:
        questions.append('这次仅做研究/回测，还是会涉及实盘参数或交易动作？')
    return _dedupe(questions)


def infer_manual_review_required(objective: str, risk_tags: list[str], mode: str) -> bool:
    lower = objective.lower()
    high_risk_tags = {'code_change_risk', 'config_change_risk', 'manual_trade_risk'}
    if any(tag in high_risk_tags for tag in risk_tags):
        return True
    if mode == 'build':
        return True
    return _contains_any(lower, ['release', 'deploy', 'publish', 'restart', '正式', '上线', '实盘', '配置'])


def infer_risk_assessment(risk_tags: list[str], intent: str, mode: str) -> list[dict[str, str]]:
    priority_map = {
        'manual_trade_risk': ('critical', '涉及实盘/交易语义，必须人工确认后才能视为正式动作'),
        'config_change_risk': ('high', '配置/生效类变更容易影响真实运行环境，必须保留审批与回滚边界'),
        'code_change_risk': ('high', '代码改动需要最小变更、可追踪 diff 与后续验收'),
        'drawdown_risk': ('high', '需要优先关注风险暴露与回撤恶化可能'),
        'backtest_bias_risk': ('high', '回测结论可能受未来函数、样本泄漏或口径偏差影响'),
        'overfit_risk': ('medium', '优化/因子/参数任务需要防止样本内过拟合'),
        'data_quality_risk': ('medium', '数据质量缺口会污染后续判断与结果'),
    }
    items: list[dict[str, str]] = []
    for tag in risk_tags:
        priority, rationale = priority_map.get(tag, ('medium', '需要纳入结构化风险观察'))
        items.append({'tag': tag, 'priority': priority, 'rationale': rationale})
    if not items:
        baseline = 'high' if mode == 'build' else 'medium'
        items.append({'tag': 'baseline_execution_risk', 'priority': baseline, 'rationale': f'{intent} 任务仍需保留最小风险边界与验收口径'})
    priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    return sorted(items, key=lambda x: (priority_order.get(x['priority'], 9), x['tag']))


def infer_clarification_priority(questions: list[str], risk_tags: list[str], manual_review_required: bool) -> str:
    if not questions:
        return 'none'
    if manual_review_required or any(tag in {'manual_trade_risk', 'config_change_risk', 'code_change_risk'} for tag in risk_tags):
        return 'high'
    if len(questions) >= 2:
        return 'medium'
    return 'low'


def infer_execution_sequence(dependency_plan: dict[str, Any], manual_review_required: bool) -> list[str]:
    steps: list[str] = []
    kickoff = dependency_plan.get('kickoff_role')
    if kickoff:
        steps.append(f'kickoff:{kickoff}')
    for group in dependency_plan.get('parallel_groups', []) or []:
        cleaned = [str(item).strip() for item in group if str(item).strip()]
        if cleaned:
            steps.append('parallel:' + ','.join(cleaned))
    for role in dependency_plan.get('serial', []) or []:
        if role != kickoff:
            steps.append(f'serial:{role}')
    if manual_review_required:
        steps.append('checkpoint:manual-approval')
    return _dedupe(steps)


def infer_dependency_plan(intent: str, role: str, mode: str, manual_review_required: bool) -> dict[str, Any]:
    base_serial = [role]
    if role != 'test-expert':
        base_serial.append('test-expert')
    if role != 'doc-manager':
        base_serial.append('doc-manager')
    if role != 'knowledge-steward':
        base_serial.append('knowledge-steward')

    parallel_groups: list[list[str]] = []
    support_roles: list[str] = []
    if intent in {'strategy', 'parameter', 'factor'}:
        support_roles = ['backtest-engine']
    elif intent == 'code':
        support_roles = ['test-expert']
    elif intent == 'ops':
        support_roles = ['test-expert']

    if intent == 'strategy':
        parallel_groups = [['factor-miner', 'sentiment-analyst']]
    elif intent == 'parameter':
        parallel_groups = [['backtest-engine', 'factor-miner']]

    checkpoints = ['test-expert']
    if manual_review_required:
        checkpoints.append('manual-approval')

    return {
        'kickoff_role': role,
        'execution_mode': mode,
        'serial': _dedupe(base_serial),
        'parallel_groups': parallel_groups,
        'support_roles': _dedupe(support_roles),
        'review_checkpoints': _dedupe(checkpoints),
    }


def infer_objective_hierarchy(main_objective: str, sub_objectives: list[str], intent: str) -> list[dict[str, Any]]:
    hierarchy: list[dict[str, Any]] = [
        {'level': 'primary', 'objective': main_objective, 'intent': intent, 'success_signal': '主目标对应的核心问题得到结构化推进'},
    ]
    secondary_items = [item for item in sub_objectives if str(item).strip() and str(item).strip() != main_objective][:5]
    for idx, item in enumerate(secondary_items, 1):
        hierarchy.append({
            'level': 'secondary',
            'order': idx,
            'objective': item,
            'intent': intent,
            'success_signal': '子目标具备明确产物或验证结论',
        })
    hierarchy.append({
        'level': 'validation',
        'objective': '通过 test-expert / 文档沉淀链确认结果可交付',
        'intent': 'validation',
        'success_signal': '结果可验收、可追踪、可进入下游闭环',
    })
    return hierarchy


def infer_acceptance_contract(intent: str, acceptance_criteria: list[str], acceptance_hints: list[str], manual_review_required: bool) -> dict[str, Any]:
    focus_map = {
        'code': '真实改动 + 可验证证据 + 可回滚线索',
        'strategy': '结构化策略方案 + 验证路径 + 风险说明',
        'parameter': '参数候选边界 + 优先级 + 验证建议',
        'factor': '因子候选 + 经济逻辑 + 验证方向',
        'backtest': '关键绩效指标 + 风险指标 + stop criteria 可用性',
        'data': '快照 + 质量检查 + 可追踪结论',
        'ops': '健康结论 + 治理建议 + 阻断级异常识别',
        'finance': '研究结论 + 可落地启发 + 后续验证方向',
        'sentiment': '情绪结论 + 主要驱动 + 风险提示',
    }
    return {
        'validation_focus': focus_map.get(intent, '满足专项 worker 的核心产物要求'),
        'required_outcomes': _dedupe(list(acceptance_criteria) + list(acceptance_hints))[:8],
        'manual_gate_required': manual_review_required,
    }


def infer_stop_policy(intent: str, stop_criteria_hints: list[str], manual_review_required: bool) -> dict[str, Any]:
    stop_when = list(stop_criteria_hints)
    continue_when: list[str] = []
    escalate_when: list[str] = []
    if intent in {'strategy', 'parameter', 'factor', 'backtest'}:
        continue_when.extend(['关键指标仍有改善空间', '尚未触达停止标准且无阻断级风险'])
        escalate_when.extend(['发现未来函数/样本泄漏风险', '多轮优化无改善或风险显著上升'])
    elif intent in {'data', 'ops'}:
        continue_when.extend(['关键数据/运行状态已恢复到可接受区间'])
        escalate_when.extend(['存在阻断级异常或关键字段缺失'])
    else:
        continue_when.extend(['当前任务已形成可验证产物且无阻断级问题'])
        escalate_when.extend(['需要人工判断才能继续推进'])
    if manual_review_required:
        stop_when.append('人工审批前不得视为正式完成')
        escalate_when.append('涉及正式发布/配置/实盘语义时必须转人工确认')
    return {
        'stop_when': _dedupe(stop_when),
        'continue_when': _dedupe(continue_when),
        'escalate_when': _dedupe(escalate_when),
    }


def routing_decision(objective: str) -> dict[str, Any]:
    intent = intake_type(objective)
    role = route_worker_role(objective)
    mode = execution_mode(objective, role)
    risk_tags = infer_risk_tags(objective, role)
    manual_review_required = infer_manual_review_required(objective, risk_tags, mode)
    dependency_plan = infer_dependency_plan(intent, role, mode, manual_review_required)
    return {
        'intake_type': intent,
        'suggested_role': role,
        'execution_mode': mode,
        'risk_tags': risk_tags,
        'manual_review_required': manual_review_required,
        'dependency_plan': dependency_plan,
    }


def analyze_request(objective: str) -> dict[str, Any]:
    routing = routing_decision(objective)
    intent = routing['intake_type']
    role = routing['suggested_role']
    mode = routing['execution_mode']
    risk_tags = routing['risk_tags']
    manual_review_required = routing['manual_review_required']
    dependency_plan = routing['dependency_plan']
    main_objective = infer_main_objective(objective)
    sub_objectives = infer_sub_objectives(intent, role, objective)
    constraints = infer_constraints(intent, role, objective, risk_tags)
    acceptance_criteria = infer_acceptance_criteria(intent, role)
    acceptance_hints = infer_acceptance_hints(intent, role)
    stop_criteria_hints = infer_stop_criteria_hints(intent, risk_tags)
    clarification_questions = infer_clarification_questions(objective, intent, risk_tags)
    needs_clarification = bool(clarification_questions)
    risk_assessment = infer_risk_assessment(risk_tags, intent, mode)
    clarification_priority = infer_clarification_priority(clarification_questions, risk_tags, manual_review_required)
    execution_sequence = infer_execution_sequence(dependency_plan, manual_review_required)
    objective_hierarchy = infer_objective_hierarchy(main_objective, sub_objectives, intent)
    acceptance_contract = infer_acceptance_contract(intent, acceptance_criteria, acceptance_hints, manual_review_required)
    stop_policy = infer_stop_policy(intent, stop_criteria_hints, manual_review_required)
    recent_learning_context = infer_recent_learning_context(intent, role)
    recent_learning_guidance = infer_recent_learning_guidance(recent_learning_context, role)

    return {
        'analysis_version': 6,
        'objective_summary': main_objective,
        'main_objective': main_objective,
        'sub_objectives': sub_objectives,
        'objective_hierarchy': objective_hierarchy,
        'constraints': constraints,
        'acceptance_criteria': acceptance_criteria,
        'acceptance_contract': acceptance_contract,
        'stop_criteria_hints': stop_criteria_hints,
        'stop_policy': stop_policy,
        'clarification_questions': clarification_questions,
        'clarification_priority': clarification_priority,
        'needs_clarification': needs_clarification,
        'manual_review_required': manual_review_required,
        'intake_type': intent,
        'suggested_role': role,
        'execution_mode': mode,
        'risk_tags': risk_tags,
        'risk_assessment': risk_assessment,
        'acceptance_hints': acceptance_hints,
        'dependency_plan': dependency_plan,
        'execution_sequence': execution_sequence,
        'recent_learning_context': recent_learning_context,
        'recent_learning_guidance': recent_learning_guidance,
    }


def intake_decision(objective: str) -> dict[str, Any]:
    analysis = analyze_request(objective)
    return {
        'analysis_version': analysis['analysis_version'],
        'intake_type': analysis['intake_type'],
        'suggested_role': analysis['suggested_role'],
        'execution_mode': analysis['execution_mode'],
        'needs_clarification': analysis['needs_clarification'],
        'clarification_questions': analysis['clarification_questions'],
        'clarification_priority': analysis['clarification_priority'],
        'manual_review_required': analysis['manual_review_required'],
        'risk_tags': analysis['risk_tags'],
        'risk_assessment': analysis['risk_assessment'],
        'execution_sequence': analysis['execution_sequence'],
        'objective_hierarchy': analysis['objective_hierarchy'],
        'acceptance_contract': analysis['acceptance_contract'],
        'stop_policy': analysis['stop_policy'],
        'recent_learning_context': analysis['recent_learning_context'],
        'recent_learning_guidance': analysis['recent_learning_guidance'],
    }


def review_outcome(issues: list[str] | None = None, *, manual_review_required: bool = False, review_scope: str = 'technical_validation') -> dict[str, Any]:
    normalized_issues = [str(item).strip() for item in (issues or []) if str(item).strip()]
    if normalized_issues:
        return {
            'review_decision': 'rejected',
            'terminal_status': classify_terminal_status(review_decision='rejected'),
            'review_scope': review_scope,
            'reason': 'validation_issues_found',
            'issues': normalized_issues,
        }
    if manual_review_required:
        return {
            'review_decision': 'manual_review_required',
            'terminal_status': classify_terminal_status(review_decision='manual_review_required'),
            'review_scope': review_scope,
            'reason': 'human_approval_required_after_validation',
            'issues': [],
        }
    return {
        'review_decision': 'passed',
        'terminal_status': classify_terminal_status(review_decision='passed'),
        'review_scope': review_scope,
        'reason': 'validation_passed',
        'issues': [],
    }


def retry_policy(role: str, metadata: dict[str, Any], review: dict[str, Any], round_no: int) -> dict[str, Any]:
    if review.get('decision') == 'manual_review_required':
        return {
            'allow_retry': False,
            'reason': 'manual_review_required',
            'requested_reason': None,
        }
    allow = bool(metadata.get('auto_retry_allowed', False)) or role == 'coder'
    issues = review.get('issues', []) or []
    if not allow:
        return {
            'allow_retry': False,
            'reason': 'auto_retry_disabled',
            'requested_reason': None,
        }
    requested_reason = f"loop_retry_round_{round_no}: {', '.join(issues[:3]) or 'review rejected'}"
    return {
        'allow_retry': True,
        'reason': 'policy_allowed',
        'requested_reason': requested_reason,
    }


def classify_failed_checks(stop_eval: dict[str, Any]) -> set[str]:
    return {c['name'] for c in stop_eval.get('checks', []) if not c.get('passed')}


def _collect_research_hints(next_role: str, research_hints: dict[str, Any] | None = None) -> list[str]:
    if not research_hints:
        return []
    preferred_keys = {
        'strategy-expert': ['strategy_handoff', 'change_priority', 'code_touchpoints', 'validation_priority'],
        'parameter-evolver': ['parameter_handoff', 'change_priority', 'code_touchpoints', 'metric_guardrails', 'validation_priority'],
        'factor-miner': ['factor_handoff', 'validation_priority', 'applicability_conditions', 'code_touchpoints'],
    }
    hints: list[str] = []
    for key in preferred_keys.get(next_role, []):
        values = research_hints.get(key, [])
        if isinstance(values, list):
            for item in values:
                cleaned = str(item).strip()
                if cleaned and cleaned not in hints:
                    hints.append(cleaned)
                if len(hints) >= 2:
                    return hints
    return hints


def _preferred_role_from_hints(failed: set[str], adjust_round: int, research_hints: dict[str, Any] | None = None) -> tuple[str | None, str | None]:
    if not research_hints:
        return None, None
    if 'min_total_trades' in failed:
        if research_hints.get('strategy_handoff'):
            return 'strategy-expert', 'trade_count_shortfall_hint_strategy'
        if research_hints.get('parameter_handoff'):
            return 'parameter-evolver', 'trade_count_shortfall_hint_parameter'
    if 'min_total_return' in failed or 'min_sharpe_ratio' in failed:
        if research_hints.get('factor_handoff'):
            return 'factor-miner', 'weak_return_quality_hint_factor'
        if research_hints.get('strategy_handoff'):
            return 'strategy-expert', 'weak_return_quality_hint_strategy'
        if research_hints.get('parameter_handoff'):
            return 'parameter-evolver', 'weak_return_quality_hint_parameter'
    if 'max_drawdown' in failed:
        if research_hints.get('parameter_handoff'):
            return 'parameter-evolver', 'drawdown_control_hint_parameter'
        if research_hints.get('strategy_handoff'):
            return 'strategy-expert', 'drawdown_control_hint_strategy'
    return None, None


def _base_objective_for_role(next_role: str, failed: set[str], adjust_round: int) -> tuple[str, str]:
    if next_role == 'strategy-expert':
        if 'min_total_trades' in failed:
            return 'Increase trade opportunity density and broaden qualifying conditions.', 'trade_count_shortfall'
        if 'min_total_return' in failed or 'min_sharpe_ratio' in failed:
            if adjust_round == 1:
                return 'Revise strategy logic early to improve return quality before deeper downstream exploration.', 'weak_return_quality_strategy_reroute'
            return 'Revise strategy logic to improve edge quality after factor exploration.', 'weak_return_quality_followup'
        if 'max_drawdown' in failed:
            return 'Revise strategy logic to reduce drawdown pressure before parameter tightening.', 'drawdown_control_strategy_reroute'
        return 'Revise strategy logic for unresolved optimization failures.', 'default_strategy_reroute'
    if next_role == 'factor-miner':
        return 'Search for stronger predictive factor/filter combinations to improve return quality.', 'weak_return_quality_first_pass'
    if next_role == 'parameter-evolver':
        if 'max_drawdown' in failed:
            return 'Tighten risk control parameters and drawdown-related thresholds.', 'drawdown_control'
        if 'min_total_return' in failed or 'min_sharpe_ratio' in failed:
            return 'Tune parameter ranges to improve return quality without sacrificing core guardrails.', 'weak_return_quality_parameter_reroute'
        if 'min_total_trades' in failed:
            return 'Loosen or rebalance qualifying thresholds to restore viable trade opportunity density.', 'trade_count_parameter_reroute'
        return 'General robustness tuning for unresolved threshold failures.', 'default_parameter_tuning'
    return 'General robustness tuning for unresolved threshold failures.', 'default_parameter_tuning'


def _merge_objective_with_hints(base_objective: str, next_role: str, research_hints: dict[str, Any] | None = None) -> tuple[str, list[str], str | None]:
    hints = _collect_research_hints(next_role, research_hints)
    if not hints:
        return base_objective, [], None
    source_role = str((research_hints or {}).get('source_role') or '').strip() or None
    enriched = base_objective + ' Focus next on: ' + '; '.join(hints)
    return enriched, hints, source_role


def adaptive_next_step(stop_eval: dict[str, Any], adjust_round: int, research_hints: dict[str, Any] | None = None) -> dict[str, Any]:
    failed = classify_failed_checks(stop_eval)
    hinted_role, hinted_basis = _preferred_role_from_hints(failed, adjust_round, research_hints)

    if hinted_role:
        base_objective, default_basis = _base_objective_for_role(hinted_role, failed, adjust_round)
        objective, hints, source_role = _merge_objective_with_hints(base_objective, hinted_role, research_hints)
        return {
            'next_role': hinted_role,
            'objective': objective,
            'decision_basis': hinted_basis or default_basis,
            'handoff_hints_used': hints,
            'handoff_source_role': source_role,
        }

    if 'min_total_trades' in failed:
        base_objective, default_basis = _base_objective_for_role('strategy-expert', failed, adjust_round)
        objective, hints, source_role = _merge_objective_with_hints(base_objective, 'strategy-expert', research_hints)
        return {
            'next_role': 'strategy-expert',
            'objective': objective,
            'decision_basis': default_basis,
            'handoff_hints_used': hints,
            'handoff_source_role': source_role,
        }
    if 'min_total_return' in failed or 'min_sharpe_ratio' in failed:
        default_role = 'factor-miner' if adjust_round == 1 else 'strategy-expert'
        base_objective, default_basis = _base_objective_for_role(default_role, failed, adjust_round)
        objective, hints, source_role = _merge_objective_with_hints(base_objective, default_role, research_hints)
        return {
            'next_role': default_role,
            'objective': objective,
            'decision_basis': default_basis,
            'handoff_hints_used': hints,
            'handoff_source_role': source_role,
        }
    if 'max_drawdown' in failed:
        base_objective, default_basis = _base_objective_for_role('parameter-evolver', failed, adjust_round)
        objective, hints, source_role = _merge_objective_with_hints(base_objective, 'parameter-evolver', research_hints)
        return {
            'next_role': 'parameter-evolver',
            'objective': objective,
            'decision_basis': default_basis,
            'handoff_hints_used': hints,
            'handoff_source_role': source_role,
        }
    base_objective, default_basis = _base_objective_for_role('parameter-evolver', failed, adjust_round)
    objective, hints, source_role = _merge_objective_with_hints(base_objective, 'parameter-evolver', research_hints)
    return {
        'next_role': 'parameter-evolver',
        'objective': objective,
        'decision_basis': default_basis,
        'handoff_hints_used': hints,
        'handoff_source_role': source_role,
    }


def stop_decision(stop_eval: dict[str, Any], adjust_round: int, max_adjust_rounds: int, research_hints: dict[str, Any] | None = None) -> dict[str, Any]:
    if stop_eval.get('passed'):
        return {
            'action': 'stop_passed',
            'reason': 'stop_criteria_satisfied',
            'terminal_status': classify_terminal_status(stop_eval=stop_eval),
        }
    if adjust_round >= max_adjust_rounds:
        return {
            'action': 'stop_threshold_not_met',
            'reason': 'max_adjust_rounds_exhausted',
            'terminal_status': classify_terminal_status(stop_eval=stop_eval, round_exhausted=True),
        }
    step = adaptive_next_step(stop_eval, adjust_round, research_hints=research_hints)
    return {
        'action': 'continue_with_adaptive_step',
        'reason': step['decision_basis'],
        'terminal_status': classify_terminal_status(stop_eval=stop_eval),
        **step,
    }


def governance_action_for_item(item: dict[str, Any]) -> dict[str, Any] | None:
    if not item.get('stale'):
        return None
    task_id = item.get('task_id', '<unknown-task>')
    allow = bool(item.get('auto_retry_allowed', False))
    if allow:
        return {
            'task_id': task_id,
            'role': item.get('role'),
            'status': item.get('status'),
            'recommended_action': 'auto_retry',
            'rationale': 'task is stale and metadata allows automatic retry',
            'reason': item.get('reason'),
        }
    return {
        'task_id': task_id,
        'role': item.get('role'),
        'status': item.get('status'),
        'recommended_action': 'manual_review',
        'rationale': 'task is stale but auto-retry is disabled for this role/task type',
        'reason': item.get('reason'),
    }


def governance_recommendations(items: list[dict[str, Any]]) -> dict[str, Any]:
    actions = []
    for item in items:
        action = governance_action_for_item(item)
        if action:
            actions.append(action)
    return {
        'action_count': len(actions),
        'actions': actions,
    }
