#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any

from artifact_manager import ArtifactManager


class OpenCodeResultNormalizer:
    def __init__(self, task_dir: str):
        self.artifacts = ArtifactManager(task_dir)

    def write(self, request: dict[str, Any], result: dict[str, Any]) -> list[str]:
        self.artifacts.write_json('engine_request.json', request)
        self.artifacts.write_json(
            'opencode_result.json',
            {
                'returncode': result['returncode'],
                'timed_out': result['timed_out'],
                'mode': result['mode'],
                'agent': result['agent'],
                'model': result['model'],
                'repo_root': result.get('repo_root'),
                'code_root': result['code_root'],
                'worktree_path': result.get('worktree_path'),
                'changed_paths': result['changed_paths'],
                'raw_line_count': result['raw_line_count'],
                'stderr_tail': result['stderr'][-2000:],
            },
        )
        self.artifacts.write_text('opencode_result.md', result['text'] or '')
        diff_text = result['diff_text'] or ('# no repo diff captured\n' if result['mode'] == 'plan' else '# build mode produced no captured diff\n')
        self.artifacts.write_text('diff.patch', diff_text)
        self.artifacts.write_json('changed_files.json', {'changed_files': result['changed_paths']})
        summary = result['text'] or 'OpenCode completed without textual summary.'
        self.artifacts.write_text('result_summary.md', summary + '\n')
        if result.get('worktree_path'):
            self.artifacts.write_text('worktree_path.txt', result['worktree_path'] + '\n')
        self.artifacts.append_log('run.log', f"returncode={result['returncode']} timed_out={result['timed_out']} mode={result['mode']}")
        if result['stderr']:
            self.artifacts.append_log('run.log', result['stderr'][-2000:])
        return self.artifacts.list_artifacts()
