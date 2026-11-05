"""neo 的命令行入口。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from . import __version__
from .rules import ERROR, RULES, WARN, Finding, check_text
from .scaffold import render

MARK_OK = "ok  "
MARK_BAD = "FAIL"


def collect(paths: Sequence[str]) -> List[Path]:
    files: List[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            files.extend(sorted(p for p in path.rglob("*.md") if ".git" not in p.parts))
        elif path.is_file():
            files.append(path)
        else:
            raise SystemExit(f"找不到：{raw}")
    unique: List[Path] = []
    for item in files:
        if item not in unique:
            unique.append(item)
    return unique


def run_check(paths: Sequence[str], strict: bool, as_json: bool) -> int:
    files = collect(paths)
    if not files:
        raise SystemExit("没有找到 .md 文件")

    results: List[Tuple[Path, List[Finding]]] = []
    errors = 0
    warnings = 0
    failed = 0
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            results.append((path, [Finding("N001", ERROR, "不是 UTF-8 文本")]))
            errors += 1
            failed += 1
            continue
        findings = check_text(text)
        results.append((path, findings))
        errors += sum(1 for item in findings if item.level == ERROR)
        warnings += sum(1 for item in findings if item.level == WARN)
        if any(item.level == ERROR for item in findings):
            failed += 1

    if as_json:
        print(json.dumps(
            [{"path": str(path), "findings": [item.as_dict() for item in findings]} for path, findings in results],
            ensure_ascii=False,
            indent=2,
        ))
    else:
        for path, findings in results:
            if not findings:
                print(f"{MARK_OK} {path}")
                continue
            print(f"{MARK_BAD} {path}")
            for item in findings:
                print(f"     {item.code}  {item.level:<5}  {item.message}")
        print()
        print(f"{len(files)} 个文件 · {failed} 个没通过 · {errors} 个错误 · {warnings} 个提醒")

    if errors:
        return 1
    if strict and warnings:
        return 1
    return 0


def run_new(args: argparse.Namespace) -> int:
    text = render(
        slug=args.slug,
        name=args.name,
        job=args.job,
        cron=args.cron,
        timezone=args.timezone,
        author=args.author,
    )
    target = Path(args.out) / f"{args.slug}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    print(f"写好了 {target}")
    findings = check_text(text)
    if findings:
        print("但它没通过检查（这不该发生，请报 issue）：")
        for item in findings:
            print(f"  {item.code}  {item.message}")
        return 1
    print("过了检查。下一步：把「绝不」改成你真正怕它做的事。")
    return 0


def run_rules() -> int:
    groups = (
        ("N", "格式：和 OpenMausBot 的解析器对齐，错了导不进去"),
        ("D", "设计：导得进去，但用起来会坏"),
    )
    for prefix, title in groups:
        print(title)
        for code, level, message in RULES:
            if code.startswith(prefix):
                print(f"  {code}  {level:<5}  {message}")
        print()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="neo", description="给 OpenMausBot 的 bot 文件做体检")
    parser.add_argument("--version", action="version", version=f"neo {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="检查 bot 文件或目录")
    check.add_argument("paths", nargs="+")
    check.add_argument("--strict", action="store_true", help="把提醒也当成失败")
    check.add_argument("--json", action="store_true", help="输出 JSON")

    new = sub.add_parser("new", help="生成一个能通过检查的 bot 文件")
    new.add_argument("slug")
    new.add_argument("--name", required=True, help="bot 的名字")
    new.add_argument("--job", required=True, help="它唯一的那件事，一句话")
    new.add_argument("--cron", help='例： "30 8 * * 1-5"')
    new.add_argument("--timezone", default="Asia/Shanghai")
    new.add_argument("--author", default="Neo")
    new.add_argument("--out", default=".")

    sub.add_parser("rules", help="列出全部规则")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "check":
        return run_check(args.paths, args.strict, args.json)
    if args.command == "new":
        try:
            return run_new(args)
        except ValueError as exc:
            print(f"neo new: {exc}", file=sys.stderr)
            return 2
    return run_rules()
