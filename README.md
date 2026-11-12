# script-dialogue-polish · 中文短剧台词优化工作流

给一份剧本 docx，把台词（对白 + os）改成**能推动剧情、像活人说的、有画面感**的台词。
**只改台词正文**——说话人前缀、△ 动作行、场次标题、剧情事实全部零改动，另存新文件不覆盖原件。

> 姊妹项目：**[script-to-visual](https://github.com/ShiXiangYu2/script-to-visual)** 管 △ 动作行的画面化，本项目管台词。两者互不越界。

---

## 它解决什么问题

大多数"台词优化"最后都变成两种翻车：**把短句全拉长**（电报体 → 文艺腔），或者**给所有人加"啊/吧/呢"**（全员一个腔）。
这个工作流的办法是：**先体检、再分级、只打点**。

| 阶段 | 干什么 | 产出 |
|---|---|---|
| ① 解析 | 拆出对白 / os / △ / 场次 / 人物表 / 节拍，建角色台词台账 | `parsed.json` |
| ② 诊断 | 九类病灶逐条扫，分 P0/P1/P2/P3 | 诊断报告（**先给用户看**） |
| ③ 改写 | 删 / 换 / 补 / 转 / 接 五法，按病灶选法 | `rewrite_map.json` |
| ④ 机检 + 落盘 | D1–D10 十项机检 → OOXML 原位替换 | 优化稿 + 逐条对照表 |

**改动力度纪律**：命中率控制在 **20–35%** 是健康的。超过 50% 说明在为了产出而制造改动——那会把已经达 1 级的句子改坏。

---

## 验收标准（唯一判据）

### 文笔五级（从高到低）

| 级 | 名称 | 判定锚点 | 结论 |
|---|---|---|---|
| 1 | 修辞手法 | 强动词 + 具体名词，零形容词堆砌，读完脑内成像（`雨砸在青石板上`） | ✅ 满分 |
| 2 | 语序 | 通顺有节奏，指代明确（合格线） | ✅ 达标 |
| 3 | 词藻 | 形容词/成语堆叠，抽掉修饰什么都不剩 | ❌ 要删 |
| 4 | 粗糙 | 只有"谁做了什么"，无细节无态度 | ❌ 要补 |
| 5 | 看不懂 | 指代不明、因果断裂 | ❌ 重写 |

**3 级和 4 级是反方向的错**：改 3 级靠删，改 4 级靠补。搞反就把句子改坏了。

### 台词三条硬要求

1. **不要无效台词、水词**——删除测试：删掉这句，信息/立场/筹码/关系/行动五项全不变 → 废句。
2. **台词要推动剧情**——每句至少产生一项变动。
3. **正常口语化**——零书面虚词、有口语颗粒（按角色分配）、无译制片腔、长短交错。
   **口语化 ≠ 加废话**。

---

## 快速开始

```bash
git clone https://github.com/ShiXiangYu2/script-dialogue-polish.git
cd script-dialogue-polish

# 1 解析（同时出角色台账与基础诊断）
python3 scripts/parse_dialogue.py 剧本.docx -o parsed.json
python3 scripts/parse_dialogue.py 剧本.docx --ledger --diagnose

# 2 照 parsed.json 里的 index 写改写映射（见 templates/）
#    key = 段落 index，value = 改后的整行文本（保留「说话人：」前缀）

# 3 机检（FAIL 必须 0）
python3 scripts/check_dialogue.py parsed.json rewrite_map.json -o 对照表.md

# 4 落盘（另存新文件，自动跑四项回读验证）
python3 scripts/apply_dialogue.py 剧本.docx rewrite_map.json 剧本_台词优化稿.docx
```

**零依赖**：三个脚本全部纯 Python 标准库（不需要 python-docx / lxml）。

### 跑一遍示例

```bash
python3 examples/build_demo_docx.py          # 生成虚构剧本《末班车》
python3 scripts/parse_dialogue.py examples/demo_episode.docx -o examples/parsed.json
python3 scripts/check_dialogue.py examples/parsed.json examples/demo_rewrite_map.json
python3 scripts/apply_dialogue.py examples/demo_episode.docx \
        examples/demo_rewrite_map.json examples/demo_episode_polished.docx
```

示例输出：

```
改写 9 / 台词 47 行 （命中率 19.1%）
🔴 FAIL 0   🟡 WARN 0
[OK] 已生成 examples/demo_episode_polished.docx
  改写台词: 9 条 | 其余内容字节级保持不变

---- 回读验证 ----
  段落数不变          ✅
  改动数 = 映射数      ✅（9 / 9）
  非台词行零改动       ✅（0 处）
  台词行数不变         ✅（47 / 47）
```

9 条改动长这样（完整对照见 [`examples/demo_before_after.md`](examples/demo_before_after.md)）：

| 原 | 改 | 病灶 → 手法 |
|---|---|---|
| 阿亮：哦。 | 阿亮：哦。那我再数一遍。 | 水词 → 升级为有信息的应答 |
| 阿亮：上午的票根？ | 阿亮：票根？票根不都在你抽屉里。 | 复述已知 → 质疑 |
| 阿亮os：这一摊子事跟乱麻似的，我心里说不清是什么滋味。 | 阿亮os：票根上的数，对不上。 | 堆词 3 级 → 删到只剩物证 |
| 周小满：我需要你给我出一份证明，说明这辆车的刹车在今天上午十点之前是完好的。 | 周小满：陈师傅，给我写个条。今天上午十点那趟，刹车是好的。 | 译制片腔 → 断成三截 |
| 周小满os：我以为他会点头。他没抬头。往后的路，得自己一步一步踩出来。 | 周小满os：我以为他会点头。他没抬头。 | 端着的总结句 → 删 |
| 马德胜：这个事，我们要研究一下。 | 马德胜：这事得开会。研究完再说。 | 流水账 4 级 → 补锚点 |
| 周小满：站长，我要求核查上午的售票记录。 | 周小满：站长，把上午的售票记录给我看。 | 书面腔 → 换成口语 |

---

## 六条硬约束（违反即回退）

1. **只改台词正文**。`周小满：` 这个「说话人 + 冒号」前缀一个字不动（D1 校验）。
2. **不增删台词行**。行数不变、顺序不变——下游分镜、配音、字幕都按行对齐（D2 校验）。
3. **△ 动作行 / 场次标题 / 音效标记 零改动**（D3 校验）。
4. **剧情事实不增不减**。时间、数字、人名、地点、物件，原文有什么就留什么（D4 校验）。
5. **不破人物身份**。惜字如金的人还是惜字如金，不能改成话痨；改完要过**遮挡名测试**。
6. **不改事件、不改因果**。只改"怎么说"，不改"发生了什么"。

---

## 机检能抓什么，抓不到什么

| 机检（FAIL） | 机检（WARN） |
|---|---|
| D1 前缀被改 / D2 行数变化 / D3 改了非台词行 / D4 事实锚点丢失 | D5 书面虚词 / D6 长句无气口 / D7 水词 / D8 情绪直白 / D9 译制片腔 / D10 同角色重复 |

**抓不到**（必须人工过）：这句是否推动剧情、潜台词是否成立、语气词加得对不对、是否破人设、1 级和 2 级的分界。

> **机检 FAIL 0 ≠ 台词好**，只代表没犯这十类硬错。
> 真实项目里出现过这种情况：机检几乎全通过，真正的问题只有 39 条（占 2003 条台词的 1.9%），而且同一个来源——作者为了让剧情事实严谨，把台词往说明书方向推了一格。**这种病，机器只能提示，人才能判。**

---

## 目录

```
script-dialogue-polish/
├── SKILL.md                    # 工作流主文档（给 Agent 读的）
├── references/
│   ├── 01-诊断清单.md          # 九类病灶 + 判定 + 优先级
│   ├── 02-改写手法.md          # 删/换/补/转/接 五法 + 改前改后对照
│   ├── 03-角色语言指纹.md      # 声纹台账 + 遮挡名测试 + 称呼矩阵 + 词汇时代盘
│   ├── 04-校验规则.md          # D1-D10 机检口径 + 人工检查单
│   └── 05-文笔五级判断法.md     # 把"修辞/语序/词藻/粗糙/看不懂"译成 30 秒可判的四个问题
├── scripts/
│   ├── parse_dialogue.py       # 解析（含角色台账、--duplicates 句式撞车）
│   ├── check_dialogue.py       # 机检 D1-D10
│   └── apply_dialogue.py       # OOXML 原位替换落盘（自动回读验证）
├── templates/rewrite_map.example.json
├── examples/                   # 虚构剧本《末班车》完整跑通示例
└── vendor/                     # 第三方方法论素材（MIT，见 SOURCES.md）
```

### 已适配的剧本格式

| 格式 | 场次写法 | 示例 |
|---|---|---|
| 短剧（集-场） | `第X场` | `第二十一场：修理间・日・内` |
| 漫剧（场次编号） | `场X-Y` | `场1-1　△外·片场灵堂台阶　日` |

自动避开三类**非台词行**（判错会把它们当台词改坏）：集标题 `第7集《末班车》`、人物表 `人物：周小满、阿亮、站长（语音）`、节拍标记 `【起】开场冲突`。

---

## 为什么用 OOXML 原位替换

不用 python-docx 重写文档，而是**复制原 docx 的 zip，只替换目标段落的 `<w:t>` 文字**：

- 排版、字体、图片、页码、页眉 100% 保留（重写必然掉格式）
- 天然满足"另存新文件不覆盖原件"
- 段落 index 严格对齐，改完能逐段回读比对

代价是：**段落结构不能动**。这正好和"不增删行"的硬约束一致。

---

## 第三方素材

`vendor/` 下是三家 MIT 仓库的方法论原文，**原样保留、未修改**，逐一在 [`vendor/SOURCES.md`](vendor/SOURCES.md) 署名：

- [zenstory-ai/drama-skills](https://github.com/zenstory-ai/drama-skills) — 台词即行动论、潜台词三层、交换说话者测试
- [lixiaoxiao9888-create/manju-laoli-skill](https://github.com/lixiaoxiao9888-create/manju-laoli-skill) — 台词七维诊断、书面→口语禁用表、称呼四轴矩阵
- [tance-mang/chinese-webnovel-skills](https://github.com/tance-mang/chinese-webnovel-skills) — 好台词五原则、语言指纹四要素

`references/` 与 `scripts/` 是基于上述方法**重新组织**的可执行口径，不直接照搬原文。

> `vendor/` 里出现的人物名属第三方作者自己的示例，与本项目 `examples/` 的虚构剧本《末班车》无关。

---

## License

MIT（见 [LICENSE](LICENSE)）。`vendor/` 下文件遵循各自上游许可证。

示例剧本《末班车》为虚构作品，人物、情节、数字均属虚构，与任何真实作品无关。
