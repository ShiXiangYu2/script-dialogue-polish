#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把台词改写结果落盘为新 docx（纯标准库）

原理：复制原 docx 的 zip 条目，仅替换 word/document.xml 中目标 <w:p> 段落内
      <w:t> 的文字，其余 XML 字节完全不动 -> 样式/页码/字体/图片/动作行 100% 保留。

落盘前做两道安全校验（不通过直接拒绝写入）：
  1. 所有 index 必须指向台词行（dialogue / os），不许碰 △ 行、场次标题、音效标记
  2. 新文本的「说话人：」前缀必须与原文完全一致

用法:
    python3 apply_dialogue.py "剧本.docx" "rewrite_map.json" "剧本_台词优化稿.docx"
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_dialogue import (  # noqa: E402
    PARA_RE, TEXT_RE, read_document_xml, iter_paragraph_blocks, classify,
)

T_OPEN_RE = re.compile(r"<w:t(?:\s[^>]*)?>")
SPEAKER_RE = re.compile(r"^([^\s：:]{1,12})\s*[:：]", re.S)


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def rewrite_paragraph_block(block: str, new_text: str) -> str:
    """把段落内第一个 <w:t> 换成 new_text，其余 <w:t> 置空（保留 run/格式）"""
    matches = list(TEXT_RE.finditer(block))
    if not matches:
        return block
    out, last = [], 0
    escaped = _escape(new_text)
    for i, m in enumerate(matches):
        out.append(block[last:m.start(1)])
        out.append(escaped if i == 0 else "")
        last = m.end(1)
    out.append(block[last:])
    result = "".join(out)
    if new_text != new_text.strip():
        def fix(m):
            tag = m.group(0)
            return tag if "xml:space" in tag else tag[:-1] + ' xml:space="preserve">'
        result = T_OPEN_RE.sub(fix, result, count=1)
    return result


def apply(src: str, map_path: str, dst: str) -> dict:
    if os.path.abspath(src) == os.path.abspath(dst):
        raise RuntimeError("输出路径与原件相同，拒绝覆盖原件。请换一个新文件名。")

    with open(map_path, "r", encoding="utf-8") as f:
        rewrite_map = json.load(f)
    rewrite_map = {int(k): str(v) for k, v in rewrite_map.items()
                   if not str(k).startswith("_")}

    xml_text = read_document_xml(src)
    blocks = list(iter_paragraph_blocks(xml_text))

    # —— 落盘前安全校验 ——
    bad_type, bad_prefix = [], []
    for idx, new_text in rewrite_map.items():
        if idx >= len(blocks):
            bad_type.append((idx, "index 越界"))
            continue
        old_text = blocks[idx][4]
        typ = classify(old_text)
        if typ not in ("dialogue", "os"):
            bad_type.append((idx, f"非台词行({typ}): {old_text[:24]}"))
            continue
        mo, mn = SPEAKER_RE.match(old_text), SPEAKER_RE.match(new_text.strip())
        if not mn:
            bad_prefix.append((idx, "新文本缺少说话人前缀"))
        elif mo and mo.group(1).strip() != mn.group(1).strip():
            bad_prefix.append((idx, f"{mo.group(1)} -> {mn.group(1)}"))

    if bad_type:
        raise RuntimeError(f"含非台词行 index，拒绝写入：{bad_type[:5]}")
    if bad_prefix:
        raise RuntimeError(f"说话人前缀被改动，拒绝写入：{bad_prefix[:5]}")

    # —— 原位替换 ——
    parts, cursor, replaced = [], 0, 0
    for idx, new_text in sorted(rewrite_map.items()):
        _i, start, end, block, _old = blocks[idx]
        parts.append(xml_text[cursor:start])
        parts.append(rewrite_paragraph_block(block, new_text.strip()))
        cursor = end
        replaced += 1
    parts.append(xml_text[cursor:])
    new_xml = "".join(parts)

    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                data = new_xml.encode("utf-8")
            zout.writestr(item, data)

    return {"output": os.path.abspath(dst), "replaced": replaced}


def verify(src: str, dst: str, map_path: str) -> dict:
    """回读验证：段落数不变 / 改动数=映射数 / 非台词行零改动 / 台词行数不变"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from parse_dialogue import build
    a = build(src)["paragraphs"]
    b = build(dst)["paragraphs"]
    with open(map_path, encoding="utf-8") as f:
        m = {int(k) for k in json.load(f) if not str(k).startswith("_")}
    changed = {x["index"] for x, y in zip(a, b) if x["text"] != y["text"]}
    return {
        "paragraphs_same": len(a) == len(b),
        "changed": len(changed),
        "mapped": len(m),
        "changed_equals_mapped": changed == m,
        "non_line_changed": len([i for i in changed
                                 if a[i]["type"] not in ("dialogue", "os")]),
        "lines_old": sum(1 for p in a if p["type"] in ("dialogue", "os")),
        "lines_new": sum(1 for p in b if p["type"] in ("dialogue", "os")),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="落盘台词改写为新 docx（不覆盖原件）")
    ap.add_argument("docx", help="原始剧本 docx")
    ap.add_argument("map", help="rewrite_map.json")
    ap.add_argument("output", help="输出的新 docx 路径")
    args = ap.parse_args()

    for p in (args.docx, args.map):
        if not os.path.isfile(p):
            print(f"[ERROR] 文件不存在: {p}", file=sys.stderr)
            return 2

    try:
        r = apply(args.docx, args.map, args.output)
    except Exception as e:
        print(f"[FAIL] {e}", file=sys.stderr)
        return 1

    print(f"[OK] 已生成 {r['output']}")
    print(f"  改写台词: {r['replaced']} 条 | 其余内容字节级保持不变")

    v = verify(args.docx, args.output, args.map)
    print("\n---- 回读验证 ----")
    print(f"  段落数不变          {'✅' if v['paragraphs_same'] else '❌'}")
    print(f"  改动数 = 映射数      {'✅' if v['changed_equals_mapped'] else '❌'}"
          f"（{v['changed']} / {v['mapped']}）")
    print(f"  非台词行零改动       {'✅' if v['non_line_changed'] == 0 else '❌'}"
          f"（{v['non_line_changed']} 处）")
    print(f"  台词行数不变         {'✅' if v['lines_old'] == v['lines_new'] else '❌'}"
          f"（{v['lines_old']} / {v['lines_new']}）")
    ok = (v["paragraphs_same"] and v["changed_equals_mapped"]
          and v["non_line_changed"] == 0 and v["lines_old"] == v["lines_new"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
