#!/usr/bin/env python3
"""v7: Nothing Design — OLED black, Doto giant hero, dashboard topbar, red as 4 interrupts only."""
import json, html, math
from pathlib import Path

OUT = Path.home() / ".openclaw/workspace/projects/fastpublish-analysis"
V = "v8"
data = json.load(open(OUT/"result.json"))
contributors = [c for c in data["contributors"] if c["commits"] >= 1 and c["name"] != "PM Agent (bot)"]
skills = [s for s in data["skills"] if not s["name"].startswith("_template")]

ROLES = {
  "Charles Liu (wei.liu)": {
    "role":"架构 · ARCHITECT",
    "verdict":"skill 体系的单点支柱。Top 10 里 7 个都是他主笔。",
    "highlights":[
      "15 个 skill 主笔，data-monitor / weekly-report / specific-analysis 三件套 22/25",
      "50 个 knowledge 文件，跨度 14 天最长",
      "三件套已被周报/告警/归因三条业务线串起来",
    ],
    "gaps":[
      "skill-evolution 结构完整但零引用，疑似实验未上",
      "bus factor = 1，他停手项目立刻减速",
    ],
    "tags":["架构","全栈主笔","高引用"],
    "grade":"A","span":True,
  },
  "Huang Yu (DeeDee)": {
    "role":"内容 · CONTENT",
    "verdict":"把游戏内容知识库从零填到 26 个文件，commits 数最高。",
    "highlights":["26 个 knowledge/game 文件","issue-tracker tool station 原型也是他起的（14k 行）"],
    "gaps":["工具化产出 = 1 个 skill；文档为主","10 天集中产出后未持续"],
    "tags":["策划知识","高产","文档型"],
    "grade":"B+",
  },
  "Peicheng Zheng": {
    "role":"集成 · INTEGRATOR",
    "verdict":"净增 51.8 万行的真相：91% 是 Confluence wiki 一键搬家。",
    "highlights":["Confluence wiki 自动同步脚本（PowerShell 三件套）","sensor-tower / version-release 是有效原创 skill"],
    "gaps":["代码量看似最高但折算后排倒数","原创 skill 仅 2 个"],
    "tags":["集成","归档","wiki 同步"],
    "grade":"B",
  },
  "Pingfan": {
    "role":"基建 · INFRA",
    "verdict":"8 个 skill 全在做 agent 自身能力（meta-skills）。",
    "highlights":["agent-browser 进 Top 5（21/25）","结构/复用维度普遍 4-5 分，文档规范最严格"],
    "gaps":["find-skills / skill-vetter / codex-oauth 文档引用为 0","做的是 agent 自用，业务侧价值难显化"],
    "tags":["基建","高规范","META"],
    "grade":"B+",
  },
  "Chenchen Zhang (张鱼哥)": {
    "role":"PM · OWNER",
    "verdict":"定方向、立框架，亲手把 event_analysis 从 10/25 提到 23/25。",
    "highlights":["AGENTS.md / 多 Agent 设计 / FGD 报告等框架性输出","演示了按维度对症提分的方法论可复用"],
    "gaps":["活跃天数 5 天，主要在前期与最近一次冲刺","初版 event_analysis 缺脚本/模板（后已修复）"],
    "tags":["PM","设计者","验收方"],
    "grade":"B-",
  },
  "Zhang Yaokuang": {
    "role":"短促 · DRIVE-BY",
    "verdict":"2 天内交付 9 个 knowledge 文件后离场。",
    "highlights":["Malaysia marketing docs + selling point extractor playbook"],
    "gaps":["未触及 skill 体系","未持续参与"],
    "tags":["内容","短促"],
    "grade":"C+",
  },
}

contributors.sort(key=lambda c: (-c["skills_authored"], -c["avg_skill_quality"] if c["avg_skill_quality"] else 0))

def esc(s): return html.escape(str(s))

# ===== Aggregate stats =====
total_commits = data["total_commits"]
total_skills_ct = len(skills)
zero_ref_ct = sum(1 for s in skills if s["refs"]==0)

# ===== Skill 主笔分布: 每人一条横向条 =====
total_sk_main = sum(c["skills_authored"] for c in contributors) or 1
dist_list = sorted([(c["name"], c["skills_authored"]) for c in contributors], key=lambda x: -x[1])
max_sk = dist_list[0][1] if dist_list else 1
dist_html = '<div class="distbars">'
for i,(name, n) in enumerate(dist_list):
    pct = n/total_sk_main*100
    bw = int(n/max_sk*100)
    op = 1.0 - i*0.13
    op = max(0.30, op)
    short = name.split(" (")[0]
    extra = name.split("(",1)[1].rstrip(")") if "(" in name else ""
    dist_html += f'''
    <div class="distrow">
      <div class="distname"><b>{esc(short)}</b>{('<span class="distextra">'+esc(extra)+'</span>') if extra else ''}</div>
      <div class="disttrack">
        <div class="distbar" style="width:{bw}%;opacity:{op:.2f}">
          <span class="distnum">{n} 个 skill</span>
        </div>
      </div>
      <div class="distpct">{pct:.0f}%</div>
    </div>'''
