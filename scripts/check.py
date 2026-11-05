#!/usr/bin/env python3
"""Check botmrr: 1 bot files against the OpenMausBot package rules they must satisfy.

Structural check only: it mirrors the documented schema, it does not import into
the app. Usage: python3 scripts/check.py bots/*.md
"""
import re
import sys

import yaml

COLORS = {"green", "blue", "red", "orange", "purple", "cyan", "pink",
          "yellow", "teal", "coral", "silver", "chrome"}
HEADINGS = ["Activation", "Mission", "Outcomes", "Connections",
            "Team", "Chief of Staff", "Completion rule"]
KEY = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
CRON = re.compile(r"^\S+ \S+ \S+ \S+ \S+$")


def check(path):
    errors = []
    text = open(path, encoding="utf-8").read()

    m = re.match(r"^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)", text)
    if not m:
        return ["缺少 YAML frontmatter"]
    meta = yaml.safe_load(m.group(1))
    if not isinstance(meta, dict):
        return ["frontmatter 不是对象"]
    if meta.get("botmrr") != 1:
        errors.append("botmrr 必须是 1")

    def need(key):
        value = meta.get(key)
        if value in (None, ""):
            errors.append(f"缺少 {key}")
        return value

    ident = need("id")
    if isinstance(ident, str) and not SLUG.match(ident):
        errors.append(f"id 不是合法 slug: {ident}")
    release = need("release")
    if isinstance(release, str) and not SEMVER.match(release):
        errors.append(f"release 不是语义化版本: {release}")

    limits = {"name": 100, "tagline": 160, "summary": 2000, "category": 80}
    for field, cap in limits.items():
        value = need(field)
        if isinstance(value, str) and len(value) > cap:
            errors.append(f"{field} 超过 {cap} 字符")
    need("license")

    author = meta.get("author")
    if not isinstance(author, dict) or not author.get("name"):
        errors.append("author.name 缺失")

    outcomes = meta.get("outcomes")
    if not isinstance(outcomes, list) or not 1 <= len(outcomes) <= 12:
        errors.append("outcomes 需要 1 到 12 条")
    elif any(not isinstance(item, str) or len(item) > 240 for item in outcomes):
        errors.append("outcomes 每条必须是 240 字符以内的文本")

    minutes = meta.get("setupMinutes")
    if not isinstance(minutes, int) or not 1 <= minutes <= 240:
        errors.append("setupMinutes 需要 1 到 240 的整数")

    req = meta.get("requirements")
    if not isinstance(req, dict) or "capabilities" not in req or "apps" not in req:
        errors.append("requirements 需要 apps 和 capabilities")

    agents = meta.get("agents")
    keys = set()
    if not isinstance(agents, list) or not agents:
        errors.append("至少需要一个 agent")
    else:
        for agent in agents:
            key = agent.get("key")
            if not isinstance(key, str) or not KEY.match(key):
                errors.append(f"agent key 不合法: {key}")
                continue
            keys.add(key)
            if not agent.get("name"):
                errors.append(f"agent {key} 缺少 name")
            soul = agent.get("soul") or ""
            if len(soul.encode("utf-8")) > 24000:
                errors.append(f"agent {key} 的 soul 超过 24000 字节")
            if "绝不" not in soul:
                errors.append(f"agent {key} 的 soul 没有 anti-jobs 段落")
            look = agent.get("appearance")
            if not isinstance(look, dict):
                errors.append(f"agent {key} 缺少 appearance")
            elif look.get("color") not in COLORS:
                errors.append(f"agent {key} 的 color 不在允许列表: {look.get('color')}")

    routines = meta.get("routines") or []
    for routine in routines:
        key = routine.get("key")
        if not isinstance(key, str) or not KEY.match(key):
            errors.append(f"routine key 不合法: {key}")
        if routine.get("agent") not in keys:
            errors.append(f"routine {key} 指向不存在的 agent")
        if routine.get("runOn") not in ("maus", "cloud"):
            errors.append(f"routine {key} 的 runOn 必须是 maus 或 cloud")
        schedule = routine.get("schedule") or {}
        if schedule.get("type") == "cron":
            if not CRON.match(str(schedule.get("expression", ""))):
                errors.append(f"routine {key} 的 cron 需要五个字段")
            if not schedule.get("timeZone"):
                errors.append(f"routine {key} 缺少 timeZone")
        else:
            errors.append(f"routine {key} 的 schedule 只检查了 cron")
        duration = routine.get("durationMinutes")
        if not isinstance(duration, int) or not 5 <= duration <= 240:
            errors.append(f"routine {key} 的 durationMinutes 需要 5 到 240")
        if routine.get("enabledAfterInstall") is not False:
            errors.append(f"routine {key} 安装后必须是暂停的")

    body = text[m.end():]
    for heading in HEADINGS:
        if f"## {heading}" not in body:
            errors.append(f"正文缺少 ## {heading}")

    return errors


def main(paths):
    bad = 0
    for path in paths:
        errors = check(path)
        if errors:
            bad += 1
            print(f"FAIL {path}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"ok   {path}")
    print(f"\n{len(paths) - bad}/{len(paths)} 通过")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["bots/repo-scout.md"]))
