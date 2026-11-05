# Neo

**导入之前，先把 bot 检查一遍。**

OpenMausBot 的 bot 是一个 `botmrr: 1` 的 Markdown 文件。能导入，不代表能用：大部分 bot 没写「绝不」，没写「什么算完」，要的权限比干的活还多。等你发现它在乱发消息，已经喂了一周的错输出。

Neo 是一个命令行检查器，读你的 bot 文件，报两类问题：

- **格式 `N-xx`**：照 OpenMausBot 的解析器核。错了，导入直接失败。
- **设计 `D-xx`**：导得进去，但用起来会坏。没有 anti-jobs、没有 done-test、说只读却要写权限。

## 三十秒

```bash
git clone https://github.com/tangzhenjxdx-tz/Neo && cd Neo
pipx install .          # 或者 pip install -e .

neo new morning --name 晨报 --job "把过去 24 小时的 AI 新闻压成三条" --cron "0 8 * * 1-5"
neo check morning.md
```

```
写好了 morning.md
过了检查。下一步：把「绝不」改成你真正怕它做的事。
```

查一个装了坏 bot 的目录：

```
$ neo check examples/bad

FAIL examples/bad/no-anti-jobs.md
     D002  error  agent editor：没有「## 绝不」，边界是空的
FAIL examples/bad/vague-done-test.md
     D005  error  agent editor：完成标准里有「看情况、差不多」，没法核对
FAIL examples/bad/readonly-writes.md
     D006  error  写的是只读，capabilities 却要「打标签」：打标签和指派 reviewer

4 个文件 · 4 个没通过 · 4 个错误 · 0 个提醒
```

退出码 `0` / `1`，可以直接挂在 CI 里；`--json` 给机器读，`--strict` 把提醒也算失败。

## 命令

| 命令 | 干什么 |
| --- | --- |
| `neo check <文件或目录>` | 检查，可递归 |
| `neo new <slug> --name --job` | 生成一个立刻能通过检查的骨架 |
| `neo rules` | 列出全部规则 |

`neo new` 还认 `--cron "0 8 * * 1-5"`、`--timezone`、`--out`。

## 规则

### 格式（错了导不进去）

| 编号 | 查什么 |
| --- | --- |
| N001–N002 | 文件开头有 `---` 包住的 YAML，且是合法 YAML |
| N003 | `botmrr: 1` |
| N004 | id / release / name / tagline / summary / category / license 齐全 |
| N005–N006 | id 是小写 slug，release 是 `1.2.3` |
| N007 | 文本字段不超上限（name 100、tagline 160、summary 2000…） |
| N008–N010 | author.name 在；outcomes 1–12 条；setupMinutes 1–240 |
| N011 | requirements 有 apps 和 capabilities，没有就写 `[]` |
| N012–N014 | 至少一个 agent；key、颜色、尺寸合法；soul 不超 24000 字节 |
| N015 | routine 的归属、四类 schedule、时长、`enabledAfterInstall: false` |
| N016 | 正文七个固定小节：Activation / Mission / Outcomes / Connections / Team / Chief of Staff / Completion rule |

### 设计（导得进去，但用起来会坏）

| 编号 | 查什么 | 为什么 |
| --- | --- | --- |
| D001 | soul 里有 `## 工作` | 一句话说不清它干什么，就没人能核对 |
| D002–D003 | 有 `## 绝不`，且至少两条 | 边界比工作更能决定它好不好用 |
| D004–D005 | 有 `## 完成标准`，且不含「看情况」「差不多」 | 没法核对的完成标准等于没有 |
| D006 | 自称只读，就不许申请写权限 | 说一套要一套，是最常见的翻车方式 |
| D007 | routine 不许让它做 soul 禁止的写操作 | 设定写「不回复」，定时任务却写「回复每一条」 |
| D008 | 一个 bot 不超过三条 routine（提醒） | 一个 bot 背三个班，每个都做不好 |
| D009 | 有 `## 声音`（提醒） | 没有声音的 bot 说话像说明书 |
| D010 | 至少一个 agent 写了 soul（提醒） | 只有一句 description 的 bot，行为全靠模型当天心情 |

规则全文和修改建议在 [rules.md](rules.md)。

## 它不检查的

- 不检查它说的话好不好听，也不替你改文案。
- 不检查外部 API 能不能连上；`requirements.apps` 只是声明。
- 不真的导入应用，所以「导入后长什么样」仍需你自己看一眼。
- 不猜你的意图。`neo new` 生成的「绝不」是占位用的两条，必须你自己改。

## 为什么是这些规则

格式规则的每一条都能在 OpenMausBot 的 `shared/package-format.ts` 里找到对应约束（截至 commit `c7e50aa`）。设计规则来自反复踩坑：一个 bot 只有一件事、写清绝不做什么、能用一句话判断成没成。

`examples/good/` 里是七个通过检查的 bot（工作日晨报、邮件分诊、仓库值班……），`examples/bad/` 里是四个各错一处的反面教材。测试拿它们当输入跑，规则改了先跑测试。

## 开发

```bash
python3 -m unittest discover -s tests -v
neo check examples/good
```

## 许可

Apache-2.0，见 [LICENSE](LICENSE)。格式规则参照 OpenMausBot（Apache-2.0）的解析器写成，未复制其代码，详见 [NOTICE](NOTICE)。
