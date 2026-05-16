"""TeamForge backend v0.1 — character CRUD with soft delete."""
import os, json, sqlite3, time, uuid, shutil
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Body
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DATA = Path(os.environ.get("TF_DATA", "/var/teamforge-data"))
DATA.mkdir(parents=True, exist_ok=True)
(AVATARS := DATA / "avatars").mkdir(exist_ok=True)
DB_PATH = DATA / "db.sqlite"

# ---------- DB ----------
def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c

def init_db():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS characters(
            id TEXT PRIMARY KEY,
            cn_name TEXT NOT NULL,
            en_name TEXT DEFAULT '',
            func TEXT DEFAULT '',
            years TEXT DEFAULT '',
            avatar_url TEXT DEFAULT '',
            tags_json TEXT DEFAULT '[]',
            skills_json TEXT DEFAULT '{}',
            bio TEXT DEFAULT '',
            style TEXT DEFAULT '',
            strengths TEXT DEFAULT '',
            weakness TEXT DEFAULT '',
            project TEXT DEFAULT '',
            capacity INTEGER DEFAULT 50,
            sort_order INTEGER DEFAULT 100,
            deleted_at INTEGER DEFAULT NULL,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS projects(
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            goal TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            color TEXT DEFAULT '#0071E3',
            start_date TEXT DEFAULT '',
            deadline TEXT DEFAULT '',
            sort_order INTEGER DEFAULT 100,
            deleted_at INTEGER DEFAULT NULL,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS project_members(
            project_id TEXT NOT NULL,
            character_id TEXT NOT NULL,
            role TEXT DEFAULT '',
            allocation INTEGER DEFAULT 30,
            is_lead INTEGER DEFAULT 0,
            created_at INTEGER NOT NULL,
            PRIMARY KEY(project_id, character_id)
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS tasks(
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            title TEXT NOT NULL,
            descr TEXT DEFAULT '',
            status TEXT DEFAULT 'todo',
            owner_id TEXT DEFAULT '',
            collaborators_json TEXT DEFAULT '[]',
            deadline TEXT DEFAULT '',
            estimate_hours REAL DEFAULT 0,
            actual_hours REAL DEFAULT 0,
            ai_reason TEXT DEFAULT '',
            sort_order INTEGER DEFAULT 100,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            completed_at INTEGER DEFAULT NULL
        )""")

SEED = [
  {"id":"pingfan","cn_name":"平凡","en_name":"Pingfan","func":"团队负责人","years":"8+ 年",
   "avatar_url":"/teamforge-api/avatars/pingfan.png","tags":["战略","决策","带队"],
   "skills":{"项目管理":95,"战略大局":95,"沟通协调":88,"数据分析":80,"商业化":82,"用户运营":78,
             "市场推广":75,"本地化":65,"创意策划":80,"审美":75,"执行力":88,"抗压":92},
   "bio":"团队大脑。其余信息 <em>pending</em>，等他自填或你补。","style":"战略型带队人",
   "strengths":"待补","weakness":"","project":"GNG","capacity":90,"sort_order":10},
  {"id":"charles","cn_name":"刘伟","en_name":"Charles","func":"数据 / 产品","years":"6 年",
   "avatar_url":"/teamforge-api/avatars/charles.png","tags":["数据","开拓","项目"],
   "skills":{"项目管理":92,"战略大局":90,"沟通协调":78,"数据分析":95,"商业化":88,"用户运营":82,
             "市场推广":80,"本地化":55,"创意策划":72,"审美":65,"执行力":86,"抗压":82},
   "bio":"Free Fire 市场 → Blockman Go 商业化 → 中台数据 PM → AOV live ops。<em>逻辑闭环的全能型操盘手</em>，能数据、能产品、能管项目。",
   "style":"数据驱动的全能型操盘手","strengths":"逻辑性强、思路清晰、性格好相处、擅长管理 / 开拓项目",
   "weakness":"","project":"GNG","capacity":85,"sort_order":20},
  {"id":"chenchen","cn_name":"张鱼哥","en_name":"Chenchen","func":"活跃 / 调研","years":"5 年",
   "avatar_url":"/teamforge-api/avatars/chenchen.png","tags":["创意","审美","活跃"],
   "skills":{"项目管理":80,"战略大局":78,"沟通协调":60,"数据分析":75,"商业化":72,"用户运营":92,
             "市场推广":68,"本地化":60,"创意策划":95,"审美":93,"执行力":90,"抗压":80},
   "bio":"灌篮高手手游活跃 → MOBA 产品 → 非对称竞技产品 → Total Football 活跃。<em>内秀型创意操盘</em>，审美在线、稳健执行，<em>不爱站台</em>但点子准。",
   "style":"内秀创意型活跃","strengths":"创意点子、稳健执行、审美在线","weakness":"沟通展示",
   "project":"GNG","capacity":80,"sort_order":30},
  {"id":"yaokuang","cn_name":"张尧匡","en_name":"Yaokuang","func":"市场","years":"7 年",
   "avatar_url":"/teamforge-api/avatars/yaokuang.png","tags":["市场","大局","细心"],
   "skills":{"项目管理":82,"战略大局":90,"沟通协调":92,"数据分析":75,"商业化":72,"用户运营":68,
             "市场推广":95,"本地化":80,"创意策划":72,"审美":74,"执行力":90,"抗压":80},
   "bio":"AOV 市场运营 7 年。<em>对外沟通顶</em>、大局意识强、细心到位。市场专精，能扛对外接口。",
   "style":"资深市场操盘 · 对外担当","strengths":"对外沟通、大局意识、逻辑、细心","weakness":"",
   "project":"GNG","capacity":78,"sort_order":40},
  {"id":"peicheng","cn_name":"郑沛城","en_name":"Peicheng","func":"产品","years":"4 年",
   "avatar_url":"/teamforge-api/avatars/peicheng.png","tags":["沉稳","执行","可靠"],
   "skills":{"项目管理":78,"战略大局":72,"沟通协调":76,"数据分析":72,"商业化":75,"用户运营":86,
             "市场推广":65,"本地化":65,"创意策划":70,"审美":75,"执行力":90,"抗压":93},
   "bio":"暖暖产品运营 → Total Football 产品运营。<em>情绪稳定</em>、有经验，活儿托付得放心，遇事不慌。",
   "style":"沉稳老练的可靠手","strengths":"情绪稳定、有经验","weakness":"","project":"GNG",
   "capacity":72,"sort_order":50},
  {"id":"huangyu","cn_name":"黄宇","en_name":"DeeDee","func":"产品 / 本地化","years":"2 年",
   "avatar_url":"/teamforge-api/avatars/huangyu.png","tags":["社交","跟进","本地化"],
   "skills":{"项目管理":72,"战略大局":58,"沟通协调":92,"数据分析":60,"商业化":60,"用户运营":76,
             "市场推广":62,"本地化":82,"创意策划":65,"审美":62,"执行力":86,"抗压":72},
   "bio":"一念逍遥线上运营出身。<em>团队润滑剂</em>、社交沟通强、事项跟进不放过细节。本地化方向潜力大。",
   "style":"团队润滑剂 · 沟通跟进担当","strengths":"社交、沟通、跟进事项","weakness":"",
   "project":"GNG","capacity":75,"sort_order":60},
]

def seed_if_empty():
    with db() as c:
        n = c.execute("SELECT COUNT(*) FROM characters").fetchone()[0]
        if n > 0: return
        now = int(time.time())
        for s in SEED:
            c.execute("""INSERT INTO characters(id,cn_name,en_name,func,years,avatar_url,tags_json,
                skills_json,bio,style,strengths,weakness,project,capacity,sort_order,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (s["id"], s["cn_name"], s["en_name"], s["func"], s["years"], s["avatar_url"],
                 json.dumps(s["tags"],ensure_ascii=False), json.dumps(s["skills"],ensure_ascii=False),
                 s["bio"], s["style"], s["strengths"], s["weakness"], s["project"],
                 s["capacity"], s["sort_order"], now, now))

init_db()
seed_if_empty()

# ---------- helpers ----------
def row_to_char(r):
    return {
        "id": r["id"], "cn_name": r["cn_name"], "en_name": r["en_name"],
        "func": r["func"], "years": r["years"], "avatar_url": r["avatar_url"],
        "tags": json.loads(r["tags_json"] or "[]"),
        "skills": json.loads(r["skills_json"] or "{}"),
        "bio": r["bio"], "style": r["style"], "strengths": r["strengths"],
        "weakness": r["weakness"], "project": r["project"],
        "capacity": r["capacity"], "sort_order": r["sort_order"],
        "deleted_at": r["deleted_at"],
        "created_at": r["created_at"], "updated_at": r["updated_at"],
    }

# ---------- app ----------
app = FastAPI(title="TeamForge API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/api/characters")
def list_chars(include_deleted: int = 0):
    with db() as c:
        if include_deleted:
            rows = c.execute("SELECT * FROM characters ORDER BY sort_order ASC, created_at ASC").fetchall()
        else:
            rows = c.execute("SELECT * FROM characters WHERE deleted_at IS NULL ORDER BY sort_order ASC, created_at ASC").fetchall()
        return [row_to_char(r) for r in rows]

@app.get("/api/characters/trash")
def list_trash():
    with db() as c:
        rows = c.execute("SELECT * FROM characters WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC").fetchall()
        return [row_to_char(r) for r in rows]

@app.get("/api/characters/{cid}")
def get_char(cid: str):
    with db() as c:
        r = c.execute("SELECT * FROM characters WHERE id=?", (cid,)).fetchone()
        if not r: raise HTTPException(404)
        return row_to_char(r)

class CharPatch(BaseModel):
    cn_name: Optional[str] = None
    en_name: Optional[str] = None
    func: Optional[str] = None
    years: Optional[str] = None
    avatar_url: Optional[str] = None
    tags: Optional[list] = None
    skills: Optional[dict] = None
    bio: Optional[str] = None
    style: Optional[str] = None
    strengths: Optional[str] = None
    weakness: Optional[str] = None
    project: Optional[str] = None
    capacity: Optional[int] = None
    sort_order: Optional[int] = None

@app.patch("/api/characters/{cid}")
def patch_char(cid: str, p: CharPatch):
    with db() as c:
        r = c.execute("SELECT * FROM characters WHERE id=?", (cid,)).fetchone()
        if not r: raise HTTPException(404)
        d = p.model_dump(exclude_none=True)
        sets, vals = [], []
        for k, v in d.items():
            if k == "tags":
                sets.append("tags_json=?"); vals.append(json.dumps(v, ensure_ascii=False))
            elif k == "skills":
                sets.append("skills_json=?"); vals.append(json.dumps(v, ensure_ascii=False))
            else:
                sets.append(f"{k}=?"); vals.append(v)
        if not sets: return row_to_char(r)
        sets.append("updated_at=?"); vals.append(int(time.time()))
        vals.append(cid)
        c.execute(f"UPDATE characters SET {','.join(sets)} WHERE id=?", vals)
        r2 = c.execute("SELECT * FROM characters WHERE id=?", (cid,)).fetchone()
        return row_to_char(r2)

class CharCreate(BaseModel):
    cn_name: str
    en_name: Optional[str] = ""
    func: Optional[str] = ""
    years: Optional[str] = ""
    avatar_url: Optional[str] = ""
    tags: Optional[list] = []
    skills: Optional[dict] = None
    bio: Optional[str] = ""
    style: Optional[str] = ""
    strengths: Optional[str] = ""
    weakness: Optional[str] = ""
    project: Optional[str] = ""
    capacity: Optional[int] = 50

DEFAULT_SKILLS = {k: 50 for k in ["项目管理","战略大局","沟通协调","数据分析","商业化","用户运营",
                                   "市场推广","本地化","创意策划","审美","执行力","抗压"]}

@app.post("/api/characters")
def create_char(p: CharCreate):
    cid = uuid.uuid4().hex[:8]
    now = int(time.time())
    skills = p.skills or DEFAULT_SKILLS
    with db() as c:
        max_sort = c.execute("SELECT MAX(sort_order) FROM characters").fetchone()[0] or 0
        c.execute("""INSERT INTO characters(id,cn_name,en_name,func,years,avatar_url,tags_json,
            skills_json,bio,style,strengths,weakness,project,capacity,sort_order,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (cid, p.cn_name, p.en_name, p.func, p.years, p.avatar_url,
             json.dumps(p.tags, ensure_ascii=False), json.dumps(skills, ensure_ascii=False),
             p.bio, p.style, p.strengths, p.weakness, p.project,
             p.capacity, max_sort + 10, now, now))
        r = c.execute("SELECT * FROM characters WHERE id=?", (cid,)).fetchone()
        return row_to_char(r)

@app.delete("/api/characters/{cid}")
def soft_delete(cid: str):
    with db() as c:
        r = c.execute("SELECT id FROM characters WHERE id=?", (cid,)).fetchone()
        if not r: raise HTTPException(404)
        c.execute("UPDATE characters SET deleted_at=?, updated_at=? WHERE id=?",
                  (int(time.time()), int(time.time()), cid))
        return {"ok": True}

@app.post("/api/characters/{cid}/restore")
def restore(cid: str):
    with db() as c:
        r = c.execute("SELECT id FROM characters WHERE id=?", (cid,)).fetchone()
        if not r: raise HTTPException(404)
        c.execute("UPDATE characters SET deleted_at=NULL, updated_at=? WHERE id=?",
                  (int(time.time()), cid))
        return {"ok": True}

@app.delete("/api/characters/{cid}/purge")
def hard_delete(cid: str):
    with db() as c:
        r = c.execute("SELECT id, deleted_at FROM characters WHERE id=?", (cid,)).fetchone()
        if not r: raise HTTPException(404)
        if r["deleted_at"] is None:
            raise HTTPException(400, "must soft-delete first")
        c.execute("DELETE FROM characters WHERE id=?", (cid,))
        return {"ok": True}

class ReorderReq(BaseModel):
    ids: list[str]  # in desired order

@app.post("/api/characters/reorder")
def reorder(req: ReorderReq):
    now = int(time.time())
    with db() as c:
        for i, cid in enumerate(req.ids):
            c.execute("UPDATE characters SET sort_order=?, updated_at=? WHERE id=?",
                      ((i + 1) * 10, now, cid))
        return {"ok": True}

@app.post("/api/characters/{cid}/avatar")
async def upload_avatar(cid: str, file: UploadFile = File(...)):
    with db() as c:
        r = c.execute("SELECT id FROM characters WHERE id=?", (cid,)).fetchone()
        if not r: raise HTTPException(404)
    ext = (file.filename.rsplit(".", 1)[-1] if "." in file.filename else "png").lower()
    if ext not in ("png", "jpg", "jpeg", "webp", "gif"):
        raise HTTPException(400, "bad ext")
    dest = AVATARS / f"{cid}.{ext}"
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    url = f"/teamforge-api/avatars/{cid}.{ext}?t={int(time.time())}"
    with db() as c:
        c.execute("UPDATE characters SET avatar_url=?, updated_at=? WHERE id=?",
                  (url, int(time.time()), cid))
        r2 = c.execute("SELECT * FROM characters WHERE id=?", (cid,)).fetchone()
        return row_to_char(r2)

@app.get("/api/avatars/{name}")
def get_avatar(name: str):
    p = AVATARS / name.split("?")[0]
    if not p.exists(): raise HTTPException(404)
    return FileResponse(p)

# ============ PROJECTS ============
def row_to_project(r, members=None):
    return {
        "id": r["id"], "name": r["name"], "goal": r["goal"],
        "status": r["status"], "color": r["color"],
        "start_date": r["start_date"], "deadline": r["deadline"],
        "sort_order": r["sort_order"], "deleted_at": r["deleted_at"],
        "created_at": r["created_at"], "updated_at": r["updated_at"],
        "members": members or [],
    }

def project_members(c, pid):
    rows = c.execute("""SELECT pm.*, ch.cn_name, ch.avatar_url FROM project_members pm
                        LEFT JOIN characters ch ON ch.id = pm.character_id
                        WHERE pm.project_id=? ORDER BY pm.is_lead DESC, pm.allocation DESC""", (pid,)).fetchall()
    return [{"character_id": r["character_id"], "cn_name": r["cn_name"],
             "avatar_url": r["avatar_url"], "role": r["role"],
             "allocation": r["allocation"], "is_lead": bool(r["is_lead"])} for r in rows]

class ProjectIn(BaseModel):
    name: str
    goal: Optional[str] = ""
    status: Optional[str] = "active"
    color: Optional[str] = "#0071E3"
    start_date: Optional[str] = ""
    deadline: Optional[str] = ""

class ProjectPatch(BaseModel):
    name: Optional[str] = None
    goal: Optional[str] = None
    status: Optional[str] = None
    color: Optional[str] = None
    start_date: Optional[str] = None
    deadline: Optional[str] = None
    sort_order: Optional[int] = None

@app.get("/api/projects")
def list_projects(include_deleted: int = 0):
    with db() as c:
        q = "SELECT * FROM projects"
        if not include_deleted: q += " WHERE deleted_at IS NULL"
        q += " ORDER BY sort_order ASC, created_at ASC"
        rows = c.execute(q).fetchall()
        return [row_to_project(r, project_members(c, r["id"])) for r in rows]

@app.get("/api/projects/trash")
def trash_projects():
    with db() as c:
        rows = c.execute("SELECT * FROM projects WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC").fetchall()
        return [row_to_project(r, project_members(c, r["id"])) for r in rows]

@app.get("/api/projects/{pid}")
def get_project(pid: str):
    with db() as c:
        r = c.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
        if not r: raise HTTPException(404)
        return row_to_project(r, project_members(c, pid))

@app.post("/api/projects")
def create_project(p: ProjectIn):
    pid = uuid.uuid4().hex[:8]
    now = int(time.time())
    with db() as c:
        max_sort = c.execute("SELECT MAX(sort_order) FROM projects").fetchone()[0] or 0
        c.execute("""INSERT INTO projects(id,name,goal,status,color,start_date,deadline,sort_order,created_at,updated_at)
                     VALUES(?,?,?,?,?,?,?,?,?,?)""",
                  (pid, p.name, p.goal, p.status, p.color, p.start_date, p.deadline, max_sort+10, now, now))
        r = c.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
        return row_to_project(r, [])

@app.patch("/api/projects/{pid}")
def patch_project(pid: str, p: ProjectPatch):
    with db() as c:
        r = c.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
        if not r: raise HTTPException(404)
        d = p.model_dump(exclude_none=True)
        if not d: return row_to_project(r, project_members(c, pid))
        sets = [f"{k}=?" for k in d.keys()]
        vals = list(d.values()) + [int(time.time()), pid]
        sets.append("updated_at=?")
        c.execute(f"UPDATE projects SET {','.join(sets)} WHERE id=?", vals)
        r2 = c.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
        return row_to_project(r2, project_members(c, pid))

@app.delete("/api/projects/{pid}")
def soft_delete_project(pid: str):
    with db() as c:
        r = c.execute("SELECT id FROM projects WHERE id=?", (pid,)).fetchone()
        if not r: raise HTTPException(404)
        now = int(time.time())
        c.execute("UPDATE projects SET deleted_at=?, updated_at=? WHERE id=?", (now, now, pid))
        return {"ok": True}

@app.post("/api/projects/{pid}/restore")
def restore_project(pid: str):
    with db() as c:
        c.execute("UPDATE projects SET deleted_at=NULL, updated_at=? WHERE id=?", (int(time.time()), pid))
        return {"ok": True}

@app.delete("/api/projects/{pid}/purge")
def purge_project(pid: str):
    with db() as c:
        r = c.execute("SELECT id, deleted_at FROM projects WHERE id=?", (pid,)).fetchone()
        if not r: raise HTTPException(404)
        if r["deleted_at"] is None: raise HTTPException(400, "must soft-delete first")
        c.execute("DELETE FROM project_members WHERE project_id=?", (pid,))
        c.execute("DELETE FROM tasks WHERE project_id=?", (pid,))
        c.execute("DELETE FROM projects WHERE id=?", (pid,))
        return {"ok": True}

class MemberIn(BaseModel):
    character_id: str
    role: Optional[str] = ""
    allocation: Optional[int] = 30
    is_lead: Optional[bool] = False

@app.post("/api/projects/{pid}/members")
def add_member(pid: str, m: MemberIn):
    with db() as c:
        if not c.execute("SELECT 1 FROM projects WHERE id=?", (pid,)).fetchone(): raise HTTPException(404)
        if not c.execute("SELECT 1 FROM characters WHERE id=?", (m.character_id,)).fetchone(): raise HTTPException(404, "char not found")
        c.execute("""INSERT OR REPLACE INTO project_members(project_id,character_id,role,allocation,is_lead,created_at)
                     VALUES(?,?,?,?,?,?)""",
                  (pid, m.character_id, m.role, m.allocation, int(bool(m.is_lead)), int(time.time())))
        return {"ok": True, "members": project_members(c, pid)}

class MemberPatch(BaseModel):
    role: Optional[str] = None
    allocation: Optional[int] = None
    is_lead: Optional[bool] = None

@app.patch("/api/projects/{pid}/members/{cid}")
def patch_member(pid: str, cid: str, m: MemberPatch):
    with db() as c:
        d = m.model_dump(exclude_none=True)
        if "is_lead" in d: d["is_lead"] = int(bool(d["is_lead"]))
        if not d: return {"ok": True}
        sets = [f"{k}=?" for k in d.keys()]
        vals = list(d.values()) + [pid, cid]
        c.execute(f"UPDATE project_members SET {','.join(sets)} WHERE project_id=? AND character_id=?", vals)
        return {"ok": True}

@app.delete("/api/projects/{pid}/members/{cid}")
def del_member(pid: str, cid: str):
    with db() as c:
        c.execute("DELETE FROM project_members WHERE project_id=? AND character_id=?", (pid, cid))
        return {"ok": True}

# ============ TASKS ============
def row_to_task(r):
    return {
        "id": r["id"], "project_id": r["project_id"], "title": r["title"],
        "descr": r["descr"], "status": r["status"], "owner_id": r["owner_id"],
        "collaborators": json.loads(r["collaborators_json"] or "[]"),
        "deadline": r["deadline"], "estimate_hours": r["estimate_hours"],
        "actual_hours": r["actual_hours"], "ai_reason": r["ai_reason"],
        "sort_order": r["sort_order"],
        "created_at": r["created_at"], "updated_at": r["updated_at"],
        "completed_at": r["completed_at"],
    }

class TaskIn(BaseModel):
    project_id: str
    title: str
    descr: Optional[str] = ""
    status: Optional[str] = "todo"
    owner_id: Optional[str] = ""
    collaborators: Optional[list] = []
    deadline: Optional[str] = ""
    estimate_hours: Optional[float] = 0
    ai_reason: Optional[str] = ""

class TaskPatch(BaseModel):
    title: Optional[str] = None
    descr: Optional[str] = None
    status: Optional[str] = None
    owner_id: Optional[str] = None
    collaborators: Optional[list] = None
    deadline: Optional[str] = None
    estimate_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    sort_order: Optional[int] = None

@app.get("/api/tasks")
def list_tasks(project_id: Optional[str] = None, status: Optional[str] = None):
    with db() as c:
        q = "SELECT * FROM tasks WHERE 1=1"
        args = []
        if project_id: q += " AND project_id=?"; args.append(project_id)
        if status: q += " AND status=?"; args.append(status)
        q += " ORDER BY sort_order ASC, created_at ASC"
        rows = c.execute(q, args).fetchall()
        return [row_to_task(r) for r in rows]

@app.post("/api/tasks")
def create_task(p: TaskIn):
    tid = uuid.uuid4().hex[:8]
    now = int(time.time())
    with db() as c:
        max_sort = c.execute("SELECT MAX(sort_order) FROM tasks WHERE project_id=?", (p.project_id,)).fetchone()[0] or 0
        c.execute("""INSERT INTO tasks(id,project_id,title,descr,status,owner_id,collaborators_json,
                     deadline,estimate_hours,ai_reason,sort_order,created_at,updated_at)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (tid, p.project_id, p.title, p.descr, p.status, p.owner_id,
                   json.dumps(p.collaborators, ensure_ascii=False), p.deadline,
                   p.estimate_hours, p.ai_reason, max_sort+10, now, now))
        r = c.execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone()
        return row_to_task(r)

@app.patch("/api/tasks/{tid}")
def patch_task(tid: str, p: TaskPatch):
    with db() as c:
        r = c.execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone()
        if not r: raise HTTPException(404)
        d = p.model_dump(exclude_none=True)
        sets, vals = [], []
        for k, v in d.items():
            if k == "collaborators":
                sets.append("collaborators_json=?"); vals.append(json.dumps(v, ensure_ascii=False))
            else:
                sets.append(f"{k}=?"); vals.append(v)
        now = int(time.time())
        # auto set completed_at when moving to done
        if d.get("status") == "done" and r["status"] != "done":
            sets.append("completed_at=?"); vals.append(now)
        if d.get("status") and d.get("status") not in ("done","archived") and r["status"] in ("done","archived"):
            sets.append("completed_at=NULL")
        if not sets: return row_to_task(r)
        sets.append("updated_at=?"); vals.append(now); vals.append(tid)
        c.execute(f"UPDATE tasks SET {','.join(sets)} WHERE id=?", vals)
        r2 = c.execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone()
        return row_to_task(r2)

@app.delete("/api/tasks/{tid}")
def delete_task(tid: str):
    with db() as c:
        c.execute("DELETE FROM tasks WHERE id=?", (tid,))
        return {"ok": True}

# ============ load summary on characters ============
@app.get("/api/characters_with_load")
def chars_with_load():
    with db() as c:
        rows = c.execute("SELECT * FROM characters WHERE deleted_at IS NULL ORDER BY sort_order").fetchall()
        out = []
        for r in rows:
            ch = row_to_char(r)
            loads = c.execute("""SELECT pm.allocation, pm.role, pm.is_lead, p.id pid, p.name pname, p.color
                                 FROM project_members pm JOIN projects p ON p.id=pm.project_id
                                 WHERE pm.character_id=? AND p.deleted_at IS NULL AND p.status!='archived'""", (r["id"],)).fetchall()
            ch["project_load"] = [{"project_id": l["pid"], "project_name": l["pname"], "color": l["color"],
                                    "allocation": l["allocation"], "role": l["role"], "is_lead": bool(l["is_lead"])} for l in loads]
            ch["computed_capacity"] = sum(l["allocation"] for l in loads)
            # active tasks (todo + doing) assigned
            tk = c.execute("""SELECT COUNT(*) cnt, SUM(CASE WHEN status='doing' THEN 1 ELSE 0 END) doing,
                                     SUM(CASE WHEN status='todo' THEN 1 ELSE 0 END) todo
                              FROM tasks WHERE owner_id=? AND status IN ('todo','doing')""", (r["id"],)).fetchone()
            ch["active_tasks"] = tk["cnt"] or 0
            ch["doing_tasks"] = tk["doing"] or 0
            ch["todo_tasks"] = tk["todo"] or 0
            # overdue
            today = time.strftime("%Y-%m-%d")
            od = c.execute("""SELECT COUNT(*) cnt FROM tasks WHERE owner_id=? AND status IN ('todo','doing')
                              AND deadline != '' AND deadline < ?""", (r["id"], today)).fetchone()
            ch["overdue_tasks"] = od["cnt"] or 0
            out.append(ch)
        return out

@app.get("/api/my_tasks")
def my_tasks(owner_id: str):
    """List all tasks across projects assigned to a character."""
    with db() as c:
        rows = c.execute("""SELECT t.*, p.name proj_name, p.color proj_color
                            FROM tasks t JOIN projects p ON p.id=t.project_id
                            WHERE t.owner_id=? AND p.deleted_at IS NULL
                            ORDER BY CASE WHEN t.deadline='' THEN 1 ELSE 0 END, t.deadline ASC, t.created_at ASC""", (owner_id,)).fetchall()
        return [dict(row_to_task(r), proj_name=r["proj_name"], proj_color=r["proj_color"]) for r in rows]

# ============ AI ============
import urllib.request as _ur
AI_GATEWAY = os.environ.get("AI_GATEWAY", "https://new-api.openclaw.ingarena.net")
AI_KEY = os.environ.get("AI_KEY", "sk-y5OvzZALUDqXBnSHcFKCdNcmBfvbD8r2NJG27EOAllObZonR")
AI_MODEL = os.environ.get("AI_MODEL", "claude-sonnet-4-6")

def ai_chat(messages, max_tokens=1200, system=None, temperature=0.4):
    body = {"model": AI_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    if system: body["system"] = system
    t0 = time.time()
    req = _ur.Request(f"{AI_GATEWAY}/v1/chat/completions",
                      data=json.dumps(body).encode(),
                      headers={"Content-Type":"application/json","Authorization":f"Bearer {AI_KEY}"},
                      method="POST")
    try:
        with _ur.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f"[AI] ERR {e}")
        raise HTTPException(502, f"AI gateway: {e}")
    dt = time.time() - t0
    txt = data.get("choices",[{}])[0].get("message",{}).get("content","") or ""
    usage = data.get("usage",{})
    print(f"[AI] {dt:.1f}s tokens={usage} reply[:200]={txt[:200]!r}")
    return txt

@app.post("/api/projects/{pid}/ai_checkup")
def ai_checkup(pid: str):
    with db() as c:
        p = c.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
        if not p: raise HTTPException(404)
        members = project_members(c, pid)
        # Fetch each member's skills
        member_full = []
        for m in members:
            ch = c.execute("SELECT cn_name, style, skills_json, strengths, weakness FROM characters WHERE id=?", (m["character_id"],)).fetchone()
            if not ch: continue
            member_full.append({
                "name": ch["cn_name"], "role": m["role"], "allocation": m["allocation"],
                "is_lead": m["is_lead"], "style": ch["style"],
                "skills": json.loads(ch["skills_json"] or "{}"),
                "strengths": ch["strengths"], "weakness": ch["weakness"]
            })
        tasks = c.execute("SELECT title, status, owner_id, deadline FROM tasks WHERE project_id=?", (pid,)).fetchall()
        task_summary = []
        for t in tasks:
            owner_name = ""
            if t["owner_id"]:
                row = c.execute("SELECT cn_name FROM characters WHERE id=?", (t["owner_id"],)).fetchone()
                if row: owner_name = row["cn_name"]
            task_summary.append({"title": t["title"], "status": t["status"], "owner": owner_name, "deadline": t["deadline"]})

    system = "输出严格按照 user 提供的示例格式。一个字都不能多写。不要加额外 H1 标题、不要引用块、不要表格、不要 emoji、不要分隔线。只能有 4 个二级标题：目标进度 / 人员配置 / 风险 / 建议。中文。人话，不要 AI 口吻。"
    fewshot = (
        "示例（另一个项目的巡检，格式严格学这个）：\n\n"
        "## 目标进度\n项目刚启动 2 周，8 条任务刚起穿，进展低于预期。主要是调研阶段还没出结论。\n\n"
        "## 人员配置\n刘伟作为 Lead 手里 3 个任务并行，偏满；黄宇 30% 投入但手上任务空。\n\n"
        "## 风险\n- 调研任务没设 deadline，容易拖到下个月\n- 张鱼哥在本项目是全职，但同时被拉去另两个项目会、实际交付会打折\n\n"
        "## 建议\n- 今天给调研任务填上 deadline\n- 下周开个 30 分钟对齐会，看是不是往方案阶段走\n"
    )
    user_payload = {
        "project": {"name": p["name"], "goal": p["goal"], "deadline": p["deadline"], "status": p["status"]},
        "team": member_full,
        "tasks": task_summary,
        "task_count_by_status": {s: sum(1 for t in tasks if t["status"]==s) for s in ["todo","doing","done","archived"]}
    }
    text = ai_chat(
        messages=[{"role":"user","content":fewshot + "\n现在请用上面一模一样的格式和长度，对下面这个项目出报告。不要加 H1、不要加表格、不要 emoji：\n\n" + json.dumps(user_payload, ensure_ascii=False, indent=2)}],
        system=system, max_tokens=550, temperature=0.4
    )

    return {"report": text, "generated_at": int(time.time())}

def _repair_quotes(s):
    """Escape unescaped inner double-quotes inside JSON string values."""
    out = []
    in_str = False
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if not in_str:
            out.append(ch)
            if ch == '"':
                in_str = True
            i += 1
            continue
        # inside string
        if ch == '\\':
            out.append(ch)
            if i+1 < n: out.append(s[i+1])
            i += 2
            continue
        if ch == '"':
            # peek ahead, skipping whitespace, to decide if this terminates the string
            j = i + 1
            while j < n and s[j] in ' \t\r\n': j += 1
            nxt = s[j] if j < n else ''
            if nxt in (',', ':', '}', ']', ''):
                out.append('"')
                in_str = False
            else:
                out.append('\\"')
            i += 1
            continue
        out.append(ch)
        i += 1
    return ''.join(out)

def _extract_json(text):
    """Extract JSON object/array from LLM output even if wrapped in code fences or prose."""
    import re
    m = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if m: text = m.group(1)
    text = text.strip()
    first_obj = text.find("{")
    first_arr = text.find("[")
    candidates = []
    if first_arr != -1 and (first_obj == -1 or first_arr < first_obj):
        candidates.append((first_arr, "]"))
    if first_obj != -1:
        candidates.append((first_obj, "}"))
    if first_arr != -1 and first_arr >= (first_obj if first_obj!=-1 else 0):
        candidates.append((first_arr, "]"))
    for start, closer in candidates:
        end = text.rfind(closer)
        if end > start:
            chunk = text[start:end+1]
            try:
                return json.loads(chunk)
            except Exception:
                try:
                    return json.loads(_repair_quotes(chunk))
                except Exception:
                    continue
    raise ValueError(f"could not parse JSON from: {text[:200]}")

def _gather_team(c, pid):
    members = project_members(c, pid)
    out = []
    for m in members:
        ch = c.execute("SELECT cn_name, style, skills_json, strengths, weakness FROM characters WHERE id=?", (m["character_id"],)).fetchone()
        if not ch: continue
        out.append({
            "id": m["character_id"], "name": ch["cn_name"], "role": m["role"],
            "allocation": m["allocation"], "is_lead": bool(m["is_lead"]),
            "style": ch["style"], "skills": json.loads(ch["skills_json"] or "{}"),
            "strengths": ch["strengths"], "weakness": ch["weakness"]
        })
    return out

# ---- B-2.1 任务自动拆解 ----
@app.post("/api/projects/{pid}/ai_breakdown")
def ai_breakdown(pid: str, body: dict = Body(...)):
    goal = (body.get("goal") or "").strip()
    extra = (body.get("context") or "").strip()
    with db() as c:
        p = c.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
        if not p: raise HTTPException(404)
        if not goal: goal = p["goal"] or ""
        team = _gather_team(c, pid)
    system = ("你是资深项目经理。把项目目标拆成 10-16 条可执行任务。只输出 JSON 数组，其他都不要（不要 markdown、不要 ```、不要解释、不要 emoji）。")
    fewshot_user = '示例：\ngoal="上线新手引导"\nteam=[{"id":"a","name":"小明"}]\n输出：'
    fewshot_out = '[\n  {"title":"梳理新手引导需求文档","descr":"明确目标人群和关键路径","estimate_hours":4,"suggested_owner_id":"a","reason":"他熟悉产品"},\n  {"title":"设计引导流程线框图","descr":"交互路径 + 奖励点","estimate_hours":8,"suggested_owner_id":"a","reason":"需要创意能力"}\n]'
    user_payload = {"goal": goal, "context": extra, "team": [{"id":t["id"],"name":t["name"],"role":t["role"],"allocation":t["allocation"],"is_lead":t["is_lead"],"strengths":t["strengths"],"skills":t["skills"]} for t in team]}
    text = ai_chat(
        messages=[
            {"role":"user","content": fewshot_user + "\n" + fewshot_out + "\n\n现在拆这个项目，只输出 JSON 数组，schema 跟示例一样（title/descr/estimate_hours/suggested_owner_id/reason）：\n\n"+json.dumps(user_payload, ensure_ascii=False, indent=2)}
        ],
        system=system, max_tokens=3500, temperature=0.5
    )
    try:
        tasks = _extract_json(text)
        if not isinstance(tasks, list): raise ValueError("not a list")
    except Exception as e:
        raise HTTPException(502, f"AI 输出解析失败：{e}")
    valid_ids = {t["id"] for t in team}
    cleaned = []
    for t in tasks[:20]:
        if not isinstance(t, dict) or not t.get("title"): continue
        owner = t.get("suggested_owner_id")
        if owner not in valid_ids: owner = None
        cleaned.append({
            "title": str(t.get("title","")).strip()[:80],
            "descr": str(t.get("descr","")).strip()[:200],
            "estimate_hours": float(t.get("estimate_hours") or 0),
            "suggested_owner_id": owner,
            "reason": str(t.get("reason","")).strip()[:60]
        })
    return {"tasks": cleaned, "generated_at": int(time.time())}

# ---- B-2.2 推荐负责人 ----
@app.post("/api/tasks/ai_suggest_owner")
def ai_suggest_owner(body: dict = Body(...)):
    pid = body.get("project_id")
    title = (body.get("title") or "").strip()
    descr = (body.get("descr") or "").strip()
    deadline = body.get("deadline") or ""
    if not pid or not title: raise HTTPException(400, "project_id + title 必填")
    with db() as c:
        team = _gather_team(c, pid)
        # current loads
        load_map = {}
        for t in team:
            rows = c.execute("SELECT status FROM tasks WHERE owner_id=? AND status IN ('todo','doing')", (t["id"],)).fetchall()
            load_map[t["id"]] = len(rows)
    enriched = [{**t, "current_open_tasks": load_map.get(t["id"],0)} for t in team]
    system = ("你是项目经理。只输出 JSON 数组（3 条），其他都不要（不要 markdown、不要 emoji、不要表格、不要标题、不要解释）。评分综合技能匹配 / 项目内角色 / 当前任务负载 / allocation。")
    fewshot_out = '[{"character_id":"a","score":92,"reason":"本地化主力且任务轻"},{"character_id":"b","score":78,"reason":"沟通强但偏满"},{"character_id":"c","score":65,"reason":"技能偏弱中选手"}]'
    text = ai_chat(
        messages=[
            {"role":"user","content":"示例输出格式（只要 JSON，别的都不要）：\n"+fewshot_out+"\n\n现在推荐这条任务的负责人，同样 schema：\n"+json.dumps({"task":{"title":title,"descr":descr,"deadline":deadline},"team":enriched}, ensure_ascii=False, indent=2)}
        ],
        system=system, max_tokens=800, temperature=0.4
    )
    try:
        arr = _extract_json(text)
        if not isinstance(arr, list): raise ValueError("not a list")
    except Exception as e:
        raise HTTPException(502, f"AI 输出解析失败：{e}")
    valid_ids = {t["id"] for t in team}
    name_map = {t["id"]: t["name"] for t in team}
    out = []
    for c0 in arr[:3]:
        if not isinstance(c0, dict): continue
        cid = c0.get("character_id")
        if cid not in valid_ids: continue
        out.append({
            "character_id": cid, "name": name_map.get(cid),
            "score": int(c0.get("score") or 0),
            "reason": str(c0.get("reason","")).strip()[:40]
        })
    return {"candidates": out, "generated_at": int(time.time())}

# ---- B-2.3 团队评估 ----
@app.post("/api/projects/{pid}/ai_team_eval")
def ai_team_eval(pid: str):
    with db() as c:
        p = c.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
        if not p: raise HTTPException(404)
        team = _gather_team(c, pid)
    # compute coverage server-side (deterministic). 使用 raw skill max（能力天花板），不要 weight by allocation 免得全红。
    skill_keys = ["项目管理","战略大局","沟通协调","数据分析","商业化","用户运营","市场推广","本地化","创意策划","审美","执行力","抗压"]
    coverage = {}
    for k in skill_keys:
        top_skill = 0
        contributors = []
        for t in team:
            v = (t["skills"] or {}).get(k, 0)
            if v >= 70:
                contributors.append({"name": t["name"], "skill": v, "alloc": t["allocation"]})
            if v > top_skill: top_skill = v
        contributors.sort(key=lambda x: x["skill"], reverse=True)
        # green ≥80 top 且有人投入足够, yellow 65-79 或 top高但投入低, red <65
        max_alloc_contrib = max([c["alloc"] for c in contributors], default=0)
        if top_skill >= 80 and max_alloc_contrib >= 50:
            light = "green"
        elif top_skill >= 65 or (top_skill >= 80 and max_alloc_contrib < 50):
            light = "yellow"
        else:
            light = "red"
        coverage[k] = {"score": top_skill, "light": light, "contributors": contributors[:3], "max_alloc": max_alloc_contrib}

    system = ("你是 HR 顾问。只输出 JSON 对象，别的都不要（不要 markdown、不要 emoji、不要解释）。")
    fewshot_out = '{"summary":"团队执行强但创意偷弱","gaps":["创意策划","商业化"],"recruit":[{"role":"创意策划","why":"补足创意发散能力","priority":"high"}]}'
    text = ai_chat(
        messages=[{"role":"user","content":"示例（只 JSON）：\n"+fewshot_out+"\n\n现在评估下面这个项目团队，同样 schema（summary/gaps/recruit）：\n"+json.dumps({"project":{"name":p["name"],"goal":p["goal"]},"team":team,"coverage":coverage}, ensure_ascii=False, indent=2)}],
        system=system, max_tokens=800, temperature=0.4
    )
    try:
        ev = _extract_json(text)
    except Exception as e:
        ev = {"summary":"AI 解析失败，仅显示覆盖图","gaps":[],"recruit":[]}
    return {"coverage": coverage, "eval": ev, "generated_at": int(time.time())}

# ---- B-2.4 全局风险扫描 ----
@app.post("/api/ai_risk_scan")
def ai_risk_scan():
    today = time.strftime("%Y-%m-%d")
    with db() as c:
        projects = c.execute("SELECT id,name,goal,deadline,color FROM projects WHERE deleted_at IS NULL AND status!='archived'").fetchall()
        chars = c.execute("SELECT id,cn_name FROM characters WHERE deleted_at IS NULL").fetchall()
        # overload: sum allocation across active projects
        overload = []
        for ch in chars:
            rows = c.execute("SELECT pm.allocation, p.name FROM project_members pm JOIN projects p ON pm.project_id=p.id WHERE pm.character_id=? AND p.deleted_at IS NULL AND p.status!='archived'", (ch["id"],)).fetchall()
            total = sum(r["allocation"] for r in rows)
            if total > 100:
                overload.append({"name": ch["cn_name"], "total": total, "projects":[r["name"] for r in rows]})
        # overdue
        overdue = []
        for p in projects:
            rows = c.execute("SELECT title, deadline, owner_id, status FROM tasks WHERE project_id=? AND deadline<? AND status IN ('todo','doing')", (p["id"], today)).fetchall()
            for r in rows:
                owner = ""
                if r["owner_id"]:
                    o = c.execute("SELECT cn_name FROM characters WHERE id=?", (r["owner_id"],)).fetchone()
                    if o: owner = o["cn_name"]
                overdue.append({"project":p["name"],"title":r["title"],"deadline":r["deadline"],"owner":owner})
        # stale: doing tasks with no DDL or DDL very far + no owner
        stale = []
        for p in projects:
            rows = c.execute("SELECT title, deadline, owner_id FROM tasks WHERE project_id=? AND status='doing' AND (owner_id IS NULL OR owner_id='') ", (p["id"],)).fetchall()
            for r in rows:
                stale.append({"project":p["name"],"title":r["title"],"deadline":r["deadline"]})
    # AI summary
    payload = {"date": today, "overload": overload, "overdue": overdue[:30], "stale_no_owner": stale[:20], "project_count": len(projects)}
    system = ("你是公司 PMO。只输出 JSON 对象，别的都不要（不要 markdown、不要 emoji、不要解释）。如需在字符串里提任务名或专有名词，用中文《》或「」，不要用英文双引号以免破坏 JSON。")
    fewshot_out = '{"summary":"三个项目报黄灯，其中 AAA 项目偏严重。建议本周介入。","actions":["今天找 XXX 聊 30 分钟拆 AAA 项目任务","本周被谁接手 YYY 项目的逾期项","拉一个周会只看逾期项"]}'
    try:
        text = ai_chat(
            messages=[{"role":"user","content":"示例输出（只 JSON）：\n"+fewshot_out+"\n\n现在扫一遍这些数据，同样 schema：\n"+json.dumps(payload, ensure_ascii=False, indent=2)}],
            system=system, max_tokens=600, temperature=0.4
        )
        ai = _extract_json(text)
    except Exception:
        ai = {"summary":"AI 不可用，仅展示原始数据","actions":[]}
    return {"data": payload, "ai": ai, "generated_at": int(time.time())}

@app.get("/api/health")
def health(): return {"ok": True}
