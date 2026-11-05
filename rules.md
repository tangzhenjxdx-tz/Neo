# 规则全文

`neo check` 的每一条都在这里：查什么、为什么、怎么改。

格式规则（N）的事实依据是 OpenMausBot 的 `shared/package-format.ts`；设计规则（D）是 Neo 自己的标准。

## 格式

| 编号 | 级别 | 查什么 | 怎么改 |
| --- | --- | --- | --- |
| N001 | error | 文件以 `---` 包住的 YAML 开头 | 别删 frontmatter |
| N002 | error | frontmatter 是合法 YAML | 常见原因是缩进不齐、冒号后没空格 |
| N003 | error | `botmrr: 1` | 版本不对，解析器直接拒 |
| N004 | error | id、release、name、tagline、summary、category、license 都在 | 缺哪个补哪个 |
| N005 | error | id 只用小写字母、数字、`-` | `Repo-Scout` → `repo-scout` |
| N006 | error | release 是 `1.2.3` | 不要 `v1`、不要 `1.0` |
| N007 | error | name≤100、tagline≤160、summary≤2000、category≤80 | 长的挪进正文 |
| N008 | error | `author.name` 在 | 写上是谁做的 |
| N009 | error | outcomes 1–12 条，每条≤240 字 | 这是「装完能得到什么」，不是功能列表 |
| N010 | error | setupMinutes 是 1–240 的整数 | 估个数，别写 0 |
| N011 | error | requirements 有 apps 和 capabilities | 没有就写 `apps: []`、`capabilities: []` |
| N012 | error | 至少一个 agent | 多 bot 包才有多个 |
| N013 | error | agent 的 key 合法、有 name、颜色在白名单、description≤4000 | 颜色只有 green blue red orange purple cyan pink yellow teal coral silver chrome |
| N014 | error | soul≤24000 字节 | 超了说明你在写小说 |
| N015 | error | routine 的 key、name、agent 归属、schedule、durationMinutes、`enabledAfterInstall: false` | 装完必须先暂停，让人看一次再开 |
| N016 | error | 正文有七个固定小节 | Activation / Mission / Outcomes / Connections / Team / Chief of Staff / Completion rule |

schedule 认四种：

```yaml
schedule:
  type: cron
  expression: "30 8 * * 1-5"
  timeZone: Asia/Shanghai
```

```yaml
schedule:
  type: daily
  time: "08:00"
  weekdays: [1, 2, 3, 4, 5]   # 0 是周日
```

```yaml
schedule:
  type: interval
  everyMinutes: 30
  anchorAt: 1762300800000     # 毫秒时间戳
```

```yaml
schedule:
  type: once
  at: 1762300800000
```

## 设计

| 编号 | 级别 | 查什么 | 为什么 |
| --- | --- | --- | --- |
| D001 | error | soul 里有 `## 工作` | 一句话说不清它干什么，别人没法核对 |
| D002 | error | soul 里有 `## 绝不` | 没有 anti-jobs 的 bot 什么都敢做 |
| D003 | error | 「绝不」至少两条 | 一条通常是「不给人类添麻烦」这种废话 |
| D004 | error | soul 里有 `## 完成标准` | 没有 done-test 就不知道什么时候该停 |
| D005 | error | 完成标准不含「适当、尽量、合适、看情况、差不多、酌情、根据需要、视情况」 | 这些词让它每次都算完成了 |
| D006 | error | 自称只读，capabilities 里就不能有写操作 | 说只读却要「打标签」，是最常见的权限膨胀 |
| D007 | error | routine 的指令不能与 soul 的 anti-jobs 冲突 | soul 写「不回复」，routine 写「回复每一条」 |
| D008 | warn | routine 不超过三条 | 一个 bot 背三个班，每个都做不好 |
| D009 | warn | soul 里有 `## 声音` | 没有声音的 bot 说话像说明书 |
| D010 | warn | 至少一个 agent 写了 soul | 只有 description 的 bot，行为全靠模型当天心情 |

D006、D007 只看**指令行开头**的动词：`别人回复的 PR` 不算，`回复每一条` 才算。以「不」「别」「勿」「禁止」开头的行整行跳过。

## 级别与退出码

- `error`：`neo check` 返回 1。
- `warn`：默认不影响退出码，`--strict` 时也算失败。

CI 里建议跑 `neo check bots --strict`。
