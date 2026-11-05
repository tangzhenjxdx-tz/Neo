"""neo new：生成一个立刻能通过检查的 botmrr:1 文件。"""
from __future__ import annotations

import json
import re
from typing import List, Optional

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
CRON_RE = re.compile(r"^\S+ \S+ \S+ \S+ \S+$")


def _q(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render(
    slug: str,
    name: str,
    job: str,
    cron: Optional[str] = None,
    timezone: str = "Asia/Shanghai",
    author: str = "Neo",
    color: str = "teal",
) -> str:
    if not SLUG_RE.match(slug):
        raise ValueError(f"slug 只能用小写字母、数字和 -：{slug}")
    if cron is not None and not CRON_RE.match(cron):
        raise ValueError(f"cron 要五个字段（分 时 日 月 周）：{cron}")

    lines: List[str] = [
        "---",
        "botmrr: 1",
        f"id: {_q(slug)}",
        'release: "0.1.0"',
        f"name: {_q(name)}",
        f"tagline: {_q(job)}",
        f"summary: {_q(job + '只做这一件事，做完就停。')}",
        'category: "custom"',
        "author:",
        f"  name: {_q(author)}",
        'license: "Apache-2.0"',
        "outcomes:",
        f"  - {_q(job)}",
        "setupMinutes: 5",
        "requirements:",
        "  apps: []",
        "  capabilities: []",
        "agents:",
        "  - key: main",
        f"    name: {_q(name)}",
        f"    description: {_q(job)}",
        "    appearance:",
        f"      color: {color}",
        "    soul: |",
    ]

    soul = [
        "## 工作",
        job,
        "",
        "## 绝不",
        "- 不接第二件事：超出上面这一句的请求，直接回「不在范围内」。",
        "- 不替你做决定，只摆事实和选项。",
        "",
        "## 声音",
        "简短、直接、不客套。",
        "示例：「三条，按重要性排。」",
        "",
        "## 完成标准",
        "一条消息，不超过 5 行；没有内容时只回一句「今天没有」。发完就停。",
    ]
    lines.extend("      " + line if line else "" for line in soul)

    if cron is not None:
        lines.extend([
            "routines:",
            "  - key: main",
            f"    name: {_q(name)}",
            "    agent: main",
            "    prompt: |",
            f"      {job}",
            "      只做这一件事；做完发一条消息，没有内容就只回一句「今天没有」。",
            "    runOn: maus",
            "    schedule:",
            "      type: cron",
            f"      expression: {_q(cron)}",
            f"      timeZone: {_q(timezone)}",
            "    durationMinutes: 15",
            "    enabledAfterInstall: false",
        ])

    lines.extend([
        "---",
        "",
        f"# {name}",
        "",
        job,
        "",
        "## Activation",
        "",
        "先确认用户要的就是这一件事；不是，就别装。",
        "",
        "## Mission",
        "",
        job,
        "",
        "## Outcomes",
        "",
        f"- {job}",
        "",
        "## Connections",
        "",
        "没有需要的就写「无」。需要什么就写什么，别多要。",
        "",
        "## Team",
        "",
        "单兵。",
        "",
        "## Chief of Staff",
        "",
        "不需要。",
        "",
        "## Completion rule",
        "",
        "发出那一条消息就结束；任何写操作都算越界。",
        "",
    ])
    return "\n".join(lines)
