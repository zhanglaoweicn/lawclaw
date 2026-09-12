---
name: session-context-recovery
description: 从被中断/失败的上一轮对话中找回原始指令与附件全文（含 docx/pdf 解析结果），在用户只说"重新分析""继续""重做"而无上下文时使用。
author: LawClaw
---

# 会话上下文找回

## 触发条件

- 用户只发一个无宾语的指令：「重新分析」「继续」「重做」「再看一下」「改一下」
- 明显在承接上一轮，但本会话 history=0（新一轮会话 / 模型或 API Key 切换后重开）
- 上一轮曾因鉴权、超时、上下文超限等原因中断，附件没有跟着传递过来

**不要**直接反问"你要我分析什么"——先花几秒钟把上一轮的原文捞出来，再决定是否需要澄清。

## 步骤

### 1. 看日志尾部，确认上一轮发生了什么

```bash
tail -60 "<工作目录>/.hermes/logs/agent.log"
```

关注 `conversation turn: session=... msg='...'` 一行 —— 它包含**上一轮的原始用户消息**（含 `[附件: xxx.docx]` 与解析器/字符数），以及紧随其后的失败原因。

同时看 `errors.log`。

### 2. 取附件全文（关键一步）

请求转储文件保存在 `<工作目录>/.hermes/sessions/request_dump_<会话ID>_<时间戳>.json`，内含**完整请求体**，包括已解析的附件正文。上一次的解析结果就在这里——不需要重新解析 docx。

```python
import json, glob, os
dumps = sorted(glob.glob(r"<工作目录>/.hermes/sessions/request_dump_*.json"),
               key=os.path.getmtime)
d = json.load(open(dumps[-1], encoding="utf-8"))

# 结构： d["timestamp"|"session_id"|"reason"|"request"|"error"]
#       d["request"]["body"]["messages"][N]["content"]
for i, m in enumerate(d["request"]["body"]["messages"]):
    c = m.get("content")
    if isinstance(c, str) and ("附件" in c or "```" in c):
        print("### messages[%d] ###" % i)
        print(c)          # 这里就是「用户消息 + 附件全文 + 历史经验召回」整块
```

要点：
- `messages[1]` 通常是第一条用户消息；但仍应**遍历全部 messages**按内容特征匹配，不要硬编码下标。
- `reason` 字段说明该 dump 为何产生（如鉴权失败、重试）。
- 同一轮会有多个 dump（重试各存一份），**按 mtime 取最新的**；文件大小差异大（140K vs 168K）说明最后一版带了更多内容，优先取大而新的。
- 附件正文以 ``` 代码块包裹，前面一行标注 `（解析器: python-docx，3607 字符）`。取到后即可直接开始工作。

### 3. 快速定位而非全量读取

`request_dump` 单文件可达数百 KB，其中绝大部分是工具定义（`body.tools[*]`）。**不要一次性 print 整个文件**。先递归遍历叶子节点，按关键词过滤出目标 content：

```python
def leaves(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items(): yield from leaves(v, f"{path}/{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o): yield from leaves(v, f"{path}[{i}]")
    else: yield path, str(o)

for p, v in leaves(d):
    if "附件" in v or "docx" in v.lower():
        print(p, "=>", v[:300])
```

### 4. 落盘暂存，再动手

把捞到的原文写到临时文件（如 `.hermes/_contract_extract.txt`）再处理，避免后续多次重复解析大型 JSON。

## 常见坑

- **别把 dump 当成"用户消息"全文** —— `messages[0]` 是 system prompt（很长），真正的用户输入在 `messages[1]`，附件解析结果拼在同一个 content 里。
- **同一会话可能有多个 dump**，只读第一个会拿到被截断/失败的中间版本。
- **会话 DB 里可能查不到**：`session_search` 只索引落库的会话；被鉴权失败打断的那一轮往往未落库，所以搜不到 ≠ 不存在。**日志 + request_dump 是更可靠的一手来源。**
- **模型/API Key 切换会产生新的 session_id**，所以"上一轮"和新会话不是同一个 session。
- 捞到原文后，仍应在回复开头**用一句话说明"已恢复上一轮的附件《XXX》"**，让用户知道你在延续哪件事。
- 若确实捞不到（日志已轮转、dump 已清理），再向用户澄清，并说明已尝试的位置。

## 相关

- `contract-review` — 捞回合同原文后的下游工作流
