---
name: legal-profile-interview-ops
description: 运行律师画像/业务规范访谈时使用。定位并写入 profile.md。
---

# 律师画像访谈与配置读写（运行层）

元力工场「诉讼 / 公司 / 合同」技能包各自带一个冷启动访谈技能（`litigation-cold-start-interview`、
`corporate-cold-start-interview`、`commercial-cold-start-interview`）和对应的 `*-customize`。
它们定义**问什么**。本技能定义**怎么在这台机器上把它跑完**：路径解析、提问方式、集成核验、写入与确认。
访谈的问题清单不要在本技能重复列出——照技能包里的原文问。

## 1. 先解析路径，别翻代码

- `$LEGAL_AGENT_PROFILE_HOME` = `backend/.hermes/profiles`（由 `backend/main.py` 用 `setdefault` 注入；
  同处还注入 `HERMES_HOME=backend/.hermes`、`LEGAL_AGENT_LOCAL_DATA_HOME=backend/.hermes/data`）。
- 画像文件 = `$LEGAL_AGENT_PROFILE_HOME/<bundle_id>/profile.md`。
  **`<bundle_id>` 取自访谈技能自己目录下的 `.legal-agent-skillpack-install.json` 的 `bundle_id` 字段**
  （已验证：`litigation-cold-start-interview` → `litigation-legal`）。不要按技能名猜目录名。
- 跨插件共享的 `company-profile.md` 直接放在 `$LEGAL_AGENT_PROFILE_HOME/` 下，不在 `<bundle_id>/` 里面。
- 该目录不存在或为空 = 全新安装：直接开始访谈，**不要**问「是否覆盖」。
- `HERMES_HOME` 是 `backend/.hermes`，不是用户的 `~/.hermes` —— 读配置、找会话、查 skills 都走前者。

## 2. 提问方式：正文编号列表，然后结束本轮

- 结构化问答工具并非在所有执行上下文都可用（LawClaw 桌面端即不提供）。因此把每一轮的问题写成
  **正文里的编号列表 + 选项**，末句明确「这个问题需要您输入——我等您」，**然后结束该轮**等用户回复。
- 这条在工具可用时同样是对的：问题写在正文里，用户看得见、能一句话回「1 / a / a」，比弹窗更省事。
- 不要因为等待问答工具而空转，也不要自问自答替用户选择。
- 每轮 2-3 个问题为上限（技能包自己的节奏要求），一轮问完再问下一轮，不要一次抛出整份访谈。
- **沿用技能包原文的选项字母，不要重排。** 用户常按技能包原文的字母作答（如「角色选(c) 独立执业」——技能包中 (c) 正是独立执业/小所，而重排后的 (c) 可能是法务）。冲突时以**用户写的标签**为准，顺带用一句话纠正编号，不要按错位的字母往下走。

## 3. 集成检查：配置清单 + 至少一次真实探针

先做这一步，把结果放在 Part 0 提问之前的同一回复里，用「服务名 / 状态」表格呈现。

- 读 `$HERMES_HOME/config.yaml` 的 `mcp_servers:` 段拿已配置清单（本环境为 6 个元典服务：
  `yuandian-law` / `yuandian-case` / `yuandian-company` / `yuandian-contract-review` /
  `yuandian-securities` / `yuandian-hallucination`，鉴权用 `Bearer ${YUANDIAN_API_KEY}`）。
- **至少对一个服务打真实探针**（如 `yuandian_get_user_balance`，返回 `code:200` 记「已连接」）。
  只看配置不探针 = 报「已配置未验证」，不足以支撑后续分流判断。
- 未配置的通道（日历、即时通讯、电子证据平台）单列「未检测到」，并在 profile 里记 `[PLACEHOLDER]`。

## 4. 画像已预填时：确认，但要做成一键确认

`$HERMES_HOME/USER.md` 通常已含姓名、执业领域、团队规模、执业年限。
**不要因此跳过 Part 0** —— 使用者与角色决定整个访谈走哪条路径、以及每份输出的保密标头，必须用户确认。
做法：把画像对应的选项标出来（例：`1. 执业律师/法律专业人士 ← 画像已标注`），
并在每组问题前一句话说明该答案的路由后果。用户回一句就能推进。

## 5. 写入与收尾

- 写入 `$LEGAL_AGENT_PROFILE_HOME/<bundle_id>/profile.md`，注明编写日期，跳过的部分留 `[PLACEHOLDER]`
  （诚实留空好过编造一个门槛）。
- 定稿前把捕获内容回读给用户确认。
- 写入后告诉用户：这是可直接编辑的纯文本文件，输出感觉不对时修复通常在此处，
  且随时可用 `*-customize` 改单项而不重跑访谈。

## 护栏

- **不要手改技能包内技能的内容。** 它们由技能包安装器管理、非 curator 托管，写入会被拒；
  若需长期固化修改，先 `hermes curator adopt <skill-name>` 认领，否则安装器更新会覆盖你的编辑。
- 不要一次问完整份访谈，也不要因为用户说「不知道」而争执或编造——注明并继续。
