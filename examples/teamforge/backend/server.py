"""TeamForge backend v0.1 — character CRUD with soft delete."""
import os, json, sqlite3, time, uuid, shutil
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
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

@app.get("/api/health")
def health(): return {"ok": True}
