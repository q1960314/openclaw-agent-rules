#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations


def decide_fallback(result: dict) -> dict:
    if result.get('returncode') == 0 and not result.get('timed_out'):
        return {'action': 'accept', 'reason': 'opencode completed successfully'}
    if result.get('timed_out'):
        return {'action': 'fail', 'reason': 'opencode timed out'}
    return {'action': 'fail', 'reason': f"opencode exited with code {result.get('returncode')}"}
