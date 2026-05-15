#!/usr/bin/env python3
"""Analyze fastpublish repo contributors + skill/knowledge quality."""
import subprocess, json, os, re, collections, datetime
from pathlib import Path

REPO = Path.home() / ".openclaw/workspace/fastpublish"
OUT = Path.home() / ".openclaw/workspace/projects/fastpublish-analysis"
OUT.mkdir(parents=True, exist_ok=True)

# ---- Identity merge ----
# Same person multiple emails. Merge by canonical handle.
IDENTITY = {
    # email -> canonical display
    "wei.liu@garena.com": "Charles Liu (wei.liu)",
    "liuwei@garena.com": "Charles Liu (wei.liu)",
    "charlesliu66@users.noreply.github.com": "Charles Liu (wei.liu)",
    "chaaarlesliu666@gmail.com": "Charles Liu (wei.liu)",
    "huangyu201910@gmail.com": "Huang Yu (DeeDee)",
    "peicheng.zheng@garena.com": "Peicheng Zheng",
    "chenchen.zhang@garena.com": "Chenchen Zhang (张鱼哥)",
    "pingfan@garena.com": "Pingfan",
    "shadow@shadowdemacbook-air.local": "Pingfan",
    "shadow@shadowdeMacBook-Air.local": "Pingfan",
    "zhangyk@garena.com": "Zhang Yaokuang",
    "pm-agent@openclaw.ai": "PM Agent (bot)",
}

def canon(email):
    return IDENTITY.get(email.strip().lower(), email)

# ---- Parse numstat ----
EXCLUDE_RE = re.compile(r"(package-lock\.json|pnpm-lock\.yaml|yarn\.lock|node_modules/|\.next/|dist/|build/|\.git/|\.png$|\.jpg$|\.jpeg$|\.webp$|\.gif$|\.pdf$|\.zip$|\.mp4$|\.mp3$|\.ico$|\.svg$)")

commits = {}  # sha -> {email, date, files}
current = None
with open(OUT/"numstat.txt") as f:
    for line in f:
        line = line.rstrip("\n")
        if line.startswith("COMMIT|"):
            parts = line.split("|", 3)
            sha = parts[1]; email = parts[2]; date = parts[3]
            current = sha
            commits[sha] = {"email": email.lower(), "date": date, "files": []}
        elif line.strip() and current:
            # numstat: insertions\tdeletions\tpath  (or "-" for binary)
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            ins, dels, path = parts[0], parts[1], parts[2]
            if EXCLUDE_RE.search(path):
                continue
            try:
                ins_n = int(ins) if ins != "-" else 0
                del_n = int(dels) if dels != "-" else 0
            except:
                continue
            commits[sha]["files"].append((path, ins_n, del_n))

# ---- Contributor aggregation ----
contrib = collections.defaultdict(lambda: {
    "commits": 0, "ins": 0, "del": 0, "files": set(), "modules": collections.Counter(),
    "first": None, "last": None, "days": set(), "emails": set(),
})

def module_of(path):
    if path.startswith("agents/"):
        # use first 2 segs
        parts = path.split("/")
        return f"agents/{parts[1]}" if len(parts) > 1 else "agents"
    if path.startswith("skills/"):
        return f"skill:{path.split('/')[1]}" if "/" in path else "skills"
    if path.startswith("knowledge/"):
        return f"knowledge/{path.split('/')[1]}" if path.count("/")>=2 else "knowledge"
    if path.startswith("tool-stations/"):
        return f"tool:{path.split('/')[1]}" if path.count("/")>=2 else "tool-stations"
    return path.split("/")[0]

for sha, c in commits.items():
    name = canon(c["email"])
    d = contrib[name]
    d["commits"] += 1
    d["emails"].add(c["email"])
    dt = c["date"][:10]
    d["days"].add(dt)
    if d["first"] is None or dt < d["first"]:
        d["first"] = dt
    if d["last"] is None or dt > d["last"]:
        d["last"] = dt
    for path, ins, dels in c["files"]:
        d["ins"] += ins
        d["del"] += dels
        d["files"].add(path)
        d["modules"][module_of(path)] += 1

