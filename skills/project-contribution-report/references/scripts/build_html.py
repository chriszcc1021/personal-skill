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
    "grade":"A",
  },
  "Huang Yu (DeeDee)": {
    "role":"内容 · CONTENT",
    "verdict":"把游戏内容知识库从零填到 26 个文件，commits 数最高。",
    "highlights":["26 个 knowledge/game 文件","issue-tracker tool station 原型也是他起的（14k 行）"],
    "gaps":["工具化产出 = 1 个 skill；文档为主","10 天集中产出后未持续"],
    "tags":["策划知识","高产","文档型"],
    "grade":"A-",
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
    "grade":"A-",
  },
  "Chenchen Zhang (张鱼哥)": {
    "role":"PM · OWNER",
    "verdict":"定方向、立框架，亲手把 event_analysis 从 10/25 提到 23/25。",
    "highlights":["AGENTS.md / 多 Agent 设计 / FGD 报告等框架性输出","演示了按维度对症提分的方法论可复用"],
    "gaps":["活跃天数 5 天，主要在前期与最近一次冲刺","初版 event_analysis 缺脚本/模板（后已修复）"],
    "tags":["PM","设计者","验收方"],
    "grade":"A-",
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

# Bayesian-weighted composite score order (highest → lowest)
_ORDER = ["Charles Liu (wei.liu)", "Huang Yu (DeeDee)", "Pingfan", "Chenchen Zhang (张鱼哥)", "Peicheng Zheng", "Zhang Yaokuang"]
def _rank(c):
    try: return _ORDER.index(c["name"])
    except ValueError: return 999
contributors.sort(key=_rank)

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
hm = [f'<svg width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}" preserveAspectRatio="xMidYMid meet" style="width:100%;height:auto;display:block" xmlns="http://www.w3.org/2000/svg" font-family="Space Mono, monospace">']
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
            tops = info.get('tops', [])
            tops_str = "|".join(f"{ti['sha']} {ti['subject'][:40]}" for ti in tops[:3])
            hm.append(f'<rect x="{x}" y="{y}" width="{CELL_W-2}" height="{CELL_H}" fill="{fill}" data-date="{d}" data-name="{esc(short)}" data-commits="{info["commits"]}" data-churn="{info["churn"]}" data-tops="{esc(tops_str)}" class="hm-cell"></rect>')
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
        kind = t.get("kind","")
        kcls = {"SKILL":"k-skill","KNOWLEDGE":"k-know","TOOL":"k-tool"}.get(kind,"k-know")
        ktag = f'<span class="ktag {kcls}">{kind}</span>' if kind else ""
        gh_url = f"https://github.com/charlesliu66/fastpublish/commit/{t['sha']}"
        rows += f"""
        <li>
          <a class="crow" href="{gh_url}" target="_blank" rel="noopener">
            <span class="cidx">[{i:02d}]</span>
            {ktag}
            <span class="csubj">{esc(t["subject"])}</span>
            <div class="cmeta">{esc(t["sha"])} · {esc(t["date"])} · {t["churn"]:,} 行 · {t["files"]} 个文件</div>
          </a>
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
    # Bus factor warning removed by user request
    extra_warn = ""
    _AV = {"Charles Liu":"charles","Huang Yu":"huangyu","Pingfan":"pingfan","Chenchen Zhang":"chenchen","Peicheng Zheng":"peicheng","Zhang Yaokuang":"yaokuang"}
    av_slug = _AV.get(short, short.lower().split()[0])
    cards_html += f"""
    <article class="card{span_cls}" id="card-{av_slug}">
      <header class="chead">
        <img class="cavatar" src="avatars/av_{av_slug}.png" alt="" onerror="this.style.display='none'">
        <div class="chead-l">
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
        <div><div class="big">{c['avg_skill_quality'] or '—'}</div><div class="lbl">SKILL 质量均分</div></div>
      </div>
      {extra_warn}
      <div class="ctags-row">{tags}</div>
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

# Path is always under repo root: skills/... or agents/... etc.
GITHUB_BASE = "https://github.com/charlesliu66/fastpublish/tree/master"

def _good_reasons(s):
    r = []
    if s["refs"] >= 5:      r.append("高引用")
    if s["exec"] >= 4:      r.append("可执行")
    if s["structure"] >= 4: r.append("强结构")
    if s["reuse"] >= 4:     r.append("高复用")
    return r or ["综合均衡"]

def _bad_reasons(s):
    r = []
    if s["refs"] == 0:      r.append("零引用")
    if s["words"] < 100:    r.append("薄文档")
    if s["exec"] <= 2:      r.append("无脚本")
    if s["structure"] <= 2: r.append("结构弱")
    if s["reuse"] <= 2:     r.append("低复用")
    return r or ["多项偏低"]

def _kw_html(reasons, cls):
    return "".join(f'<span class="kw {cls}">{t}</span>' for t in reasons)

rows_top = ""
for i, s in enumerate(skills_sorted[:10], 1):
    short = s["author"].split(" (")[0].upper()
    pct = s["total"]
    bw = int(pct)
    url = f"{GITHUB_BASE}/{s['path']}"
    kw = _kw_html(_good_reasons(s), "kw-good")
    rows_top += f"""
    <tr class="skill-row">
      <td>{status_dot(s["total"])}</td>
      <td class="rank">[{i:02d}]</td>
      <td class="nm"><a class="skill-link" href="{url}" target="_blank" rel="noopener">{esc(s["name"])}</a></td>
      <td class="auth">{esc(short)}</td>
      <td class="kw-cell">{kw}</td>
      <td><div class="bc"><span class="bar" style="width:{bw}px"></span><span>{pct:02d}/100</span></div></td>
    </tr>"""

# Low quality Top 10: sort by total ASC
low_skills = sorted(skills, key=lambda x: x["total"])[:10]
rows_zero = ""
for i, s in enumerate(low_skills, 1):
    short = s["author"].split(" (")[0].upper()
    pct = s["total"]
    bw = int(pct)
    url = f"{GITHUB_BASE}/{s['path']}"
    kw = _kw_html(_bad_reasons(s), "kw-bad")
    rows_zero += f"""
    <tr class="skill-row">
      <td><span class="sd sd-red"></span></td>
      <td class="rank">[{i:02d}]</td>
      <td class="nm"><a class="skill-link" href="{url}" target="_blank" rel="noopener">{esc(s["name"])}</a></td>
      <td class="auth">{esc(short)}</td>
      <td class="kw-cell">{kw}</td>
      <td><div class="bc"><span class="bar bar-red" style="width:{bw}px"></span><span>{pct:02d}/100</span></div></td>
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

  /* ===== Update button + progress ===== */
  .upd-btn{position:relative;display:inline-flex;align-items:center;gap:8px;background:var(--accent);color:#fff;border:0;padding:5px 12px;font-family:'Space Mono',monospace;font-size:10px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;cursor:pointer;overflow:hidden;min-width:160px;justify-content:center;transition:opacity 0.15s}
  .upd-btn:not(:disabled):not(.run):not(.ok):not(.fail)::after{content:"";position:absolute;inset:-2px;border:1px solid var(--accent);opacity:0;pointer-events:none;transition:opacity 0.2s}
  .upd-btn:not(:disabled):not(.run):hover::after{opacity:1;animation:btnScan 1.8s linear infinite}
  @keyframes btnScan{0%{clip-path:inset(0 100% 0 0)}50%{clip-path:inset(0 0 0 0)}100%{clip-path:inset(0 0 0 100%)}}
  .upd-btn:hover{opacity:0.9}
  .upd-btn:disabled{cursor:not-allowed;background:var(--raised);color:var(--t-secondary)}
  .upd-btn .upd-fill{position:absolute;left:0;top:0;bottom:0;width:0;background:rgba(255,255,255,0.22);transition:width 0.4s ease}
  .upd-btn.run{background:var(--raised);color:var(--t-display);border:1px solid var(--border-v)}
  .upd-btn.run .upd-fill{background:var(--accent)}
  .upd-btn.ok{background:#0d3d12;color:#aef0b6;border:1px solid #1e6c25}
  .upd-btn.fail{background:#3d0d10;color:#f0aeb3;border:1px solid #6c1e25}
  .upd-btn .upd-text{position:relative;z-index:1;display:inline-flex;align-items:center;gap:6px}
  .upd-btn .upd-text::before{content:'';width:6px;height:6px;border-radius:50%;background:currentColor;display:inline-block}
  .upd-btn.run .upd-text::before{animation:pulse 1s infinite}

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
  .distbar{height:100%;background:var(--t-display);display:flex;align-items:center;padding:0 16px;min-width:130px;transform:scaleX(0);transform-origin:left center;transition:transform 0.9s cubic-bezier(0.25,0.1,0.25,1),background 0.2s}
  .in-view .distbar,.seg-section.in-view .distbar{transform:scaleX(1)}
  .distrow:hover .distbar{background:var(--accent)}
  .distbar .distnum{opacity:0;transition:opacity 0.4s ease 0.6s}
  .in-view .distbar .distnum,.seg-section.in-view .distbar .distnum{opacity:1}
  @media (prefers-reduced-motion: reduce){.distbar{transform:scaleX(1)!important;transition:none!important} .distbar .distnum{opacity:1!important}}
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
  .verdict{font-family:'Space Grotesk','PingFang SC',sans-serif;font-size:17px;color:var(--t-primary);line-height:1.6;margin-bottom:24px;padding:14px 18px;background:rgba(215,25,33,0.06);border-left:3px solid var(--accent)}

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
  .ktag{display:inline-block;font-family:'Space Mono',monospace;font-size:9.5px;font-weight:700;letter-spacing:0.12em;padding:2px 6px;margin-right:8px;border:1px solid var(--border-v);vertical-align:1px}
  .ktag.k-skill{color:#f0aeb3;border-color:#6c1e25;background:rgba(215,25,33,0.10)}
  .ktag.k-know {color:#aef0b6;border-color:#1e6c25;background:rgba(25,180,80,0.08)}
  .ktag.k-tool {color:#f0d8ae;border-color:#6c4f1e;background:rgba(215,150,25,0.10)}

  /* ===== Commit row clickable ===== */
  .crow{display:block;color:inherit;text-decoration:none;padding:8px 10px;margin:-8px -10px;border-radius:0;transition:background 0.15s}
  .crow:hover{background:var(--raised);text-decoration:none}
  .crow:hover .csubj{color:var(--t-display);text-decoration:underline;text-decoration-color:var(--accent);text-underline-offset:3px}
  .crow:hover .cmeta{color:var(--t-primary)}

  /* ===== Avatar ===== */
  .cavatar{width:56px;height:56px;flex-shrink:0;display:block;margin-top:4px;border-radius:50%;transition:transform 0.25s cubic-bezier(0.25,0.1,0.25,1),box-shadow 0.25s}
  .chead:hover .cavatar{transform:scale(1.06);box-shadow:0 0 0 2px var(--accent)}
  .chead{align-items:flex-start;gap:18px}
  .chead-l{flex:1;min-width:0}

  /* ===== Heatmap tooltip ===== */
  .hmwrap{position:relative}
  /* ===== Heatmap cell typewriter pop-in ===== */
  .hm-cell{cursor:crosshair;opacity:0;transform-origin:center;transform:scale(0.4);transition:opacity 0.12s linear,transform 0.18s cubic-bezier(0.34,1.56,0.64,1),stroke 0.15s}
  .hmwrap.in-view .hm-cell{opacity:1;transform:scale(1)}
  .hm-cell:hover{stroke:var(--accent);stroke-width:1.5}
  #hm-tip{position:fixed;display:none;background:rgba(15,15,15,0.97);color:var(--t-display);padding:12px 14px;border:1px solid #444;font-family:'Space Mono',monospace;font-size:11px;line-height:1.7;letter-spacing:0.04em;pointer-events:none;z-index:50;min-width:220px;max-width:340px;box-shadow:0 8px 24px rgba(0,0,0,0.6);white-space:nowrap}
  #hm-tip .tip-h{color:var(--accent);font-weight:700;letter-spacing:0.08em;text-transform:uppercase;border-bottom:1px solid #333;padding-bottom:6px;margin-bottom:8px;font-size:10.5px}
  #hm-tip .tip-m{color:var(--t-secondary);font-size:10px;text-transform:uppercase;letter-spacing:0.08em}
  #hm-tip .tip-top{color:var(--t-primary);margin-top:6px;white-space:normal}
  #hm-tip .tip-top .ts{color:#888;display:inline-block;width:60px}

  /* ===== Mini X-axis date cursor under heatmap ===== */
  .hmwrap{overflow:hidden}
  #hm-cursor{position:absolute;top:0;bottom:0;width:1px;background:var(--accent);pointer-events:none;display:none;opacity:0.7}
  #hm-cursor-lbl{position:absolute;background:var(--accent);color:#fff;padding:3px 8px;font-family:'Space Mono',monospace;font-size:10px;letter-spacing:0.1em;pointer-events:none;display:none;white-space:nowrap;z-index:51}

  /* ===== Update button hover hint ===== */
  .upd-btn[data-since]:hover::after{
    content:attr(data-since);
    position:absolute;top:calc(100% + 8px);right:0;
    background:rgba(15,15,15,0.97);color:var(--t-primary);
    padding:6px 10px;border:1px solid #444;
    font-family:'Space Mono',monospace;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;
    white-space:nowrap;pointer-events:none;z-index:60;
  }

  .cfoot{margin-top:auto;display:flex;flex-wrap:wrap;gap:6px;padding-top:18px;border-top:1px solid var(--border)}
  .ctags-row{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:18px}

  /* Skill table row link + keyword chips (Nothing design: high contrast monochrome) */
  .skill-row:hover{background:var(--raised)}
  .skill-link{color:var(--t-display);text-decoration:none;border-bottom:1px solid transparent}
  .skill-link:hover{color:var(--accent);border-bottom-color:var(--accent)}
  .kw-cell{padding:6px 12px;vertical-align:middle;white-space:nowrap;line-height:1}
  .kw-cell .kw{margin-right:5px}
  .kw-cell .kw:last-child{margin-right:0}
  .kw{display:inline-block;font-family:'Space Mono',monospace;font-size:10px;font-weight:700;letter-spacing:0.1em;padding:3px 8px;text-transform:uppercase;line-height:1.4;vertical-align:middle}
  .kw-good{color:#0a0a0a;background:#E8E8E8;border:1px solid #E8E8E8}
  .kw-bad {color:#E8E8E8;background:transparent;border:1px solid #666}
  .bar-red{background:var(--accent)!important;opacity:0.85}
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
  .bc .bar{height:5px;background:var(--t-display);min-width:2px;display:inline-block;transform-origin:left center;transform:scaleX(0);transition:transform 0.9s cubic-bezier(0.25,0.1,0.25,1)}
  body.loaded .bc .bar{transform:scaleX(1)}
  .bc span{font-family:'Space Mono',monospace;font-size:13px;color:var(--t-primary);letter-spacing:0.04em}

  /* === Page entrance: cards fade-up stagger === */
  .card{opacity:0;transform:translateY(12px);transition:opacity 0.5s cubic-bezier(0.25,0.1,0.25,1),transform 0.5s cubic-bezier(0.25,0.1,0.25,1)}
  body.loaded .card{opacity:1;transform:translateY(0)}
  body.loaded .card:nth-child(1){transition-delay:0ms}
  body.loaded .card:nth-child(2){transition-delay:80ms}
  body.loaded .card:nth-child(3){transition-delay:160ms}
  body.loaded .card:nth-child(4){transition-delay:240ms}
  body.loaded .card:nth-child(5){transition-delay:320ms}
  body.loaded .card:nth-child(6){transition-delay:400ms}

  /* === Top scroll-progress 1px red line === */
  #scroll-prog{position:fixed;top:0;left:0;height:1.5px;width:0;background:var(--accent);z-index:200;transition:width 0.08s linear;pointer-events:none}

  /* === Back-to-top button === */
  #go-top{position:fixed;right:24px;bottom:24px;width:40px;height:40px;background:var(--accent);color:#fff;border:0;font-family:'Space Mono',monospace;font-size:18px;font-weight:700;cursor:pointer;opacity:0;transform:translateY(12px);transition:opacity 0.25s cubic-bezier(0.25,0.1,0.25,1),transform 0.25s cubic-bezier(0.25,0.1,0.25,1);z-index:150;display:flex;align-items:center;justify-content:center;padding:0;line-height:1}
  #go-top.show{opacity:1;transform:translateY(0)}
  #go-top:hover{background:#a5141b}
  @media (prefers-reduced-motion: reduce){#go-top{transition:none}}

  /* === Enhanced hover: commit row with red rail === */
  .crow{position:relative}
  .crow::before{content:"";position:absolute;left:0;top:0;bottom:0;width:0;background:var(--accent);transition:width 0.18s cubic-bezier(0.25,0.1,0.25,1)}
  .crow:hover{padding-left:18px;transition:padding 0.18s cubic-bezier(0.25,0.1,0.25,1),background 0.15s}
  .crow:hover::before{width:2px}

  /* === Enhanced hover: skill row bar turns red === */
  .skill-row{transition:background 0.15s}
  .skill-row .bar{transition:transform 0.9s cubic-bezier(0.25,0.1,0.25,1),background 0.18s}
  .skill-row:hover .bar{background:var(--accent)}
  .skill-row:hover .bar-red{opacity:1}

  /* === Respect user motion preferences === */
  @media (prefers-reduced-motion: reduce){
    .card,.bc .bar,.crow,.skill-row .bar{transition:none!important;animation:none!important}
    .card{opacity:1;transform:none}
    .bc .bar{transform:scaleX(1)}
  }

  /* === Scroll-in reveal for sections + standalone rows === */
  .reveal{opacity:0;transform:translateY(16px);transition:opacity 0.45s cubic-bezier(0.25,0.1,0.25,1),transform 0.45s cubic-bezier(0.25,0.1,0.25,1)}
  .reveal.in-view{opacity:1;transform:none}
  .stagger-row{opacity:0;transform:translateY(8px);transition:opacity 0.35s cubic-bezier(0.25,0.1,0.25,1),transform 0.35s cubic-bezier(0.25,0.1,0.25,1)}
  .stagger-row.in-view{opacity:1;transform:none}
  @media (prefers-reduced-motion: reduce){
    .reveal,.stagger-row{opacity:1!important;transform:none!important;transition:none!important}
    .hm-cell{opacity:1!important}
  }

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
<div id="scroll-prog"></div>
<button id="go-top" type="button" aria-label="返回顶部">↑</button>

<!-- DASHBOARD TOP BAR -->
<div class="topbar">
  <div class="tb-l"><span class="brand-dot"></span><span>FASTPUBLISH</span><span style="color:var(--t-disabled);margin-left:8px">/ 仓库画像</span></div>
  <div class="tb-c"><a class="active">[ 分析 ]</a><a>SKILLS</a><a>贡献者</a><a>历史</a></div>
  <div class="tb-r"><button id="updBtn" class="upd-btn" type="button" onclick="runUpdate()"><span class="upd-fill"></span><span class="upd-text" id="updTxt">UPDATE REPORT</span></button><span>@@GEN@@</span><span style="color:var(--t-disabled)">·</span><span>HTTP</span></div>
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
  <div class="hmwrap">@@HEATMAP@@<div id="hm-cursor"></div><div id="hm-cursor-lbl"></div><div id="hm-tip"></div></div>
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
      <th style="width:36px"></th><th>贡献者</th><th>提交</th><th>净增行</th><th>主笔技能</th><th>知识文档</th><th>活跃天数</th><th>SKILL 质量均分</th>
    </tr></thead>
    <tbody>@@ROWS_BAR@@</tbody>
  </table>
</section>

<!-- TOP SKILLS -->
<section class="sec">
  <div class="sec-head"><h2>核心技能 Top 10</h2><div class="lbl">[ 04 ] 按质量分排序 · 点击跳 GITHUB</div></div>
  <table>
    <thead><tr><th style="width:36px"></th><th style="width:56px">#</th><th>技能名称</th><th>主笔</th><th>亮点</th><th>分数</th></tr></thead>
    <tbody>@@ROWS_TOP@@</tbody>
  </table>
</section>

<!-- LOW QUALITY -->
<section class="sec">
  <div class="sec-head"><h2>低质量技能 Top 10</h2><div class="lbl">[ 05 ] • 待跟进项 · 点击跳 GITHUB</div></div>
  <table>
    <thead><tr><th style="width:36px"></th><th style="width:56px">#</th><th>技能名称</th><th>主笔</th><th>问题</th><th>分数</th></tr></thead>
    <tbody>@@ROWS_ZERO@@</tbody>
  </table>
</section>



<!-- CAVEAT + METHOD removed by user request -->

<footer>
  <div>● FASTPUBLISH · 仓库画像</div>
  <div>VER <span class="ver-red">8.0</span> · @@GEN@@ · ANALYZE.PY + BUILD_HTML_V8.PY</div>
</footer>

</div>
<script>
function runUpdate(){
  const btn = document.getElementById('updBtn');
  const txt = document.getElementById('updTxt');
  const fill = btn.querySelector('.upd-fill');
  if (btn.disabled) return;
  btn.disabled = true; btn.classList.remove('ok','fail'); btn.classList.add('run');
  txt.textContent = 'STARTING...'; fill.style.width = '0%';
  fetch('/fastpublish/refresh', {method:'POST'})
    .then(r => r.ok ? r.json() : r.json().then(j => Promise.reject(j.error || 'error')))
    .then(({job_id}) => {
      const es = new EventSource('/fastpublish/refresh/' + job_id);
      let totalSteps = 5;
      es.onmessage = (e) => {
        const ev = JSON.parse(e.data);
        if (ev.type === 'step') {
          totalSteps = ev.total;
          const pct = Math.round(((ev.i + (ev.status === 'ok' ? 1 : 0.4)) / ev.total) * 100);
          fill.style.width = pct + '%';
          if (ev.status === 'running') txt.textContent = '[' + (ev.i+1) + '/' + ev.total + '] ' + (ev.label || ev.key).toUpperCase();
          if (ev.status === 'fail') { btn.classList.remove('run'); btn.classList.add('fail'); txt.textContent = 'FAILED: ' + ev.key; es.close(); }
        } else if (ev.type === 'done') {
          es.close();
          if (ev.ok) {
            fill.style.width = '100%';
            btn.classList.remove('run'); btn.classList.add('ok');
            txt.textContent = 'UPDATED · RELOADING';
            setTimeout(() => location.reload(), 1500);
          } else {
            btn.classList.remove('run'); btn.classList.add('fail');
            txt.textContent = 'FAILED' + (ev.err ? ': ' + ev.err.slice(0,30) : '');
            setTimeout(resetBtn, 4000);
          }
        }
      };
      es.onerror = () => { es.close(); btn.classList.remove('run'); btn.classList.add('fail'); txt.textContent = 'STREAM ERROR'; setTimeout(resetBtn, 4000); };
    })
    .catch(err => {
      btn.classList.remove('run'); btn.classList.add('fail');
      txt.textContent = (typeof err === 'string' ? err : 'REQUEST FAILED').toUpperCase().slice(0,30);
      setTimeout(resetBtn, 4000);
    });
  function resetBtn(){ btn.disabled = false; btn.classList.remove('fail','ok'); txt.textContent = 'UPDATE REPORT'; fill.style.width = '0%'; }
}
</script>
<script>
// === Trigger entrance animations after first paint ===
requestAnimationFrame(() => {
  requestAnimationFrame(() => document.body.classList.add('loaded'));
});

// === Top scroll-progress bar ===
(function(){
  const bar = document.getElementById('scroll-prog');
  const top = document.getElementById('go-top');
  if (top){
    top.addEventListener('click', () => window.scrollTo({top:0, behavior:'smooth'}));
  }
  if (!bar) return;
  function update(){
    const h = document.documentElement;
    const max = h.scrollHeight - h.clientHeight;
    const pct = max > 0 ? (h.scrollTop / max) * 100 : 0;
    bar.style.width = pct + '%';
    if (top){ top.classList.toggle('show', h.scrollTop > 800); }
  }
  update();
  window.addEventListener('scroll', update, {passive: true});
  window.addEventListener('resize', update);
})();

// === Scroll-in reveal (IntersectionObserver) ===
(function(){
  if (!('IntersectionObserver' in window)) return;
  // Tag elements
  document.querySelectorAll('section.sec, section.seg-section, .hmwrap').forEach(el => el.classList.add('reveal'));
  document.querySelectorAll('.skill-row, .crow, tbody tr').forEach(el => el.classList.add('stagger-row'));

  // Typewriter stagger: row by row, left to right ("啦啦啦啦")
  const cells = document.querySelectorAll('.hm-cell');
  cells.forEach(c => {
    const x = parseFloat(c.getAttribute('x') || '0');
    const y = parseFloat(c.getAttribute('y') || '0');
    // row index from y (~22px stride), col from x (~14px stride, label offset 160)
    const row = Math.round((y - 30) / 22);
    const col = Math.round((x - 160) / 14);
    const delay = row * 380 + col * 22;  // 380ms per row "clack", 22ms per cell
    c.style.transitionDelay = delay + 'ms';
  });

  // Stagger distbars by row index inside .seg-section
  document.querySelectorAll('.seg-section .distrow').forEach((row, i) => {
    const bar = row.querySelector('.distbar');
    if (bar) bar.style.transitionDelay = (i * 90) + 'ms';
    const num = row.querySelector('.distnum');
    if (num) num.style.transitionDelay = (600 + i * 90) + 'ms';
  });

  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting){
        e.target.classList.add('in-view');
        // Stagger child rows once container hits
        if (e.target.classList.contains('reveal')){
          const rows = e.target.querySelectorAll('.stagger-row');
          rows.forEach((r,i) => { r.style.transitionDelay = Math.min(i*30, 480) + 'ms'; });
        }
        io.unobserve(e.target);
      }
    });
  }, {rootMargin: '0px 0px -10% 0px', threshold: 0.12});

  document.querySelectorAll('.reveal, .stagger-row').forEach(el => io.observe(el));
})();
</script>

<script>
// ===== Heatmap interactive tooltip + x-axis date cursor =====
(function(){
  const wrap = document.querySelector('.hmwrap');
  if (!wrap) return;
  const tip = document.getElementById('hm-tip');
  const cur = document.getElementById('hm-cursor');
  const curLbl = document.getElementById('hm-cursor-lbl');
  const cells = wrap.querySelectorAll('.hm-cell');
  function fmtDate(s){
    const [y,m,d] = s.split('-').map(Number);
    const dt = new Date(y, m-1, d);
    const wk = ['周日','周一','周二','周三','周四','周五','周六'][dt.getDay()];
    return s + ' · ' + wk;
  }
  cells.forEach(cell => {
    cell.addEventListener('mouseenter', e => {
      const d = cell.getAttribute('data-date');
      const name = cell.getAttribute('data-name');
      const commits = cell.getAttribute('data-commits');
      const churn = parseInt(cell.getAttribute('data-churn'),10).toLocaleString();
      const tops = cell.getAttribute('data-tops');
      let topsHtml = '';
      if (tops) {
        topsHtml = '<div class="tip-top">' + tops.split('|').slice(0,3).map(t => {
          const sp = t.indexOf(' ');
          if (sp<0) return '';
          return '<div><span class="ts">'+t.slice(0,sp)+'</span>'+t.slice(sp+1)+'</div>';
        }).join('') + '</div>';
      }
      tip.innerHTML = '<div class="tip-h">'+name+'</div>'+
        '<div>'+fmtDate(d)+'</div>'+
        '<div class="tip-m">'+commits+' commits · '+churn+' 行</div>'+
        topsHtml;
      tip.style.display = 'block';
    });
    cell.addEventListener('mouseleave', () => { tip.style.display = 'none'; });
  });
  wrap.addEventListener('mousemove', e => {
    const rect = wrap.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    // Position tooltip (position:fixed) using viewport coords, clamp to viewport
    if (tip.style.display === 'block') {
      const tw = tip.offsetWidth, th = tip.offsetHeight;
      let tx = e.clientX + 14, ty = e.clientY + 14;
      if (tx + tw > window.innerWidth - 8)  tx = e.clientX - tw - 14;
      if (ty + th > window.innerHeight - 8) ty = e.clientY - th - 14;
      tip.style.left = Math.max(8, tx) + 'px';
      tip.style.top  = Math.max(8, ty) + 'px';
    }
    // Find date from cell under cursor (if any) for x-axis cursor label
    const el = document.elementFromPoint(e.clientX, e.clientY);
    if (el && el.classList && el.classList.contains('hm-cell')) {
      const d = el.getAttribute('data-date');
      const cellRect = el.getBoundingClientRect();
      cur.style.left = (cellRect.left - rect.left + cellRect.width/2) + 'px';
      cur.style.display = 'block';
      curLbl.textContent = fmtDate(d);
      curLbl.style.left = (cellRect.left - rect.left + cellRect.width/2 - 50) + 'px';
      curLbl.style.bottom = '-26px';
      curLbl.style.display = 'block';
    } else {
      cur.style.display = 'none';
      curLbl.style.display = 'none';
    }
  });
  wrap.addEventListener('mouseleave', () => { tip.style.display='none'; cur.style.display='none'; curLbl.style.display='none'; });
})();

// ===== Update button hover: show 'last update X min ago' =====
(function(){
  const btn = document.getElementById('updBtn');
  if (!btn) return;
  const stampEl = document.querySelector('.hero-stamp');
  let stamp = null;
  if (stampEl) {
    const m = stampEl.textContent.match(/(\d{4}-\d{2}-\d{2})\s+(\d{1,2}:\d{2})/);
    if (m) stamp = new Date(m[1] + 'T' + m[2] + ':00+08:00');
  }
  function update(){
    if (!stamp) { btn.setAttribute('data-since', 'NEVER UPDATED'); return; }
    const min = Math.floor((Date.now() - stamp.getTime())/60000);
    let txt;
    if (min < 1)   txt = '刚刚更新';
    else if (min < 60)  txt = '上次更新 ' + min + ' 分钟前';
    else if (min < 24*60) txt = '上次更新 ' + Math.floor(min/60) + ' 小时前';
    else txt = '上次更新 ' + Math.floor(min/(60*24)) + ' 天前';
    btn.setAttribute('data-since', txt);
  }
  update();
  setInterval(update, 30000);
})();
</script>
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