dist_html += '</div>'
dist_html += f'<div class="distfoot"><span>主笔 skill 数 ÷ 全员主笔总数 {total_sk_main} = 占比</span><span>29 个 skill 中 {total_sk_main} 个有明确主笔</span></div>'


# ===== Heatmap (mono, white density on black) =====
all_days = sorted({dt for c in contributors for dt in c.get("daily",{}).keys()})
CELL_W = 14; CELL_H = 18; LABEL_W = 160; ROW_GAP = 4
max_churn = 0
for c in contributors:
    for dt, v in c.get("daily",{}).items():
        if v["churn"] > max_churn: max_churn = v["churn"]
def alpha(churn):
    if churn <= 0: return 0
    return max(0.18, min(1.0, math.log10(churn+1)/math.log10(max_churn+1)))

svg_h = (CELL_H + ROW_GAP) * len(contributors) + 56
svg_w = LABEL_W + len(all_days) * CELL_W + 20
hm = [f'<svg width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}" xmlns="http://www.w3.org/2000/svg" font-family="Space Mono, monospace">']
for i, d in enumerate(all_days):
    if i % 5 == 0:
        x = LABEL_W + i * CELL_W
        hm.append(f'<text x="{x}" y="14" font-size="9" fill="#666" letter-spacing="0.5">{d[5:]}</text>')
for ri, c in enumerate(contributors):
    y = 26 + ri * (CELL_H + ROW_GAP)
    short = c["name"].split(" (")[0].upper()
    hm.append(f'<text x="{LABEL_W-10}" y="{y+CELL_H/2+4}" font-size="10" text-anchor="end" fill="#E8E8E8" font-weight="400" letter-spacing="0.5">{esc(short)}</text>')
    for i, d in enumerate(all_days):
        x = LABEL_W + i * CELL_W
        info = c.get("daily",{}).get(d)
        if info:
            a = alpha(info["churn"])
            fill = f"rgba(255,255,255,{a:.2f})"
            t = f"{d}: {info['commits']} commits, {info['churn']:,} churn"
            hm.append(f'<rect x="{x}" y="{y}" width="{CELL_W-2}" height="{CELL_H}" fill="{fill}"><title>{t}</title></rect>')
        else:
            hm.append(f'<rect x="{x}" y="{y}" width="{CELL_W-2}" height="{CELL_H}" fill="none" stroke="#222" stroke-width="1"/>')
hm.append(f'<text x="{LABEL_W}" y="{svg_h-12}" font-size="9" fill="#666" letter-spacing="0.8">[ DENSITY = LOG(CHURN) ]</text>')
hm.append('</svg>')
heatmap_svg = "".join(hm)

# ===== Cards =====
def commits_block(name):
    c = next((x for x in contributors if x["name"]==name), None)
    if not c: return ""
    items = c.get("top_commits",[])[:3]
    if not items: return ""
    rows = ""
    for i, t in enumerate(items, 1):
        rows += f"""
        <li>
          <span class="cidx">[{i:02d}]</span>
          <span class="csubj">{esc(t["subject"])}</span>
          <div class="cmeta">{esc(t["sha"])} · {esc(t["date"])} · {t["churn"]:,} 行 · {t["files"]} 个文件</div>
        </li>"""
    return f'<div class="commits"><div class="lbl">代表性 COMMIT</div><ol>{rows}</ol></div>'

