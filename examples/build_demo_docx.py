#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成示例剧本 examples/demo_episode.docx（纯标准库，无需 python-docx）

用法:
    python3 examples/build_demo_docx.py

产出:
    examples/demo_episode.docx   一个 5 场的迷你剧本（虚构），可直接跑完整四步工作流

说明: 这是一个「最小合法 docx」的构造器，只用于造 demo，不是工作流的一部分。
     剧本《末班车》为虚构作品，人物、情节、数字均属虚构。
"""
from __future__ import annotations

import os
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "demo_episode.docx")

CT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""

DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults>
  <w:rPrDefault><w:rPr>
    <w:rFonts w:ascii="Microsoft YaHei" w:eastAsia="Microsoft YaHei" w:hAnsi="Microsoft YaHei"/>
    <w:sz w:val="22"/><w:szCs w:val="22"/>
  </w:rPr></w:rPrDefault>
  <w:pPrDefault><w:pPr><w:spacing w:line="320" w:lineRule="auto"/></w:pPr></w:pPrDefault>
</w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Heading1">
  <w:name w:val="heading 1"/><w:basedOn w:val="Normal"/>
  <w:pPr><w:spacing w:before="240" w:after="120"/><w:outlineLvl w:val="0"/></w:pPr>
  <w:rPr><w:b/><w:sz w:val="28"/><w:szCs w:val="28"/></w:rPr>
</w:style>
</w:styles>"""

CORE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<dc:title>示例剧本 末班车（虚构）</dc:title>
<dc:creator>script-dialogue-polish</dc:creator>
<cp:lastModifiedBy>script-dialogue-polish</cp:lastModifiedBy>
</cp:coreProperties>"""

APP = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
 xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
<Application>script-dialogue-polish</Application>
</Properties>"""

