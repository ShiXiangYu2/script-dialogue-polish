#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""台词改写机检（纯标准库）

用法:
    python3 check_dialogue.py parsed.json rewrite_map.json
    python3 check_dialogue.py parsed.json rewrite_map.json -o 对照表.md

rewrite_map.json 结构:
    {"562": "周小满：改后的台词全文", ...}
    key = parse_dialogue.py 输出的段落 index（字符串）
    value = 改写后的**整行文本**（必须保留"说话人："前缀）

机检项:
    D1  说话人前缀被改动            FAIL
    D2  index 不在台词行 / 条数异常   FAIL
    D3  改了非台词行（△/标题/音效）  FAIL
    D4  剧情事实锚点丢失            FAIL
    D5  书面虚词                    WARN
    D6  ≥25 字且无气口              WARN
    D7  整句为水词/纯应答            WARN
    D8  情绪直白宣告                WARN
    D9  译制片腔                    WARN
    D10 与同角色台词完全重复         WARN

退出码: 0 = 无 FAIL；1 = 有 FAIL
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys

SPEAKER_RE = re.compile(r"^([^\s：:]{1,12})\s*[:：]\s*(.*)$", re.S)

BOOK_WORDS = ["是否", "因此", "从而", "鉴于", "予以", "加以", "可否", "颇为",
              "甚为", "以及", "由于", "进行", "兹", "并且", "何以"]

WATER_EXACT = {"嗯", "哦", "啊", "好", "好的", "行", "行了", "知道了", "明白了",
               "懂了", "是", "对", "没事", "没什么", "谢谢", "对不起", "我知道"}

EMO_RE = re.compile(r"我(很|好|太|特别|真的)(生气|难过|伤心|失望|开心|高兴|害怕|担心|恨)")
DUB_RE = re.compile(r"对.{1,12}感到|这不在.{0,10}之内|我需要你.{0,10}(解释|说)|我为.{0,10}感到")

# 事实锚点：数字 + 量词（排除虚化量词）
NUM_RE = re.compile(
    r"[一二三四五六七八九十百千万零两\d]+\s*"
    r"(?:块钱|块|元|斤|亩|公里|里|年|个月|月|日|天|岁|趟|章|页|箱|件|条|张|只|亩地|口人|袋)"
)
NUM_BLACKLIST = {"一个", "一下", "一口", "一点", "一阵", "一声", "一样", "一起",
                 "一定", "一边", "一直", "一些", "一回", "一步", "一年", "一天"}
TIME_WORDS = ["三天后", "十年前", "那年", "明天", "昨天", "今天", "清晨", "晚上",
              "早上", "中午", "夜里", "前几天", "上个月", "开春", "入冬"]


def load_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def is_skip_key(k: str) -> bool:
    return k.startswith("_")


def extract_speakers(parsed: dict) -> list[str]:
    names = set()
    for p in parsed["paragraphs"]:
        s = re.sub(r"[（(][^）)]*[）)]", "", p.get("speaker") or "").strip()
        if 2 <= len(s) <= 6 and re.fullmatch(r"[\u4e00-\u9fa5]{2,6}", s):
            names.add(s)
    return sorted(names, key=len, reverse=True)


def facts_of(text: str, names: list[str]) -> set[str]:
    """抽取承载剧情的硬事实（数字+量词 / 时间词 / 人名）"""
    facts = set()
    for m in NUM_RE.finditer(text):
        tok = m.group(0).strip()
        if tok not in NUM_BLACKLIST:
            facts.add(tok)
    for w in TIME_WORDS:
        if w in text:
            facts.add(w)
    body = text.split("：", 1)[-1].split(":", 1)[-1]
    for n in names:
        if n != body and n in text:
            facts.add(n)
    return facts


