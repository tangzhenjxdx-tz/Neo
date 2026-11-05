# Neo

五个只干一件事的 [OpenMausBot](https://github.com/milind-soni/OpenMausBot) 样板 bot。用 `botmrr: 1` 的 Markdown 写，一个文件就是一个 bot。

每个都守同一条规矩：**一个工作、一个声音、明确的 anti-jobs、不留多余工具**。写不出 done-test 的，不收。

## 五个 bot

| 文件 | 一个工作 | 什么时候 | 绝不 |
| --- | --- | --- | --- |
| [`bots/repo-scout.md`](bots/repo-scout.md) | 列出在等你回应的 issue 和 PR，最多 5 条 | 工作日 08:30 | 不回复、不打标签、不关 issue |
| [`bots/ci-watch.md`](bots/ci-watch.md) | 同一原因的连续失败合并成一条告警 | 工作日 10:00、16:00 | 不重跑、不改码、不评论 |
| [`bots/release-notes.md`](bots/release-notes.md) | 把合并的 PR 写成一段 changelog 草稿 | 周五 17:00 | 不打 tag、不建 release |
| [`bots/triage-clerk.md`](bots/triage-clerk.md) | 按四条规则给新 issue 打标签、指一个人 | 工作日 09:00 | 不关闭、不回复、不猜优先级 |
| [`bots/stale-sweeper.md`](bots/stale-sweeper.md) | 列出 30 天没动静的分支和 PR | 周一 08:45 | 不删分支、不关 PR |

## 怎么用

1. 打开任意一个 `.md`，长期指示第一行已经填好 `tangzhenjxdx-tz/Neo`；换仓库就改这一行。
2. 改时区：文件末尾的 `timeZone: Asia/Shanghai` 换成你的。
3. 导入：设置里的「模板 → 导入」，选这个 `.md`。它会被当成一个单 bot 的包，例行任务自动暂停。
   如果你的版本不接受 Markdown，就把 `soul:` 下面那段贴进新建 bot 的长期指示，效果一样。
4. 例行任务默认是**暂停**的。先手动跑一次，看它说的话你受不受得了，再开。

## 为什么长这样

- **一个工作**：每个 bot 都只回答一个问题。写第二件事的时候，去 `templates/build-sheet.md` 重新填一页。
- **anti-jobs**：每个 bot 都有一节「绝不」。这一节比「工作」更能决定它好不好用，模板见 [`templates/anti-jobs.md`](templates/anti-jobs.md)。
- **done-test**：每个 bot 都能用一句「发完就停」判断成没成。没有这个的 bot 不放行。
- **不给多余工具**：需要写权限的地方只有一处（triage），其余全部只读。

## 目录

```
bots/        五个单 bot 文件，一个文件一个 bot
templates/   build sheet 与 anti-jobs 检查表
```

## 许可

Apache-2.0，见 [LICENSE](LICENSE)。`botmrr: 1` 的 Markdown 格式来自 OpenMausBot（Apache-2.0），本仓库只是按这个格式写的配置，不含它的代码。详见 [NOTICE](NOTICE)。