# 虚构剧本《末班车》· 第7集：1995 年，北方县城长途汽车站
# 全部为虚构内容。刻意埋入九类病灶，用于演示诊断与改写
# （水词 / 复述 / 堆词 / 流水账 / 书面腔 / 译制片腔 / 端着的总结句 / 说明式交代）。
SCRIPT = [
    ("episode", "第7集《末班车》"),

    ("scene", "第一场：售票厅・日・内"),
    ("action", "△ 周小满把一沓票根摊在售票窗口的台面上，一张一张对着数。"),
    ("dialogue", "周小满：十七块八。"),
    ("dialogue", "阿亮：姐，你数几遍了？"),
    ("dialogue", "周小满：三遍。差四块二。"),
    ("dialogue", "阿亮：哦。"),
    ("action", "△ 周小满把票根往台面上一推。"),
    ("dialogue", "周小满：把上午的票根拿来。"),
    ("dialogue", "阿亮：上午的票根？"),
    ("dialogue", "周小满：十点那趟的。"),
    ("action", "△ 阿亮蹲下去翻抽屉，翻到一半停住，抬头看她。"),
    ("os", "阿亮os：这一摊子事跟乱麻似的，我心里说不清是什么滋味。"),
    ("action", "△ 抽屉里翻出一把旧票夹，铁皮边卷了。"),

    ("scene", "第二场：站台・日・外"),
    ("action", "△ 王秀兰端着个铝盆从站门口进来，盆里泡着两只碗。"),
    ("dialogue", "王秀兰：小满！上个月你在我家吃了十二顿饭，钱呢！"),
    ("dialogue", "周小满：王婶，我记着。"),
    ("dialogue", "王秀兰：你记着？我那本子上记得比你清楚！"),
    ("action", "△ 马德胜从候车室出来，站在台阶上，手插在裤兜里。"),
    ("dialogue", "马德胜：秀兰，站上的事站上管。饭钱你们私下算。"),
    ("dialogue", "王秀兰：私下算？他爹欠的那笔，也是私下算的？"),
    ("dialogue", "周小满：王婶，先说票的事。饭钱我月底给。"),
    ("dialogue", "阿亮：我哪知道啊。"),
    ("dialogue", "王秀兰：你别插嘴！"),
    ("action", "△ 王秀兰把铝盆往台子上一放，水泼出来一半。"),

    ("scene", "第三场：修理间・日・内"),
    ("action", "△ 陈守义躺在车底下，只露出两只脚和一只手。"),
    ("dialogue", "陈守义：扳手。"),
    ("dialogue", "周小满：哪个？"),
    ("dialogue", "陈守义：十二的。"),
    ("action", "△ 周小满把扳手递进去，铁碰铁响了一声。"),
    ("dialogue", "周小满：陈师傅，上午那趟，你验过没有。"),
    ("dialogue", "陈守义：验过。"),
    ("dialogue", "周小满：刹车呢。"),
    ("dialogue", "陈守义：没动过。"),
    ("dialogue", "周小满：我需要你给我出一份证明，说明这辆车的刹车在今天上午十点之前是完好的。"),
    ("action", "△ 陈守义从车底滑出来，坐起来，拿袖子擦手。"),
    ("dialogue", "陈守义：写不了。"),
    ("dialogue", "周小满：为什么。"),
    ("dialogue", "陈守义：我只管修。谁开的车，谁签的字。"),
    ("action", "△ 周小满站着没走。"),
    ("os", "周小满os：我以为他会点头。他没抬头。往后的路，得自己一步一步踩出来。"),
    ("dialogue", "阿亮：我去拿抹布。"),

    ("scene", "第四场：站长办公室・昏・内"),
    ("action", "△ 马德胜把茶杯盖扣上，抬眼看她。"),
    ("dialogue", "马德胜：小满，四块二，不是大事。你补上，这事就过去了。"),
    ("dialogue", "周小满：补上？那就等于是我拿的。"),
    ("dialogue", "马德胜：没人说你拿的。年轻人，工作上有疏忽，谁都难免。"),
    ("dialogue", "马德胜：这个事，我们要研究一下。"),
    ("dialogue", "周小满：站长，我要求核查上午的售票记录。"),
    ("dialogue", "马德胜：查可以。不过你想清楚，查完了，你在这个站还待不待。"),
    ("dialogue", "周小满：我要是现在认了，才真待不下去。"),
    ("action", "△ 马德胜没说话，把茶杯推到桌角。"),
    ("dialogue", "马德胜：你先回去吧。"),
    ("dialogue", "周小满：我就在这儿等。"),

    ("scene", "第五场：售票厅・夜・内"),
    ("action", "△ 赵科长把公文包放在窗台上，抽出一张表格。"),
    ("dialogue", "赵科长：周小满同志，我们接到反映，来核一下上午的票。"),
    ("dialogue", "周小满：票根在抽屉里，一张不少。"),
    ("dialogue", "赵科长：十点那趟，你卖了多少张。"),
    ("dialogue", "周小满：四十一张。收的钱，十七块八。"),
    ("dialogue", "赵科长：记录上是三十九张。"),
    ("dialogue", "周小满：那就有两张票，没上记录，钱也没进账。"),
    ("dialogue", "赵科长：你这话，是在说谁？"),
    ("dialogue", "周小满：我说的是账。您问的是人。"),
    ("action", "△ 门口有人接话。陈守义站在门框边上，手里还捏着那块擦手的棉纱。"),
    ("dialogue", "陈守义：车是我验的。签字的是他。"),
]


def esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def para(kind: str, text: str) -> str:
    ppr = '<w:pPr><w:pStyle w:val="Heading1"/></w:pPr>' if kind in ("scene", "episode") else ""
    return (
        "<w:p>" + ppr +
        '<w:r><w:rPr><w:rFonts w:hint="eastAsia"/></w:rPr>'
        f'<w:t xml:space="preserve">{esc(text)}</w:t></w:r></w:p>'
    )


def build() -> str:
    body = "".join(para(k, t) for k, t in SCRIPT)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}"
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr>'
        "</w:body></w:document>"
    )


def main() -> int:
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CT)
        z.writestr("_rels/.rels", RELS)
        z.writestr("docProps/core.xml", CORE)
        z.writestr("docProps/app.xml", APP)
        z.writestr("word/_rels/document.xml.rels", DOC_RELS)
        z.writestr("word/styles.xml", STYLES)
        z.writestr("word/document.xml", build())
    print(f"[OK] 已生成 {OUT}")
    print(f"  {len(SCRIPT)} 段 / {sum(1 for k, _ in SCRIPT if k == 'scene')} 场")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