# ---- Per-file primary author (for quality scoring) ----
# Determine "main author" of skill/knowledge: who added the most lines.
file_authors = collections.defaultdict(lambda: collections.Counter())  # path -> {author: lines}
for sha, c in commits.items():
    name = canon(c["email"])
    for path, ins, dels in c["files"]:
        file_authors[path][name] += ins  # weight by insertions

def main_author(path):
    if path not in file_authors or not file_authors[path]:
        return None
    return file_authors[path].most_common(1)[0][0]

# ---- Skill quality scoring ----
def score_skill(skill_dir: Path):
    """Return dict with quality scores 1-5 each."""
    sm = skill_dir / "SKILL.md"
    text = sm.read_text(errors="ignore") if sm.exists() else ""
    files = list(skill_dir.rglob("*"))
    files = [f for f in files if f.is_file()]
    file_count = len(files)
    has_scripts = any(f.suffix in (".py",".sh",".ts",".js") and "scripts" in str(f) for f in files)
    has_templates = any("template" in str(f).lower() or f.suffix==".j2" for f in files)
    has_config = any(f.name in ("config.yaml","config.yml",".env.example") for f in files)
    has_refs = (skill_dir/"references").exists()
    has_tests = (skill_dir/"tests").exists()
    word_count = len(text.split())
    
    # 结构性: front-matter + sections
    sec = sum(1 for kw in ("## ", "When to","Inputs","Outputs","Steps","Workflow","Trigger") if kw in text)
    structure = min(5, 1 + sec//1)
    if "summary:" in text or "name:" in text: structure = min(5, structure+1)
    structure = max(1, min(5, structure))
    
    # 可复用: 抽象/模板/参数化
    reuse = 1
    if has_templates: reuse += 1
    if has_refs: reuse += 1
    if word_count > 200: reuse += 1
    if "template" in text.lower() or "parameter" in text.lower(): reuse += 1
    reuse = min(5, reuse)
    
    # 可执行: scripts/templates
    exec_s = 1
    if has_scripts: exec_s += 2
    if has_config: exec_s += 1
    if has_templates: exec_s += 1
    exec_s = min(5, exec_s)
    
    # 时效: 维护程度（看 git 最后修改时间 + 文件数）
    try:
        last = subprocess.check_output(["git","-C",str(REPO),"log","-1","--format=%ai","--",str(skill_dir.relative_to(REPO))], text=True).strip()
        if last:
            age_days = (datetime.date.today() - datetime.date.fromisoformat(last[:10])).days
            if age_days < 14: fresh = 5
            elif age_days < 30: fresh = 4
            elif age_days < 60: fresh = 3
            elif age_days < 120: fresh = 2
            else: fresh = 1
        else:
            fresh = 1
    except Exception:
        fresh = 1
    
    return {
        "structure": structure, "reuse": reuse, "exec": exec_s, "fresh": fresh,
        "file_count": file_count, "word_count": word_count, "last": last if 'last' in locals() else "",
    }

# ---- Find references (引用率) ----
def ref_count(skill_name):
    try:
        out = subprocess.check_output(
            ["git","-C",str(REPO),"grep","-l","-i","-E",re.escape(skill_name),"--","*.md"],
            text=True, stderr=subprocess.DEVNULL,
        )
        return len([l for l in out.splitlines() if skill_name not in l.split("/")[-2:]])
    except subprocess.CalledProcessError:
        return 0

# ---- Scan skills ----
skill_dirs = []
for base in ["skills","agents"]:
    bp = REPO/base
    if not bp.exists(): continue
    for sm in bp.rglob("SKILL.md"):
        skill_dirs.append(sm.parent)

skills_data = []
for sd in skill_dirs:
    rel = sd.relative_to(REPO)
    name = sd.name
    if name.startswith("_template"): continue
    scores = score_skill(sd)
    # Main author = author who added most lines across all files in this dir
    auth_counter = collections.Counter()
    for f in sd.rglob("*"):
        if f.is_file():
            try:
                p = str(f.relative_to(REPO))
                if p in file_authors:
                    for a, v in file_authors[p].items():
                        auth_counter[a] += v
            except: pass
    main = auth_counter.most_common(1)[0][0] if auth_counter else "unknown"
    refs = ref_count(name)
    # Reference score 1-5
    if refs >= 10: ref_s = 5
    elif refs >= 5: ref_s = 4
    elif refs >= 2: ref_s = 3
    elif refs >= 1: ref_s = 2
    else: ref_s = 1
    total = scores["structure"]+scores["reuse"]+scores["exec"]+ref_s+scores["fresh"]
    skills_data.append({
        "path": str(rel), "name": name, "author": main,
        "structure": scores["structure"], "reuse": scores["reuse"],
        "exec": scores["exec"], "refs": refs, "ref_score": ref_s,
        "fresh": scores["fresh"], "total": total,
        "files": scores["file_count"], "words": scores["word_count"],
        "last": scores["last"],
    })

skills_data.sort(key=lambda x: -x["total"])

# ---- Knowledge files: score by main author ----
knowledge_by_author = collections.defaultdict(int)  # author -> files authored
for f in (REPO/"knowledge").rglob("*.md"):
    rel = str(f.relative_to(REPO))
    a = main_author(rel)
    if a: knowledge_by_author[a] += 1

# ---- Skill counts per author ----
skill_by_author = collections.Counter()
for s in skills_data:
    skill_by_author[s["author"]] += 1
skill_quality_avg = {}
buckets = collections.defaultdict(list)
for s in skills_data:
    buckets[s["author"]].append(s["total"])
for a, lst in buckets.items():
    skill_quality_avg[a] = sum(lst)/len(lst)

# ---- Daily activity per author ----
daily = collections.defaultdict(lambda: collections.defaultdict(lambda: {"commits":0,"churn":0}))
for sha, c in commits.items():
    name = canon(c["email"])
    dt = c["date"][:10]
    churn = sum(ins+dels for _,ins,dels in c["files"])
    daily[name][dt]["commits"] += 1
    daily[name][dt]["churn"] += churn

# ---- Top commits per author (representative) ----
# Pull commit messages
commit_msg = {}
with open(OUT/"commits.txt") as f:
    for line in f:
        parts = line.rstrip().split("|", 4)
        if len(parts) >= 5:
            commit_msg[parts[0]] = {"author": parts[1], "email": parts[2], "date": parts[3], "subject": parts[4]}

top_commits = collections.defaultdict(list)
for sha, c in commits.items():
    name = canon(c["email"])
    if name == "PM Agent (bot)": continue
    info = commit_msg.get(sha, {})
    subj = info.get("subject", "")
    churn = sum(ins+dels for _,ins,dels in c["files"])
    files_n = len(c["files"])
    # score: prefer non-trivial commits (skip merges/typos)
    if subj.lower().startswith(("merge ","merge:")): continue
    if churn < 5: continue
    top_commits[name].append({
        "sha": sha[:7], "date": c["date"][:10], "subject": subj[:90],
        "churn": churn, "files": files_n,
    })
for name in top_commits:
    # Sort by churn descending, pick top 3
    top_commits[name].sort(key=lambda x: -x["churn"])
    top_commits[name] = top_commits[name][:3]

# ---- Build final contributor list ----
contributors = []
for name, d in contrib.items():
    contributors.append({
        "name": name,
        "commits": d["commits"],
        "ins": d["ins"], "del": d["del"], "net": d["ins"]-d["del"],
        "files": len(d["files"]),
        "active_days": len(d["days"]),
        "first": d["first"], "last": d["last"],
        "top_modules": d["modules"].most_common(5),
        "emails": sorted(d["emails"]),
        "skills_authored": skill_by_author.get(name, 0),
        "knowledge_files": knowledge_by_author.get(name, 0),
        "avg_skill_quality": round(skill_quality_avg.get(name, 0), 1),
        "daily": {dt: v for dt, v in daily[name].items()},
        "top_commits": top_commits.get(name, []),
    })
contributors.sort(key=lambda x: -x["commits"])

# ---- Dump JSON ----
result = {
    "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
    "repo": str(REPO),
    "total_commits": len(commits),
    "total_skills": len(skills_data),
    "contributors": contributors,
    "skills": skills_data,
}
(OUT/"result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
print(f"OK: {len(contributors)} contributors, {len(skills_data)} skills, {len(commits)} commits")
print(f"Output: {OUT/'result.json'}")