cards_html = ""
for i, c in enumerate(contributors):
    card = ROLES.get(c["name"])
    if not card: continue
    g = card["grade"]
    short = c["name"].split(" (")[0]
    extra = c["name"].split("(",1)[1].rstrip(")") if "(" in c["name"] else ""
    highlights = "".join(f"<li><span class='hi-mark'>+</span>{esc(h)}</li>" for h in card["highlights"]) or "<li>—</li>"
    gaps = "".join(f"<li><span class='ga-mark'>−</span>{esc(g_)}</li>" for g_ in card["gaps"]) or "<li>—</li>"
    tags = "".join(f'<span class="tag">{esc(t).upper()}</span>' for t in card["tags"])
    span_cls = " span2" if card.get("span") else ""
    # Bus factor warning red for Charles
    extra_warn = ""
    if c["name"].startswith("Charles"):
        extra_warn = '<div class="warn-row"><span class="dot-red"></span><span class="warn-txt">BUS FACTOR <b>= 1</b> · 单点保有风险</span></div>'
    cards_html += f"""
    <article class="card{span_cls}">
      <header class="chead">
        <div>
          <div class="lbl">{esc(card["role"])}　·　[{i+1:02d}/06]</div>
          <h3>{esc(short)}</h3>
          <div class="sub">{esc(extra) if extra else "&nbsp;"}</div>
        </div>
        <div class="cgrade">
          <div class="ghuge">{g}</div>
          <div class="lbl">评级</div>
        </div>
      </header>
      <p class="verdict">{esc(card["verdict"])}</p>
      <div class="cmetrics">
        <div><div class="big">{c['commits']:02d}</div><div class="lbl">提交</div></div>
        <div><div class="big">{c['skills_authored']:02d}</div><div class="lbl">主笔 SKILLS</div></div>
        <div><div class="big">{c['knowledge_files']:02d}</div><div class="lbl">知识文档</div></div>
        <div><div class="big">{c['active_days']:02d}</div><div class="lbl">活跃天数</div></div>
        <div><div class="big">{c['avg_skill_quality'] or '—'}</div><div class="lbl">平均分</div></div>
      </div>
      {extra_warn}
      <div class="ccols">
        <div class="col">
          <div class="lbl">亮点</div>
          <ul>{highlights}</ul>
        </div>
        <div class="col">
          <div class="lbl">短板</div>
          <ul>{gaps}</ul>
        </div>
      </div>
      {commits_block(c["name"])}
      <footer class="cfoot">{tags}</footer>
    </article>"""

# ===== Bars (white) =====
def bar(val, mx, w=110):
    if mx <= 0: return ""
    width = max(2, int(abs(val)/mx*w))
    return f'<span class="bar" style="width:{width}px"></span>'

max_commits = max(c["commits"] for c in contributors)
max_net     = max(abs(c["net"]) for c in contributors)
max_skills  = max(c["skills_authored"] for c in contributors) or 1
max_know    = max(c["knowledge_files"] for c in contributors) or 1
max_quality = max(c["avg_skill_quality"] or 0 for c in contributors) or 1
max_days    = max(c["active_days"] for c in contributors)

def status_dot(q):
    if q is None or q == 0: return '<span class="sd sd-off"></span>'
    if q >= 18: return '<span class="sd sd-on"></span>'
    if q >= 15: return '<span class="sd sd-mid"></span>'
    return '<span class="sd sd-low"></span>'

rows_bar = ""
for c in contributors:
    short = c["name"].split(" (")[0].upper()
    rows_bar += f"""
    <tr>
      <td>{status_dot(c["avg_skill_quality"])}</td>
      <td class="nm">{esc(short)}</td>
      <td><div class="bc">{bar(c["commits"], max_commits)}<span>{c["commits"]:03d}</span></div></td>
      <td><div class="bc">{bar(c["net"], max_net)}<span>{c["net"]:,}</span></div></td>
      <td><div class="bc">{bar(c["skills_authored"], max_skills)}<span>{c["skills_authored"]:02d}</span></div></td>
      <td><div class="bc">{bar(c["knowledge_files"], max_know)}<span>{c["knowledge_files"]:02d}</span></div></td>
      <td><div class="bc">{bar(c["active_days"], max_days)}<span>{c["active_days"]:02d}</span></div></td>
      <td><div class="bc">{bar(c["avg_skill_quality"] or 0, max_quality)}<span>{c["avg_skill_quality"] or "—"}</span></div></td>
    </tr>"""

skills_sorted = sorted(skills, key=lambda x: -x["total"])
rows_top = ""
for i, s in enumerate(skills_sorted[:10], 1):
    short = s["author"].split(" (")[0].upper()
    bw = int(s["total"]/25*100)
    rows_top += f"""
    <tr>
      <td>{status_dot(s["total"])}</td>
      <td class="rank">[{i:02d}]</td>
      <td class="nm">{esc(s["name"])}</td>
      <td class="auth">{esc(short)}</td>
      <td><div class="bc"><span class="bar" style="width:{bw}px"></span><span>{s["total"]:02d}/25</span></div></td>
    </tr>"""

zero_ref = sorted([s for s in skills if s["refs"]==0], key=lambda x: x["total"])
rows_zero = ""
for s in zero_ref:
    short = s["author"].split(" (")[0].upper()
    rows_zero += f"""
    <tr>
      <td><span class="sd sd-red"></span></td>
      <td class="nm">{esc(s["name"])}</td>
      <td class="auth">{esc(short)}</td>
      <td class="num">{s["structure"]}</td>
      <td class="num">{s["exec"]}</td>
      <td class="num">{s["fresh"]}</td>
      <td class="num total">{s["total"]:02d}/25</td>
    </tr>"""

