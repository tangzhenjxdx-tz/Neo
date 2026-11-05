"""Neo 的检查规则。

两条线：

  N-xx  格式。照着 OpenMausBot 的 botmrr:1 解析器核，错了导入会直接失败。
  D-xx  设计。导入能成功，但用起来会坏：没有 anti-jobs、没有 done-test、权限给多了。

格式规则的事实依据是 OpenMausBot 仓库里的 shared/package-format.ts（Apache-2.0）：
顶层字段就是 package 的字段，正文必须有七个固定小节。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import yaml

ERROR = "error"
WARN = "warn"

# shared/wire.ts 里的 MAUS_COLOR_NAMES
COLORS = {
    "green", "blue", "red", "orange", "purple", "cyan", "pink",
    "yellow", "teal", "coral", "silver", "chrome",
}

PACKAGE_HEADINGS = [
    "Activation", "Mission", "Outcomes", "Connections",
    "Team", "Chief of Staff", "Completion rule",
]

LIMITS = {"name": 100, "tagline": 160, "summary": 2000, "category": 80, "license": 80}

FRONT_RE = re.compile(r"^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)")
HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
KEY_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
SEMVER_RE = re.compile(r"^(0|[1-9]\d{0,5})\.(0|[1-9]\d{0,5})\.(0|[1-9]\d{0,5})$")
CRON_RE = re.compile(r"^\S+ \S+ \S+ \S+ \S+$")
CLOCK_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

# 设计规则用的词表：出现这些动词，说明它真的会动手。
WRITE_VERBS = (
    "回复", "评论", "打标签", "改标签", "关闭", "删除", "修改", "写入",
    "创建", "合并", "推送", "发送", "发信", "发布", "发帖", "指派", "编辑",
)
NEGATIONS = ("不", "别", "勿", "禁止", "无需", "不用", "绝不", "没有", "未")
READ_ONLY_MARKERS = ("只读", "不写", "不改", "只报")
VAGUE_WORDS = ("适当", "尽量", "合适", "看情况", "差不多", "酌情", "根据需要", "视情况")


@dataclass
class Finding:
    code: str
    level: str
    message: str

    def as_dict(self) -> Dict[str, str]:
        return {"code": self.code, "level": self.level, "message": self.message}


RULES: Tuple[Tuple[str, str, str], ...] = (
    ("N001", ERROR, "文件开头必须是 --- 包住的 YAML frontmatter"),
    ("N002", ERROR, "frontmatter 必须是合法 YAML"),
    ("N003", ERROR, "botmrr 必须是 1"),
    ("N004", ERROR, "缺少必填字段"),
    ("N005", ERROR, "id 必须是小写 slug"),
    ("N006", ERROR, "release 必须是 1.2.3 这样的版本号"),
    ("N007", ERROR, "文本字段超过长度上限"),
    ("N008", ERROR, "author.name 缺失"),
    ("N009", ERROR, "outcomes 要 1 到 12 条、每条 240 字以内"),
    ("N010", ERROR, "setupMinutes 要是 1 到 240 的整数"),
    ("N011", ERROR, "requirements 需要 apps 和 capabilities 两个列表"),
    ("N012", ERROR, "至少要有一个 agent"),
    ("N013", ERROR, "agent 字段不合法（key、name、颜色、大小）"),
    ("N014", ERROR, "soul 超过 24000 字节"),
    ("N015", ERROR, "routine 不合法（归属、schedule、时长、初始暂停）"),
    ("N016", ERROR, "正文缺少七个小节之一"),
    ("D001", ERROR, "soul 里没有「工作」一节"),
    ("D002", ERROR, "soul 里没有「绝不」一节"),
    ("D003", ERROR, "「绝不」少于两条"),
    ("D004", ERROR, "soul 里没有「完成标准」一节"),
    ("D005", ERROR, "完成标准里有含糊词，无法核对"),
    ("D006", ERROR, "自称只读，却申请了写权限"),
    ("D007", ERROR, "routine 让它做 soul 明令禁止的写操作"),
    ("D008", WARN, "一个 bot 挂了三条以上的例行任务"),
    ("D009", WARN, "soul 里没有「声音」一节"),
    ("D010", WARN, "所有 agent 都没写 soul，只剩一句 description"),
)


def utf8_len(text: str) -> int:
    return len(text.encode("utf-8"))


def sections(text: str) -> Dict[str, str]:
    """按二级标题切段，返回 {标题: 正文}。"""
    found: Dict[str, str] = {}
    matches = list(HEADING_RE.finditer(text))
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        found[match.group(1).strip()] = text[start:end].strip()
    return found


def bullets(text: str) -> List[str]:
    return [line.strip() for line in text.splitlines() if re.match(r"^\s*(?:[-*]|\d+\.)\s+\S", line)]


LEAD_RE = re.compile(r"^\s*(?:[-*]|[0-9]+[.)、])\s*")
SOFT_PREFIXES = ("直接", "再", "然后", "并", "都", "必须", "请", "记得")


def imperative_hits(text: str, verbs: Sequence[str]) -> List[str]:
    """找出以动作开头的指令行。

    只看句式：描述「别人回复的 PR」不算，写「回复每一条」才算。
    以「不」「别」开头的行整行跳过。
    """
    hits: List[str] = []
    for raw in text.splitlines():
        line = LEAD_RE.sub("", raw).strip()
        if not line:
            continue
        for prefix in SOFT_PREFIXES:
            if line.startswith(prefix):
                line = line[len(prefix):].strip()
        if any(line.startswith(negation) for negation in NEGATIONS):
            continue
        for verb in verbs:
            if line.startswith(verb):
                hits.append(verb)
                break
    return sorted(set(hits))


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _required(meta: Dict[str, Any], field: str, out: List[Finding]) -> Any:
    value = meta.get(field)
    if value is None or (isinstance(value, str) and not value.strip()):
        out.append(Finding("N004", ERROR, f"缺少 {field}"))
        return None
    return value


def check_text(text: str) -> List[Finding]:
    out: List[Finding] = []

    front = FRONT_RE.match(text)
    if not front:
        return [Finding("N001", ERROR, "没有 YAML frontmatter：文件必须以 --- 开头，再以 --- 结束配置")]

    try:
        meta = yaml.safe_load(front.group(1))
    except yaml.YAMLError as exc:
        return [Finding("N002", ERROR, f"frontmatter 不是合法 YAML：{exc}".replace("\n", " "))]
    if not isinstance(meta, dict):
        return [Finding("N002", ERROR, "frontmatter 必须是一个对象，不是列表或纯文本")]

    if meta.get("botmrr") != 1:
        out.append(Finding("N003", ERROR, f"botmrr 是 {meta.get('botmrr')!r}，必须是 1"))

    for field in ("id", "release", "name", "tagline", "summary", "category", "license"):
        _required(meta, field, out)

    identifier = meta.get("id")
    if isinstance(identifier, str) and identifier and not SLUG_RE.match(identifier):
        out.append(Finding("N005", ERROR, f"id 只能用小写字母、数字和 -：{identifier}"))

    release = meta.get("release")
    if release is not None and not SEMVER_RE.match(str(release)):
        out.append(Finding("N006", ERROR, f"release 要写成 1.2.3：{release}"))

    for field, cap in LIMITS.items():
        value = meta.get(field)
        if isinstance(value, str) and len(value) > cap:
            out.append(Finding("N007", ERROR, f"{field} 有 {len(value)} 字，上限 {cap}"))

    author = meta.get("author")
    if not isinstance(author, dict) or not _text(author.get("name")):
        out.append(Finding("N008", ERROR, "author.name 缺失，导入方要知道是谁写的"))

    outcomes = meta.get("outcomes")
    if not isinstance(outcomes, list) or not 1 <= len(outcomes) <= 12:
        out.append(Finding("N009", ERROR, "outcomes 要 1 到 12 条"))
    else:
        for item in outcomes:
            if not isinstance(item, str) or not item.strip() or len(item) > 240:
                out.append(Finding("N009", ERROR, "outcomes 每条要是 1 到 240 字的文本"))
                break

    minutes = meta.get("setupMinutes")
    if not isinstance(minutes, int) or isinstance(minutes, bool) or not 1 <= minutes <= 240:
        out.append(Finding("N010", ERROR, f"setupMinutes 要是 1 到 240 的整数，现在是 {minutes!r}"))

    requirements = meta.get("requirements")
    if not isinstance(requirements, dict) or not isinstance(requirements.get("apps"), list) or not isinstance(requirements.get("capabilities"), list):
        out.append(Finding("N011", ERROR, "requirements 需要 apps 和 capabilities，没有就写空列表 []"))
    else:
        if len(requirements["apps"]) > 30:
            out.append(Finding("N011", ERROR, "requirements.apps 最多 30 个"))
        if len(requirements["capabilities"]) > 20:
            out.append(Finding("N011", ERROR, "requirements.capabilities 最多 20 条"))

    agents = meta.get("agents")
    agent_keys: List[str] = []
    if not isinstance(agents, list) or not agents:
        out.append(Finding("N012", ERROR, "至少需要一个 agent"))
        agents = []
    else:
        for agent in agents:
            if not isinstance(agent, dict):
                out.append(Finding("N013", ERROR, "agents 里每一项都必须是对象"))
                continue
            key = agent.get("key")
            if not isinstance(key, str) or not KEY_RE.match(key):
                out.append(Finding("N013", ERROR, f"agent key 只能用小写字母、数字、- 和 _：{key!r}"))
                continue
            agent_keys.append(key)
            if not _text(agent.get("name")):
                out.append(Finding("N013", ERROR, f"agent {key} 缺少 name"))
            description = agent.get("description")
            if description is not None and (not isinstance(description, str) or len(description) > 4000):
                out.append(Finding("N013", ERROR, f"agent {key} 的 description 超过 4000 字"))
            soul = agent.get("soul")
            if soul is not None:
                if not isinstance(soul, str):
                    out.append(Finding("N013", ERROR, f"agent {key} 的 soul 必须是文本"))
                elif utf8_len(soul) > 24000:
                    out.append(Finding("N014", ERROR, f"agent {key} 的 soul 有 {utf8_len(soul)} 字节，上限 24000"))
            look = agent.get("appearance")
            if not isinstance(look, dict):
                out.append(Finding("N013", ERROR, f"agent {key} 缺少 appearance"))
            else:
                color = look.get("color")
                if color not in COLORS:
                    out.append(Finding("N013", ERROR, f"agent {key} 的 color 不在允许列表里：{color!r}"))
                body = look.get("mascotBody")
                if body is not None and (not isinstance(body, str) or len(body) > 40):
                    out.append(Finding("N013", ERROR, f"agent {key} 的 mascotBody 超过 40 字"))

    routines = meta.get("routines") or []
    if not isinstance(routines, list):
        out.append(Finding("N015", ERROR, "routines 必须是列表"))
        routines = []
    for routine in routines:
        if not isinstance(routine, dict):
            out.append(Finding("N015", ERROR, "routines 里每一项都必须是对象"))
            continue
        key = routine.get("key")
        if not isinstance(key, str) or not KEY_RE.match(key):
            out.append(Finding("N015", ERROR, f"routine key 不合法：{key!r}"))
        name = routine.get("name")
        if not isinstance(name, str) or not name.strip() or len(name) > 80:
            out.append(Finding("N015", ERROR, f"routine {key} 的 name 要 1 到 80 字"))
        if routine.get("agent") not in agent_keys:
            out.append(Finding("N015", ERROR, f"routine {key} 指向不存在的 agent：{routine.get('agent')!r}"))
        prompt = routine.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            out.append(Finding("N015", ERROR, f"routine {key} 缺少 prompt"))
        elif len(prompt) > 20000:
            out.append(Finding("N015", ERROR, f"routine {key} 的 prompt 超过 20000 字"))
        if routine.get("runOn") not in ("maus", "cloud"):
            out.append(Finding("N015", ERROR, f"routine {key} 的 runOn 必须是 maus 或 cloud"))
        schedule = routine.get("schedule")
        out.extend(_schedule_findings(key, schedule))
        duration = routine.get("durationMinutes")
        if not isinstance(duration, int) or isinstance(duration, bool) or not 5 <= duration <= 240:
            out.append(Finding("N015", ERROR, f"routine {key} 的 durationMinutes 要是 5 到 240 的整数"))
        if routine.get("enabledAfterInstall") is not False:
            out.append(Finding("N015", ERROR, f"routine {key} 装完必须先是暂停的：enabledAfterInstall: false"))

    for heading in PACKAGE_HEADINGS:
        if f"## {heading}" not in text:
            out.append(Finding("N016", ERROR, f"正文缺少 ## {heading}"))

    out.extend(_design_findings(agents, routines, meta))
    return out


def _schedule_findings(key: Any, schedule: Any) -> List[Finding]:
    out: List[Finding] = []
    if not isinstance(schedule, dict):
        return [Finding("N015", ERROR, f"routine {key} 缺少 schedule")]
    kind = schedule.get("type")
    if kind == "cron":
        if not CRON_RE.match(str(schedule.get("expression", ""))):
            out.append(Finding("N015", ERROR, f"routine {key} 的 cron 要五个字段"))
        if not _text(schedule.get("timeZone")):
            out.append(Finding("N015", ERROR, f"routine {key} 的 cron 缺少 timeZone"))
    elif kind == "daily":
        if not CLOCK_RE.match(str(schedule.get("time", ""))):
            out.append(Finding("N015", ERROR, f"routine {key} 的 time 要写成 HH:MM"))
        weekdays = schedule.get("weekdays")
        if not isinstance(weekdays, list) or not 1 <= len(weekdays) <= 7 or any(
            not isinstance(day, int) or isinstance(day, bool) or not 0 <= day <= 6 for day in weekdays
        ):
            out.append(Finding("N015", ERROR, f"routine {key} 的 weekdays 要是 0 到 6 的数字，0 是周日"))
    elif kind == "interval":
        every = schedule.get("everyMinutes")
        if not isinstance(every, int) or isinstance(every, bool) or not 5 <= every <= 1440:
            out.append(Finding("N015", ERROR, f"routine {key} 的 everyMinutes 要是 5 到 1440"))
        anchor = schedule.get("anchorAt")
        if not isinstance(anchor, int) or isinstance(anchor, bool):
            out.append(Finding("N015", ERROR, f"routine {key} 的 interval 缺少 anchorAt（毫秒时间戳）"))
    elif kind == "once":
        if not isinstance(schedule.get("at"), int) or isinstance(schedule.get("at"), bool):
            out.append(Finding("N015", ERROR, f"routine {key} 的 once 缺少 at（毫秒时间戳）"))
    else:
        out.append(Finding("N015", ERROR, f"routine {key} 的 schedule.type 只能是 cron、daily、interval、once"))
    return out


def _design_findings(agents: List[Any], routines: List[Any], meta: Dict[str, Any]) -> List[Finding]:
    out: List[Finding] = []
    if not any(isinstance(agent, dict) and _text(agent.get("soul")) for agent in agents):
        out.append(Finding("D010", WARN, "没有任何 agent 写 soul，它只剩一句 description 可用"))
        return out

    souls: Dict[str, str] = {}
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        soul = _text(agent.get("soul"))
        if not soul:
            continue
        key = str(agent.get("key"))
        souls[key] = soul
        parts = sections(soul)

        if "工作" not in parts:
            out.append(Finding("D001", ERROR, f"agent {key}：没有「## 工作」，没人知道它到底干什么"))
        if "绝不" not in parts:
            out.append(Finding("D002", ERROR, f"agent {key}：没有「## 绝不」，边界是空的"))
        else:
            lines = bullets(parts["绝不"])
            if len(lines) < 2:
                out.append(Finding("D003", ERROR, f"agent {key}：「绝不」只有 {len(lines)} 条，至少两条"))
        if "声音" not in parts:
            out.append(Finding("D009", WARN, f"agent {key}：没有「## 声音」，它说话会像谁都不像"))

        done = parts.get("完成标准")
        if done is None:
            out.append(Finding("D004", ERROR, f"agent {key}：没有「## 完成标准」，不知道什么算完"))
        else:
            vague = [word for word in VAGUE_WORDS if word in done]
            if vague:
                out.append(Finding("D005", ERROR, f"agent {key}：完成标准里有「{'、'.join(vague)}」，没法核对"))

        read_only = any(marker in soul for marker in READ_ONLY_MARKERS)
        if read_only:
            for routine in routines:
                prompt = routine.get("prompt") if isinstance(routine, dict) else None
                if not isinstance(prompt, str) or routine.get("agent") != key:
                    continue
                hits = imperative_hits(prompt, WRITE_VERBS)
                if hits:
                    out.append(Finding(
                        "D007", ERROR,
                        f"agent {key}：soul 说只读，routine {routine.get('key')} 却让它「{hits[0]}」",
                    ))

    if len(routines) > 3:
        out.append(Finding("D008", WARN, f"挂了 {len(routines)} 条例行任务，一个 bot 一件事就够了"))

    # D006：soul 自称只读，requirements.capabilities 里却写了写操作。
    if any(marker in soul for soul in souls.values() for marker in READ_ONLY_MARKERS):
        requirements = meta.get("requirements")
        capabilities = requirements.get("capabilities") if isinstance(requirements, dict) else None
        for capability in capabilities or []:
            if not isinstance(capability, str):
                continue
            hits = imperative_hits(capability, WRITE_VERBS)
            if hits:
                out.append(Finding("D006", ERROR, f"写的是只读，capabilities 却要「{hits[0]}」：{capability}"))
                break

    return out
