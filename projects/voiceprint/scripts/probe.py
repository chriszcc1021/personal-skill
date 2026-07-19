#!/usr/bin/env python3
"""voiceprint Batch0 探针 — 声纹提取 + 音域检测 + 余弦匹配
用途:验证"唱歌能否声纹匹配 + 区分度",不是生产代码。
用法:
  建库:  python probe.py build  <singer_id> <audio1> [audio2 ...]
  匹配:  python probe.py match  <user_audio>
  列表:  python probe.py list
库存于 lib.json(仅向量+元数据,不存音频)。
"""
import sys, os, json, glob
import numpy as np

LIB = os.path.join(os.path.dirname(__file__), "lib.json")

def load_lib():
    if os.path.exists(LIB):
        with open(LIB) as f: return json.load(f)
    return {}

def save_lib(lib):
    with open(LIB, "w") as f: json.dump(lib, f, ensure_ascii=False, indent=2)

def to_wav16k(path):
    """任意格式 → wav 16k mono, 返回临时 wav 路径"""
    import subprocess, tempfile
    out = tempfile.mktemp(suffix=".wav")
    subprocess.run(["ffmpeg", "-y", "-i", path, "-ar", "16000", "-ac", "1", out],
                   capture_output=True, check=True)
    return out

def get_embedding(wav_path):
    """Resemblyzer 提 256维声纹向量"""
    from resemblyzer import VoiceEncoder, preprocess_wav
    wav = preprocess_wav(wav_path)
    encoder = VoiceEncoder(verbose=False)
    return encoder.embed_utterance(wav)

def get_vocal_range(wav_path):
    """librosa pyin 测音域 low/high note + 声部"""
    import librosa
    y, sr = librosa.load(wav_path, sr=16000)
    f0, voiced, _ = librosa.pyin(y, fmin=65, fmax=1000, sr=sr)
    f0v = f0[~np.isnan(f0)]
    if len(f0v) < 5:
        return {"low": None, "high": None, "type": "unknown"}
    lo, hi = float(np.percentile(f0v, 5)), float(np.percentile(f0v, 95))
    lo_note = librosa.hz_to_note(lo); hi_note = librosa.hz_to_note(hi)
    # 简易声部判定(按中位音高)
    med = float(np.median(f0v))
    if med < 130: vtype = "bass 男低音"
    elif med < 175: vtype = "baritone 男中音"
    elif med < 260: vtype = "tenor 男高音/alto 女低音"
    elif med < 350: vtype = "mezzo 女中音"
    else: vtype = "soprano 女高音"
    return {"low": lo_note, "high": hi_note, "type": vtype,
            "low_hz": round(lo,1), "high_hz": round(hi,1)}

def cosine(a, b):
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def cmd_build(singer_id, audios):
    lib = load_lib()
    embs = []
    for a in audios:
        wav = to_wav16k(a)
        embs.append(get_embedding(wav))
        os.remove(wav)
        print(f"  提取 {a} ✓")
    mean_emb = np.mean(embs, axis=0)
    # 内部一致性:多段之间平均余弦
    if len(embs) > 1:
        sims = [cosine(embs[i], embs[j]) for i in range(len(embs)) for j in range(i+1, len(embs))]
        consistency = round(float(np.mean(sims)), 3)
    else:
        consistency = None
    lib[singer_id] = {"embedding": mean_emb.tolist(), "sample_count": len(audios),
                      "consistency": consistency}
    save_lib(lib)
    print(f"✅ {singer_id} 入库,{len(audios)}段,内部一致性={consistency}")

def cmd_match(user_audio):
    lib = load_lib()
    if not lib:
        print("❌ 库为空,先 build"); return
    wav = to_wav16k(user_audio)
    uemb = get_embedding(wav)
    vrange = get_vocal_range(wav)
    os.remove(wav)
    scored = [(sid, cosine(uemb, d["embedding"])) for sid, d in lib.items()]
    scored.sort(key=lambda x: -x[1])
    print(f"\n🎤 你的音域: {vrange['low']} — {vrange['high']} · {vrange['type']}")
    print(f"📊 声纹匹配排名(原始余弦相似度):")
    for i, (sid, sc) in enumerate(scored, 1):
        bar = "█" * int(sc * 30)
        print(f"  {i:2d}. {sid:14s} {sc:.3f} {bar}")
    top = scored[0][1]; gap = scored[0][1] - scored[1][1] if len(scored) > 1 else 0
    print(f"\n区分度: Top1={top:.3f}, Top1-Top2 gap={gap:.3f}")

def cmd_list():
    lib = load_lib()
    print(f"库中 {len(lib)} 个歌手:")
    for sid, d in lib.items():
        print(f"  {sid}: {d['sample_count']}段, 一致性={d.get('consistency')}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "build": cmd_build(sys.argv[2], sys.argv[3:])
    elif cmd == "match": cmd_match(sys.argv[2])
    elif cmd == "list": cmd_list()
    else: print(__doc__)