html_out = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>FASTPUBLISH · REPO ANALYSIS</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="preconnect" href="https://fonts.loli.net" crossorigin>
<link rel="preconnect" href="https://fonts.gstatic.cn" crossorigin>
<link rel="stylesheet" href="https://fonts.loli.net/css2?family=Doto:wght@400;700;800;900&family=Space+Grotesk:wght@300;400;500;700&family=Space+Mono:wght@400;700&display=swap">
<style>
  :root{
    --bg:#000000; --surface:#0A0A0A; --raised:#111111;
    --border:#1F1F1F; --border-v:#2A2A2A;
    --t-disabled:#555; --t-secondary:#888; --t-primary:#E8E8E8; --t-display:#FFFFFF;
    --accent:#D71921; --success:#4A9E5C; --warning:#D4A843;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  html,body{background:var(--bg);color:var(--t-primary);font-family:'Space Grotesk','DM Sans',system-ui,sans-serif;font-weight:400;line-height:1.5;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}

  /* Dot pattern texture top-right */
  body{background-image:
    radial-gradient(circle at center, rgba(255,255,255,0.06) 1px, transparent 1px),
    linear-gradient(180deg, rgba(255,255,255,0.015) 0%, transparent 280px);
    background-size:18px 18px, 100% 100%;
    background-position:right -200px top -200px, 0 0;
    background-repeat:no-repeat, no-repeat;
    min-height:100vh;
  }

  /* ===== Topbar (dashboard) ===== */
  .topbar{position:sticky;top:0;z-index:50;background:var(--bg);border-bottom:1px solid var(--border);padding:14px 32px;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;font-family:'Space Mono',monospace;font-size:10px;letter-spacing:0.12em;text-transform:uppercase}
  .tb-l{display:flex;align-items:center;gap:10px;color:var(--t-display)}
  .tb-l .brand-dot{width:8px;height:8px;background:var(--accent);display:inline-block;border-radius:50%;animation:pulse 2s ease-in-out infinite}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}
  .tb-c{color:var(--t-secondary);display:flex;gap:32px}
  .tb-c a{color:var(--t-secondary);text-decoration:none}
  .tb-c a.active{color:var(--t-display)}
  .tb-r{justify-self:end;display:flex;align-items:center;gap:14px;color:var(--t-secondary)}
  .tb-live{background:var(--accent);color:#fff;padding:3px 7px;font-weight:700;letter-spacing:0.14em}

  /* ===== Layout ===== */
  .wrap{max-width:1240px;margin:0 auto;padding:64px 32px 96px}

  /* ===== Labels ===== */
  .lbl{font-family:'Space Mono',monospace;font-size:12px;font-weight:400;letter-spacing:0.12em;text-transform:uppercase;color:var(--t-secondary);line-height:1.4}

  /* ===== HERO — asymmetric, 8:4 ===== */
  .hero{display:grid;grid-template-columns:2fr 1fr;gap:64px;padding:48px 0 80px;align-items:end;border-bottom:1px solid var(--border)}
  .hero-l .lbl-top{margin-bottom:24px;color:var(--t-disabled);display:flex;align-items:center;gap:14px;flex-wrap:wrap}
  .hero-stamp{display:inline-flex;align-items:center;gap:8px;padding:5px 12px 5px 10px;background:var(--raised);border:1px solid var(--border-v);border-radius:0;font-family:'Space Mono',monospace;font-size:10.5px;letter-spacing:0.12em;color:var(--t-primary);text-transform:uppercase}
  .hero-stamp-dot{width:7px;height:7px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 0 var(--accent);animation:hsPulse 2s infinite}
  @keyframes hsPulse{0%{box-shadow:0 0 0 0 rgba(215,25,33,0.7)}70%{box-shadow:0 0 0 6px rgba(215,25,33,0)}100%{box-shadow:0 0 0 0 rgba(215,25,33,0)}}
  .hero-num{font-family:'Doto',monospace;font-weight:800;font-size:240px;line-height:0.85;letter-spacing:-0.04em;color:var(--t-display);margin-bottom:8px;display:flex;align-items:flex-end;gap:20px}
  .hero-num .unit{font-family:'Space Mono',monospace;font-size:11px;font-weight:400;letter-spacing:0.12em;color:var(--t-secondary);text-transform:uppercase;padding-bottom:24px;align-self:center;line-height:1.5}
  .hero-sub{font-family:'Space Grotesk','PingFang SC','Noto Sans CJK SC',sans-serif;font-size:19px;color:var(--t-primary);max-width:600px;line-height:1.6;margin-top:32px}
  .hero-sub b{color:var(--t-display);font-weight:500}

  .hero-r{display:flex;flex-direction:column;gap:28px;padding-bottom:12px;border-left:1px solid var(--border);padding-left:36px}
  .mstat .num{font-family:'Space Mono',monospace;font-size:40px;font-weight:400;color:var(--t-display);line-height:1;letter-spacing:-0.02em}
  .mstat .num small{font-family:'Space Mono',monospace;font-size:16px;color:var(--t-secondary);margin-left:4px}
  .mstat .lbl{margin-top:8px;font-size:11.5px}
  .mstat.alert .num{color:var(--accent)}
  .mstat.alert .lbl{color:var(--accent)}

  /* ===== Skill 主笔分布 section ===== */
  .seg-section{margin-top:80px;padding-top:56px;border-top:1px solid var(--border)}
  .seg-head{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:32px}
  .seg-head h2{font-family:'Space Grotesk','PingFang SC',sans-serif;font-size:28px;font-weight:500;color:var(--t-display);letter-spacing:-0.015em}
  .seg-head .lbl{color:var(--t-disabled);font-size:11px}
  .distbars{display:flex;flex-direction:column;gap:12px;margin-bottom:18px}
  .distrow{display:grid;grid-template-columns:220px 1fr 70px;gap:24px;align-items:center}
  .distname{font-family:'Space Grotesk','PingFang SC',sans-serif;font-size:17px;color:var(--t-display);text-align:right;line-height:1.2}
  .distname b{font-weight:500}
  .distextra{font-family:'Space Mono',monospace;font-size:11px;color:var(--t-disabled);letter-spacing:0.04em;display:block;margin-top:3px}
  .disttrack{height:42px;background:var(--raised);position:relative;border-left:1px solid var(--border-v)}
  .distbar{height:100%;background:var(--t-display);display:flex;align-items:center;padding:0 16px;min-width:130px}
  .distnum{font-family:'Space Mono',monospace;font-size:14px;font-weight:700;color:#000;letter-spacing:0.02em}
  .distpct{font-family:'Space Mono',monospace;font-size:22px;font-weight:400;color:var(--t-display);letter-spacing:-0.01em;text-align:right}
  .distfoot{display:flex;justify-content:space-between;font-family:'Space Mono',monospace;font-size:11.5px;color:var(--t-disabled);letter-spacing:0.04em;margin-top:18px;padding-top:14px;border-top:1px solid var(--border)}

  /* ===== Section header ===== */
  .sec{margin-top:96px}
  .sec-head{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:32px;padding-bottom:14px;border-bottom:1px solid var(--t-display)}
  .sec-head h2{font-family:'Space Grotesk','PingFang SC','Noto Sans CJK SC',sans-serif;font-size:28px;font-weight:500;letter-spacing:-0.015em;color:var(--t-display)}
  .sec-head .lbl{color:var(--t-secondary)}

  /* ===== Heatmap ===== */
  .hmwrap{background:var(--surface);border:1px solid var(--border);padding:32px;overflow-x:auto}

  /* ===== Cards ===== */
  .cards{display:grid;grid-template-columns:repeat(2,1fr);gap:24px}
  .card{background:var(--surface);border:1px solid var(--border);padding:28px 32px;display:flex;flex-direction:column}
  .card.span2{grid-column:1 / -1}
  .chead{display:flex;align-items:flex-start;justify-content:space-between;gap:24px;margin-bottom:18px;padding-bottom:20px;border-bottom:1px solid var(--border)}
  .chead h3{font-family:'Space Grotesk','PingFang SC',sans-serif;font-size:36px;font-weight:500;letter-spacing:-0.02em;color:var(--t-display);margin-top:10px;line-height:1.05}
  .chead .sub{font-family:'Space Mono',monospace;font-size:10px;color:var(--t-disabled);margin-top:6px;letter-spacing:0.06em;text-transform:uppercase}
  .cgrade{text-align:right;flex-shrink:0}
  .ghuge{font-family:'Doto',monospace;font-size:72px;font-weight:800;line-height:0.85;color:var(--t-display);letter-spacing:-0.04em;margin-bottom:8px}
  .verdict{font-family:'Space Grotesk','PingFang SC',sans-serif;font-size:17px;color:var(--t-primary);line-height:1.6;margin-bottom:24px}

  .cmetrics{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;padding:18px 0 24px;border-bottom:1px solid var(--border);margin-bottom:24px}
  .cmetrics .big{font-family:'Space Mono',monospace;font-size:28px;font-weight:400;color:var(--t-display);letter-spacing:-0.01em;line-height:1}
  .cmetrics .lbl{margin-top:8px;font-size:11px}

  .warn-row{display:flex;align-items:center;gap:10px;padding:10px 14px;background:rgba(215,25,33,0.08);border-left:2px solid var(--accent);margin-bottom:24px;font-family:'Space Mono',monospace;font-size:11px;letter-spacing:0.06em;text-transform:uppercase;color:var(--t-primary)}
  .dot-red{width:8px;height:8px;background:var(--accent);display:inline-block;border-radius:50%;animation:pulse 1.5s ease-in-out infinite}
  .warn-txt b{color:var(--accent);font-weight:700}

  .ccols{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-bottom:20px}
  .col .lbl{margin-bottom:12px}
  .col ul{list-style:none;padding:0}
  .col ul li{padding:10px 0;font-size:15px;line-height:1.55;color:var(--t-primary);border-top:1px solid var(--border);position:relative;padding-left:22px}
  .col ul li:first-child{border-top:none}
  .hi-mark,.ga-mark{font-family:'Space Mono',monospace;position:absolute;left:0;top:8px;font-weight:700;color:var(--t-secondary);font-size:14px}

  .commits{background:var(--raised);padding:18px 20px;margin-bottom:20px;border:1px solid var(--border)}
  .commits > .lbl{margin-bottom:12px}
  .commits ol{list-style:none;padding:0}
  .commits ol li{padding:10px 0;border-top:1px solid var(--border-v)}
  .commits ol li:first-child{border-top:none;padding-top:4px}
  .cidx{font-family:'Space Mono',monospace;font-size:10px;font-weight:700;color:var(--t-disabled);letter-spacing:0.06em;margin-right:10px}
  .csubj{font-family:'Space Grotesk','PingFang SC',sans-serif;font-size:15px;color:var(--t-display);font-weight:500}
  .cmeta{font-family:'Space Mono',monospace;font-size:11.5px;color:var(--t-secondary);letter-spacing:0.06em;text-transform:uppercase;margin-top:4px;margin-left:36px}

  .cfoot{margin-top:auto;display:flex;flex-wrap:wrap;gap:6px;padding-top:18px;border-top:1px solid var(--border)}
  .tag{font-family:'Space Mono',monospace;font-size:11px;font-weight:400;letter-spacing:0.08em;text-transform:uppercase;color:var(--t-secondary);padding:5px 12px;border:1px solid var(--border-v)}

  /* ===== Tables ===== */
  table{width:100%;border-collapse:collapse;background:var(--surface);border:1px solid var(--border)}
  th{font-family:'Space Mono',monospace;text-align:left;font-weight:700;color:var(--t-display);font-size:12px;letter-spacing:0.1em;text-transform:uppercase;padding:18px 20px;border-bottom:1px solid var(--t-display)}
  td{padding:18px 20px;border-bottom:1px solid var(--border);font-size:15px;color:var(--t-primary);vertical-align:middle}
  tr:last-child td{border-bottom:none}
  td.nm{font-family:'Space Grotesk','PingFang SC',sans-serif;font-weight:500;color:var(--t-display);letter-spacing:0.02em;font-size:15px}
  td.auth{font-family:'Space Mono',monospace;font-size:12px;color:var(--t-secondary);letter-spacing:0.06em;text-transform:uppercase}
  td.num{text-align:right;font-family:'Space Mono',monospace;font-size:14px}
  td.rank{font-family:'Space Mono',monospace;color:var(--t-disabled);font-size:12px;letter-spacing:0.06em;width:56px}
  td.total{font-family:'Space Mono',monospace;font-weight:700;color:var(--t-display);font-size:15px}

  .sd{display:inline-block;width:10px;height:10px;border-radius:50%}
  .sd-on{background:var(--t-display)}
  .sd-mid{background:var(--t-secondary)}
  .sd-low{background:var(--t-disabled)}
  .sd-off{background:transparent;border:1px solid var(--t-disabled)}
  .sd-red{background:var(--accent)}

  .bc{display:flex;align-items:center;gap:12px}
  .bc .bar{height:5px;background:var(--t-display);min-width:2px;display:inline-block}
  .bc span{font-family:'Space Mono',monospace;font-size:13px;color:var(--t-primary);letter-spacing:0.04em}

  /* ===== Caveat (bottom, dashboard-style) ===== */
  .caveat{background:var(--surface);border:1px solid var(--border);padding:24px 32px;margin-top:48px}
  .caveat .lbl{margin-bottom:16px;color:var(--t-secondary)}
  .caveat ol{list-style:none;counter-reset:ca;padding:0}
  .caveat ol li{counter-increment:ca;padding:14px 0 14px 56px;position:relative;font-size:15.5px;line-height:1.65;color:var(--t-primary);border-top:1px solid var(--border)}
  .caveat ol li:first-child{border-top:none}
  .caveat ol li:before{content:"[" counter(ca,decimal-leading-zero) "]";position:absolute;left:0;top:11px;font-family:'Space Mono',monospace;font-size:10px;font-weight:400;color:var(--t-disabled);letter-spacing:0.08em}
  .caveat ol li b{color:var(--t-display);font-weight:500}

  /* ===== Findings ===== */
  .findings{display:grid;grid-template-columns:repeat(3,1fr);gap:0;background:var(--surface);border:1px solid var(--border)}
  .finding{padding:36px 28px;border-right:1px solid var(--border);position:relative}
  .finding:last-child{border-right:none}
  .finding .fn{font-family:'Doto',monospace;font-size:64px;font-weight:800;color:var(--t-disabled);line-height:0.9;margin-bottom:18px;letter-spacing:-0.04em}
  .finding h3{font-family:'Space Grotesk',sans-serif;font-size:18px;font-weight:500;line-height:1.3;color:var(--t-display);margin-bottom:14px;letter-spacing:-0.005em}
  .finding p{font-size:13px;line-height:1.65;color:var(--t-secondary)}
  .finding p b{color:var(--t-primary);font-weight:500}
  .finding.win{background:var(--raised)}
  .finding.win .fn{color:var(--accent)}
  .finding.win .arrow{display:inline-block;color:var(--accent);font-weight:700;font-family:'Space Mono',monospace}

  .followup{background:var(--surface);border:1px solid var(--border);padding:20px 28px;margin-top:0;border-top:none;font-family:'Space Mono',monospace;font-size:11px;letter-spacing:0.04em;color:var(--t-primary);display:flex;flex-wrap:wrap;gap:32px}
  .followup .lbl{color:var(--t-secondary);letter-spacing:0.1em}
  .followup .fu-item{display:flex;align-items:center;gap:10px}
  .followup .fu-num{font-family:'Doto',monospace;font-size:20px;font-weight:700;color:var(--t-display);letter-spacing:-0.02em}

  /* ===== Method ===== */
  .method{display:grid;grid-template-columns:repeat(3,1fr);gap:0;background:var(--surface);border:1px solid var(--border)}
  .method > div{padding:20px 26px;border-right:1px solid var(--border);border-bottom:1px solid var(--border)}
  .method > div:nth-child(3n){border-right:none}
  .method > div:nth-last-child(-n+3){border-bottom:none}
  .method .lbl{margin-bottom:8px}
  .method p{font-size:14.5px;line-height:1.6;color:var(--t-primary)}

  footer{margin-top:96px;padding-top:32px;border-top:1px solid var(--border);display:flex;justify-content:space-between;align-items:baseline;font-family:'Space Mono',monospace;font-size:12px;color:var(--t-disabled);letter-spacing:0.1em;text-transform:uppercase}
  footer .ver-red{color:var(--accent)}

  @media (max-width:900px){
    .wrap{padding:32px 16px}
    .hero{grid-template-columns:1fr;gap:32px}
    .hero-num{font-size:144px}
    .hero-r{border-left:none;padding-left:0;border-top:1px solid var(--border);padding-top:24px}
    .cards{grid-template-columns:1fr}
    .card.span2{grid-column:auto}
    .cmetrics{grid-template-columns:repeat(3,1fr)}
    .findings,.method{grid-template-columns:1fr}
    .finding,.method > div{border-right:none;border-bottom:1px solid var(--border)}
    .ccols{grid-template-columns:1fr}
    .topbar{padding:12px 16px;grid-template-columns:1fr auto;font-size:9px}
    .tb-c{display:none}
  }
</style></head><body>

<!-- DASHBOARD TOP BAR -->
<div class="topbar">
  <div class="tb-l"><span class="brand-dot"></span><span>FASTPUBLISH</span><span style="color:var(--t-disabled);margin-left:8px">/ 仓库画像</span></div>
  <div class="tb-c"><a class="active">[ 分析 ]</a><a>SKILLS</a><a>贡献者</a><a>历史</a></div>
  <div class="tb-r"><span class="tb-live">LIVE</span><span>2026.05.15</span><span style="color:var(--t-disabled)">·</span><span>00:08 GMT+8</span></div>
</div>

<div class="wrap">

<!-- HERO -->
<section class="hero">
  <div class="hero-l">
    <div class="lbl lbl-top">[ 内部 ] FASTPUBLISH 仓库画像 // 30 天 // 6 位贡献者 <span class="hero-stamp"><span class="hero-stamp-dot"></span>UPDATED @@STAMP@@</span></div>
    <div class="hero-num">@@COMMITS@@<span class="unit">提交总数</span></div>
    <div class="hero-sub">基于 git 全历史的贡献者画像。<b>看 commit 数会得出错误结论</b>，看净增行数也会，必须把产出类型拆开看。</div>
  </div>
  <div class="hero-r">
    <div class="mstat"><div class="num">@@NSKILLS@@<small>/29</small></div><div class="lbl">参与评分 SKILLS</div></div>
    <div class="mstat"><div class="num">06</div><div class="lbl">贡献者数</div></div>
    <div class="mstat"><div class="num">30D</div><div class="lbl">采样窗口</div></div>
    <div class="mstat alert"><div class="num">@@ZERO@@</div><div class="lbl">● 零引用 SKILLS</div></div>
  </div>
</section>

<!-- SEGMENTED BAR: skill authorship distribution -->
<section class="seg-section">
  <div class="seg-head">
    <h2>Skill 主笔分布</h2>
    <div class="lbl">[ 横向条 = 该贡献者主笔的 skill 数占比 ]</div>
  </div>
  @@DIST@@
</section>

<!-- HEATMAP -->
<section class="sec">
  <div class="sec-head"><h2>时间序列</h2><div class="lbl">[ 01 ] 每日 churn / 30 天</div></div>
  <div class="hmwrap">@@HEATMAP@@</div>
</section>

<!-- CARDS -->
<section class="sec">
  <div class="sec-head"><h2>贡献者画像</h2><div class="lbl">[ 02 ] 画像 · 评级 · 代表 commit</div></div>
  <div class="cards">@@CARDS@@</div>
</section>

<!-- RAW DATA -->
<section class="sec">
  <div class="sec-head"><h2>原始数据</h2><div class="lbl">[ 03 ] 每列按最大值归一化</div></div>
  <table>
    <thead><tr>
      <th style="width:36px"></th><th>贡献者</th><th>提交</th><th>净增行</th><th>主笔技能</th><th>知识文档</th><th>活跃天数</th><th>平均分</th>
    </tr></thead>
    <tbody>@@ROWS_BAR@@</tbody>
  </table>
</section>

<!-- TOP SKILLS -->
<section class="sec">
  <div class="sec-head"><h2>核心技能 Top 10</h2><div class="lbl">[ 04 ] 按质量分排序</div></div>
  <table>
    <thead><tr><th style="width:36px"></th><th style="width:56px">#</th><th>技能名称</th><th>主笔</th><th>分数</th></tr></thead>
    <tbody>@@ROWS_TOP@@</tbody>
  </table>
</section>

<!-- ZERO REF -->
<section class="sec">
  <div class="sec-head"><h2>零引用技能</h2><div class="lbl">[ 05 ] ● 待跟进项</div></div>
  <table>
    <thead><tr><th style="width:36px"></th><th>技能名称</th><th>主笔</th><th>结构</th><th>可执行</th><th>时效</th><th>总分</th></tr></thead>
    <tbody>@@ROWS_ZERO@@</tbody>
  </table>
</section>



<!-- CAVEAT (moved to bottom) -->
<section class="sec">
  <div class="sec-head"><h2>方法局限</h2><div class="lbl">[ 06 ] 阅读前请知悉</div></div>
  <div class="caveat">
    <div class="lbl">声明</div>
    <ol>
      <li><b>分数不是全部。</b>「结构 / 复用 / 可执行」是数文件和章节，「引用率」是 grep 文档，不等于实际调用价值。</li>
      <li><b>commit 数 ≠ 价值。</b>文档型和重构型都算 1 次，必须结合代表性 commit 判断。</li>
      <li><b>bus factor 判断是定性。</b>基于 Top10 占比，不是基于停手实验。</li>
      <li><b>没有 PR / review 数据。</b>看不到代码审查、退回、协作密度。</li>
    </ol>
  </div>
</section>

<!-- METHOD -->
<section class="sec">
  <div class="sec-head"><h2>方法说明</h2><div class="lbl">[ 07 ] 评分细则</div></div>
  <div class="method">
    <div><div class="lbl">身份合并</div><p>wei.liu / liuwei / charlesliu66 → Charles；pingfan / shadow → Pingfan。</p></div>
    <div><div class="lbl">噪音排除</div><p>lock 文件、构建产物、二进制资源不计入行数。</p></div>
    <div><div class="lbl">主笔判定</div><p>该 skill 目录下累计提交行数最多的人，而非首次创建者。</p></div>
    <div><div class="lbl">质量五维</div><p>结构 / 复用 / 可执行 / 引用率 / 时效，每项 1-5，总 25。</p></div>
    <div><div class="lbl">评级</div><p>综合五维 + 角色定位主观加权得出 A/B/C；不作绩效评估。</p></div>
    <div><div class="lbl">可复现</div><p>analyze.py + build_html_v8.py · source: result.json</p></div>
  </div>
</section>

<footer>
  <div>● FASTPUBLISH · 仓库画像</div>
  <div>VER <span class="ver-red">8.0</span> · @@GEN@@ · ANALYZE.PY + BUILD_HTML_V8.PY</div>
</footer>

</div>
</body></html>
"""

html_out = (html_out
  .replace("@@COMMITS@@", f"{total_commits}")
  .replace("@@NSKILLS@@", f"{total_skills_ct}")
  .replace("@@ZERO@@", f"{zero_ref_ct:02d}")
  .replace("@@GEN@@", data["generated_at"][:10])
  .replace("@@STAMP@@", data["generated_at"].replace("T", " ")[:16] + " GMT+8")
  .replace("@@DIST@@", dist_html)
  .replace("@@HEATMAP@@", heatmap_svg)
  .replace("@@CARDS@@", cards_html)
  .replace("@@ROWS_BAR@@", rows_bar)
  .replace("@@ROWS_TOP@@", rows_top)
  .replace("@@ROWS_ZERO@@", rows_zero))

(OUT/"report_v8.html").write_text(html_out, encoding="utf-8")
print(f"v8 written: {OUT/'report_v8.html'} ({len(html_out)} bytes)")
