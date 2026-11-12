#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解析中文剧本 docx 中的台词结构 -> 结构化 JSON（纯标准库，无第三方依赖）

用法:
    python3 parse_dialogue.py "剧本.docx" -o parsed.json
    python3 parse_dialogue.py "剧本.docx" --ledger          # 只打角色台账
    python3 parse_dialogue.py "剧本.docx" --duplicates      # 查重复句（句式撞车）
    python3 parse_dialogue.py "剧本.docx" --scene 21        # 只看某场

输出 JSON:
{
  "source": "...",
  "stats": {...},
  "ledger": [{speaker, count, avg_len, tone_rate, tone_words, top_words}],
  "paragraphs": [
    {"index":0, "type":"scene|action|dialogue|os|sfx|other",
     "scene_id":"第二十一场", "speaker":"周小满", "content":"...", "text":"周小满：..."}
  ]
}

type 说明:
  scene    场次标题（第X场）
  action   △ 动作/舞台指示行
  dialogue 对白（角色名：内容）
  os       内心独白 / 画外音（周小满os：..., XXX vo：...）
  sfx      音效标记（【音效 xxx】）
  other    其他（分集标题、空行、说明文字）

index 是 <w:p> 段落在 word/document.xml 中的 0-based 顺序号，
apply_dialogue.py 用同一套提取逻辑，保证 index 严格对齐。
"""
from __future__ import annotations

import argparse
import collections
import html
import json
import os
import re
import statistics
import sys
import zipfile

PARA_RE = re.compile(r"<w:p(?:\s[^>]*)?>.*?</w:p>", re.S)
TEXT_RE = re.compile(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", re.S)
# 场次标题：兼容两种剧本格式
#   「第二十一场：修理间・日・内」（短剧）
#   「场1-1　△外·片场灵堂台阶　日」（漫剧）
SCENE_RE = re.compile(
    r"第\s*[一二三四五六七八九十百千零〇两\d]+\s*场"
    r"|场\s*\d+\s*[-—－]\s*\d+"
)
# 集标题：「第1集《十七块八》」
EPISODE_RE = re.compile(r"^第\s*\d+\s*集")
# 人物表行：「人物：周小满、阿亮、站长（语音）」——不是台词，是场次头部信息
CAST_RE = re.compile(r"^人物\s*[:：]")
# 节拍标记：「【起】开场冲突」「【承】推进发展」
BEAT_RE = re.compile(r"^[【\[]\s*(起|承|转|钩|合)")
OS_RE = re.compile(r"(?i)(os|vo)\s*[:：]|画外音|旁白")
SPEAKER_RE = re.compile(r"^([^\s：:]{1,16})\s*[:：]\s*(.*)$", re.S)
SFX_RE = re.compile(r"^[【\[]\s*(音效|音|SFX|BGM)", re.I)

# 口语颗粒：句尾助词 + 垫词 + 应答词 + 程度垫词
TONE_WORDS = ["啊", "吧", "呢", "嘛", "呗", "啦", "呀", "哦", "咯", "么",
              "唉", "哎", "嘿", "哟", "啧", "得了", "行吧", "那什么", "你说"]
# 书面虚词（A 类，现代/年代剧台词禁用）
BOOK_WORDS = ["是否", "因此", "从而", "鉴于", "予以", "加以", "可否", "颇为",
              "甚为", "以及", "由于", "进行", "兹", "并且", "何以"]


def read_document_xml(docx_path: str) -> str:
    with zipfile.ZipFile(docx_path) as zf:
        name = "word/document.xml"
        if name not in zf.namelist():
            raise RuntimeError(f"不是有效的 docx（缺少 {name}）: {docx_path}")
        return zf.read(name).decode("utf-8")


def plain_text(block: str) -> str:
    return html.unescape("".join(TEXT_RE.findall(block))).strip()


def iter_paragraph_blocks(xml_text: str):
    for i, m in enumerate(PARA_RE.finditer(xml_text)):
        block = m.group(0)
        yield i, m.start(), m.end(), block, plain_text(block)


def classify(text: str) -> str:
    if not text:
        return "other"
    s = text.strip()
    if SFX_RE.match(s):
        return "sfx"
    if BEAT_RE.match(s):
        return "beat"                 # 【起】开场冲突 等节拍标记
    if EPISODE_RE.match(s):
        return "episode"              # 第1集《十七块八》
    if CAST_RE.match(s):
        return "cast"                 # 人物：A、B、C  ← 不是台词！
    if SCENE_RE.search(s[:24]):
        return "scene"
    if s.startswith("△") or s.startswith("▲"):
        return "action"
    m = SPEAKER_RE.match(s)
    if m:
        speaker = m.group(1)
        if re.search(r"(?i)(os|vo)$", speaker) or OS_RE.search(s[:24]):
            return "os"
        return "dialogue"
    return "other"


def split_speaker(text: str) -> tuple[str, str]:
    """拆出 (说话人, 正文)。拆不出返回 ('', text)

    说话人带的 os / vo 后缀会被剥离（"周小满os" -> "周小满"），
    这样台账能把同一个人格的画内台词与内心独白合在一起统计。
    """
    m = SPEAKER_RE.match(text.strip())
    if not m:
        return "", text.strip()
    speaker = m.group(1).strip()
    stripped = re.sub(r"(?i)\s*(os|vo)$", "", speaker).strip()
    if stripped:                      # 剥离后为空说明整句就是 "OS：" 这种，保留原样
        speaker = stripped
    return speaker, m.group(2).strip()


def norm_speaker(speaker: str) -> str:
    """台账归一：去掉说话人后的括号说明（站长（语音） -> 站长）"""
    s = re.sub(r"[（(][^）)]*[）)]", "", speaker).strip()
    return s or speaker


def build(docx_path: str) -> dict:
    xml_text = read_document_xml(docx_path)
    paragraphs = []
    current_scene = ""
    for idx, _s, _e, _block, text in iter_paragraph_blocks(xml_text):
        typ = classify(text)
        if typ == "scene":
            m = SCENE_RE.search(text)
            current_scene = m.group(0) if m else text[:20]
        speaker, content = "", ""
        if typ in ("dialogue", "os"):
            speaker, content = split_speaker(text)
        paragraphs.append({
            "index": idx,
            "type": typ,
            "scene_id": current_scene,
            "speaker": speaker,
            "content": content,
            "text": text,
        })

    stats = {
        "total_paragraphs": len(paragraphs),
        "episodes": sum(1 for p in paragraphs if p["type"] == "episode"),
        "scenes": sum(1 for p in paragraphs if p["type"] == "scene"),
        "actions": sum(1 for p in paragraphs if p["type"] == "action"),
        "dialogues": sum(1 for p in paragraphs if p["type"] == "dialogue"),
        "os": sum(1 for p in paragraphs if p["type"] == "os"),
        "sfx": sum(1 for p in paragraphs if p["type"] == "sfx"),
        "cast": sum(1 for p in paragraphs if p["type"] == "cast"),
        "beat": sum(1 for p in paragraphs if p["type"] == "beat"),
        "other": sum(1 for p in paragraphs if p["type"] == "other"),
        "lines": sum(1 for p in paragraphs if p["type"] in ("dialogue", "os")),
    }

    return {
        "source": os.path.abspath(docx_path),
        "stats": stats,
        "ledger": build_ledger(paragraphs),
        "paragraphs": paragraphs,
    }


def build_ledger(paragraphs: list[dict]) -> list[dict]:
    """角色台词台账：句数 / 均长 / 语气词率 / 专属词（按归一后的说话人聚合）"""
    groups: dict[str, list[str]] = collections.defaultdict(list)
    for p in paragraphs:
        if p["type"] in ("dialogue", "os") and p["speaker"]:
            groups[norm_speaker(p["speaker"])].append(p["content"])

    ledger = []
    for speaker, contents in groups.items():
        lens = [len(c) for c in contents]
        tone_hits = sum(1 for c in contents if any(w in c for w in TONE_WORDS))
        # 专属词：该角色高频 2-3 字词（粗粒度，仅作参考）
        cnt = collections.Counter()
        for c in contents:
            for w in re.findall(r"[\u4e00-\u9fa5]{2,3}", c):
                cnt[w] += 1
        common = [w for w, n in cnt.most_common(60)
                  if n >= 3 and w not in ("什么", "怎么", "这个", "那个", "我们", "你们",
                                          "他们", "自己", "知道", "一个", "不是", "就是")]
        ledger.append({
            "speaker": speaker,
            "count": len(contents),
            "avg_len": round(statistics.mean(lens), 1) if lens else 0,
            "max_len": max(lens) if lens else 0,
            "std_len": round(statistics.pstdev(lens), 1) if len(lens) > 1 else 0,
            "tone_rate": round(tone_hits / len(contents) * 100, 1) if contents else 0,
            "top_words": common[:6],
        })
    ledger.sort(key=lambda x: -x["count"])
    return ledger


def find_duplicates(paragraphs: list[dict], min_times: int = 3, min_len: int = 4):
    """找重复句（句式撞车的证据）。返回 [(句子, 次数, [说话人...])]"""
    seen: dict[str, list[str]] = collections.defaultdict(list)
    for p in paragraphs:
        if p["type"] in ("dialogue", "os") and len(p["content"]) >= min_len:
            seen[p["content"]].append(p["speaker"])
    rows = [(k, len(v), v) for k, v in seen.items() if len(v) >= min_times]
    rows.sort(key=lambda x: -x[1])
    return rows


def diagnose(paragraphs: list[dict]) -> dict:
    """基础诊断：九类病灶的可机检部分"""
    lines = [p for p in paragraphs if p["type"] in ("dialogue", "os")]
    total = len(lines) or 1

    water = [p for p in lines if p["content"].strip("。！？…， ") in
             ("嗯", "哦", "啊", "好", "好的", "行", "行了", "知道了", "明白了",
              "懂了", "是", "对", "没事", "没什么", "谢谢", "对不起")]
    book = [p for p in lines if any(w in p["content"] for w in BOOK_WORDS)]
    emo_re = re.compile(r"(我(很|好|太|特别|真的)|气死|伤心死|难过死|开心死|害怕死)")
    emo = [p for p in lines if emo_re.search(p["content"])]
    long_no_pause = [p for p in lines
                     if len(p["content"]) >= 25 and not re.search(r"[，。！？…、；：—]", p["content"])]
    end_punct = collections.Counter(p["content"][-1] for p in lines if p["content"])
    tone_hits = sum(1 for p in lines if any(w in p["content"] for w in TONE_WORDS))
    dup = find_duplicates(paragraphs)

    return {
        "total_lines": len(lines),
        "water": len(water),
        "book_words": len(book),
        "emotion_declared": len(emo),
        "long_no_pause": len(long_no_pause),
        "tone_rate": round(tone_hits / total * 100, 1),
        "period_rate": round(end_punct.get("。", 0) / total * 100, 1),
        "exclaim_rate": round(end_punct.get("！", 0) / total * 100, 1),
        "duplicate_groups": len(dup),
        "samples": {
            "water": [f'{p["speaker"]}：{p["content"]}' for p in water[:8]],
            "book_words": [f'{p["speaker"]}：{p["content"][:40]}' for p in book[:8]],
            "duplicates": [f'x{n}  {k[:30]}  ({"/".join(sorted(set(s)))})' for k, n, s in dup[:10]],
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="解析剧本台词结构")
    ap.add_argument("docx", help="剧本 docx 路径")
    ap.add_argument("-o", "--output", help="输出 JSON 路径")
    ap.add_argument("--ledger", action="store_true", help="打印角色台词台账")
    ap.add_argument("--duplicates", action="store_true", help="查重复句")
    ap.add_argument("--diagnose", action="store_true", help="打印基础诊断")
    ap.add_argument("--scene", help="只显示指定场次（如 21）")
    args = ap.parse_args()

    if not os.path.isfile(args.docx):
        print(f"[ERROR] 文件不存在: {args.docx}", file=sys.stderr)
        return 2

    data = build(args.docx)
    s = data["stats"]

    if args.ledger:
        print(f'{"角色":<10}{"句数":>6}{"均长":>7}{"最长":>6}{"标准差":>8}{"语气词率":>9}  专属词')
        for r in data["ledger"][:20]:
            print(f'{r["speaker"]:<10}{r["count"]:>6}{r["avg_len"]:>7}{r["max_len"]:>6}'
                  f'{r["std_len"]:>8}{r["tone_rate"]:>8}%  {" ".join(r["top_words"][:5])}')

    if args.duplicates:
        dup = find_duplicates(data["paragraphs"])
        print(f"\n重复 ≥3 次的句子: {len(dup)} 组")
        for k, n, sp in dup:
            print(f'  x{n}  {k[:36]}  ← {"/".join(sorted(set(sp)))}')

    if args.diagnose:
        dg = diagnose(data["paragraphs"])
        print("\n==== 基础诊断 ====")
        print(f'台词总行数 {dg["total_lines"]}')
        print(f'  水词/纯应答      {dg["water"]:>5}')
        print(f'  书面虚词        {dg["book_words"]:>5}')
        print(f'  情绪直白宣告     {dg["emotion_declared"]:>5}')
        print(f'  长句无气口      {dg["long_no_pause"]:>5}')
        print(f'  重复句组        {dg["duplicate_groups"]:>5}')
        print(f'  语气词率        {dg["tone_rate"]:>5}%')
        print(f'  句末句号率      {dg["period_rate"]:>5}%')
        print(f'  感叹句率        {dg["exclaim_rate"]:>5}%')

    if args.output:
        payload = data
        if args.scene:
            key = args.scene.replace("第", "").replace("场", "")
            payload = dict(data)
            payload["paragraphs"] = [p for p in data["paragraphs"]
                                     if key in p["scene_id"] or p["scene_id"].endswith(key)]
            print(f'# 场次筛选 {args.scene} -> {len(payload["paragraphs"])} 段', file=sys.stderr)
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"[OK] 已写出 {args.output}")
        head = f'  集 {s["episodes"]} | ' if s.get("episodes") else '  '
        print(head + f'场次 {s["scenes"]} | △动作 {s["actions"]} | 对白 {s["dialogues"]} | '
                     f'os {s["os"]} | 音效 {s["sfx"]} | 人物表 {s.get("cast", 0)} | '
                     f'节拍 {s.get("beat", 0)} | 其他 {s["other"]} | 总段落 {s["total_paragraphs"]}')
        print(f'  台词行合计 {s["lines"]}')

    if not (args.ledger or args.duplicates or args.diagnose or args.output):
        print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