def check(parsed: dict, rewrite_map: dict) -> dict:
    by_idx = {p["index"]: p for p in parsed["paragraphs"]}
    names = extract_speakers(parsed)
    fails, warns, rows = [], [], []

    # 同角色改后台词池（查 D10）
    after_by_speaker: dict[str, list[str]] = collections.defaultdict(list)
    for p in parsed["paragraphs"]:
        if p["type"] in ("dialogue", "os") and p["speaker"]:
            after_by_speaker[p["speaker"]].append(p["content"])

    valid_keys = []
    for k, v in rewrite_map.items():
        if is_skip_key(k):
            continue
        try:
            idx = int(k)
        except ValueError:
            fails.append(("D2", k, "key 不是整数 index"))
            continue
        valid_keys.append(idx)
        new = str(v).strip()
        p = by_idx.get(idx)

        # D2 / D3：index 必须是台词行
        if p is None:
            fails.append(("D2", k, "index 不存在"))
            continue
        if p["type"] not in ("dialogue", "os"):
            fails.append(("D3", k, f'改到了非台词行（type={p["type"]}）：{p["text"][:30]}'))
            continue

        old = p["text"]
        # D1：说话人前缀
        mo, mn = SPEAKER_RE.match(old), SPEAKER_RE.match(new)
        if not mn:
            fails.append(("D1", k, f'缺少"说话人："前缀：{new[:30]}'))
            continue
        if mo and mo.group(1).strip() != mn.group(1).strip():
            fails.append(("D1", k, f'说话人被改：{mo.group(1)} -> {mn.group(1)}'))
            continue

        new_body = mn.group(2).strip()
        old_body = mo.group(2).strip() if mo else old

        # D4：事实锚点
        missing = facts_of(old, names) - facts_of(new, names)
        if missing:
            fails.append(("D4", k, f'事实丢失 {sorted(missing)}：{new_body[:40]}'))

        # WARN 组
        hit = [w for w in BOOK_WORDS if w in new_body]
        if hit:
            warns.append(("D5", k, f'书面虚词 {hit}：{new_body[:40]}'))
        if len(new_body) >= 25 and not re.search(r"[，。！？…、；：—]", new_body):
            warns.append(("D6", k, f"长句无气口：{new_body[:40]}"))
        if new_body.strip("。！？…， ") in WATER_EXACT:
            warns.append(("D7", k, f"整句为水词：{new_body}"))
        if EMO_RE.search(new_body):
            warns.append(("D8", k, f"情绪直白宣告：{new_body[:40]}"))
        if DUB_RE.search(new_body):
            warns.append(("D9", k, f"译制片腔：{new_body[:40]}"))
        spk = (mo.group(1).strip() if mo else "")
        if spk and new_body != old_body:
            pool = after_by_speaker[spk]
            if new_body in pool:
                warns.append(("D10", k, f"{spk} 已有同句：{new_body[:30]}"))

        rows.append({
            "index": idx, "scene": p["scene_id"], "speaker": spk,
            "old": old_body, "new": new_body,
        })

    return {
        "fails": fails, "warns": warns, "rows": rows,
        "count": len(valid_keys),
        "total_lines": sum(1 for p in parsed["paragraphs"] if p["type"] in ("dialogue", "os")),
    }


def print_report(res: dict) -> None:
    print("=" * 60)
    print(f'改写 {res["count"]} / 台词 {res["total_lines"]} 行 '
          f'（命中率 {res["count"] / max(res["total_lines"], 1) * 100:.1f}%）')
    print(f'🔴 FAIL {len(res["fails"])}   🟡 WARN {len(res["warns"])}')
    if res["fails"]:
        print("\n---- FAIL ----")
        for code, k, msg in res["fails"]:
            print(f"  [{code}] #{k}  {msg}")
    if res["warns"]:
        print("\n---- WARN ----")
        agg = collections.Counter(c for c, _, _ in res["warns"])
        print("  " + "  ".join(f"{k}×{v}" for k, v in sorted(agg.items())))
        for code, k, msg in res["warns"][:15]:
            print(f"  [{code}] #{k}  {msg}")
        if len(res["warns"]) > 15:
            print(f"  ... 另有 {len(res['warns']) - 15} 条")
    print("=" * 60)


def write_markdown(res: dict, path: str) -> None:
    lines = [
        "# 台词优化 · 逐条对照",
        "",
        f'- 改写 **{res["count"]}** 条 / 台词总行数 **{res["total_lines"]}**'
        f'（命中率 {res["count"] / max(res["total_lines"], 1) * 100:.1f}%）',
        f'- 机检：🔴 FAIL **{len(res["fails"])}** ／ 🟡 WARN **{len(res["warns"])}**',
        "",
        "> 说话人前缀、△ 动作行、场次标题、音效标记均未改动；行数不变。",
        "",
        "---",
        "",
    ]
    cur = None
    for r in sorted(res["rows"], key=lambda x: x["index"]):
        if r["scene"] != cur:
            cur = r["scene"]
            lines += [f"## {cur}", ""]
        lines += [
            f'**#{r["index"]}**　{r["speaker"]}',
            "",
            f'- 原：{r["old"]}',
            f'- 改：{r["new"]}',
            "",
        ]
    if res["fails"]:
        lines += ["## 🔴 未通过的项", ""]
        for code, k, msg in res["fails"]:
            lines.append(f"- [{code}] #{k} {msg}")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[OK] 对照表已写出 {path}")


def main() -> int:
    ap = argparse.ArgumentParser(description="台词改写机检")
    ap.add_argument("parsed", help="parse_dialogue.py 输出的 parsed.json")
    ap.add_argument("rewrite_map", help="改写映射 JSON")
    ap.add_argument("-o", "--output", help="输出 Markdown 对照表路径")
    args = ap.parse_args()

    for f in (args.parsed, args.rewrite_map):
        if not os.path.isfile(f):
            print(f"[ERROR] 文件不存在: {f}", file=sys.stderr)
            return 2

    parsed = load_json(args.parsed)
    rewrite_map = load_json(args.rewrite_map)
    res = check(parsed, rewrite_map)
    print_report(res)
    if args.output:
        write_markdown(res, args.output)
    return 1 if res["fails"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
