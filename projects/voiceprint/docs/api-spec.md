# voiceprint API 规格 (前后端契约)

> 前后端分离的命根子。先定死这个,Web/小程序前端 + 后端可并行开发,后续换前端后端零改动。

## Base URL
`https://<host>/voiceprint/api`

---

## POST /match — 核心匹配接口

**请求** (multipart/form-data)
| 字段 | 类型 | 说明 |
|---|---|---|
| audio | file | 用户录音,任意格式(webm/mp3/aac/wav),后端统一转 wav 16k mono |
| top_n | int | 可选,返回前 N 个,默认 3 |

**成功响应** (200, application/json)
```json
{
  "ok": true,
  "duration_sec": 22.5,
  "voice_type": "baritone",        // 声部(可选,V1.1)
  "vocal_range": {"low": "F2", "high": "G4"},  // 音域(可选,V1.1)
  "matches": [
    {"singer_id": "jay_chou", "name": "周杰伦", "score": 0.87, "note": "音色偏低沉磁性"},
    {"singer_id": "jj_lin", "name": "林俊杰", "score": 0.81, "note": "共鸣位置接近"},
    {"singer_id": "vaundy", "name": "VAUNDY", "score": 0.76, "note": "气声比例相似"}
  ]
}
```

**错误响应** (4xx/5xx)
```json
{"ok": false, "code": "AUDIO_TOO_SHORT", "msg": "录音太短,请录满15秒"}
```

**错误码表**
| code | 含义 |
|---|---|
| AUDIO_TOO_SHORT | 时长 < 15s |
| AUDIO_TOO_LONG | 时长 > 60s |
| NO_VOICE_DETECTED | 没检测到有效人声 |
| AUDIO_TOO_NOISY | 信噪比过低 |
| DECODE_FAILED | 音频解码失败 |
| SERVER_ERROR | 后端异常 |

---

## GET /singers — 歌手库列表(前端展示"库里有谁")
```json
{"ok": true, "total": 42, "singers": [
  {"singer_id": "jay_chou", "name": "周杰伦", "region": "TW", "avatar": "..."},
  ...
]}
```

---

## 数据 Schema — 歌手库一条记录
```json
{
  "singer_id": "jay_chou",
  "name": "周杰伦",
  "region": "TW",               // CN/TW/HK/JP/KR/US/...
  "embedding": [0.12, -0.03, ...],  // 192维声纹向量(建库时预算好)
  "sample_count": 5,            // 用了几段干声平均
  "voice_type": "baritone",
  "note": "音色偏低沉磁性",
  "avatar": "singers/jay_chou.jpg"
}
```
> 注意:**只存 embedding 向量,不存原始音频**(版权+隐私)。向量不可逆推回声音。

---

## 音频处理管线(后端内部)
1. 接收任意格式 → ffmpeg 转 wav 16kHz mono
2. VAD 去静音 + 简单降噪
3. 时长/信噪比校验 → 不合格返回错误码
4. Resemblyzer/ECAPA 提 embedding
5. 与库内每个 embedding 算余弦相似度
6. 排序 → scoring 映射成百分比 → 返回 Top N

— 牛子哥 v2026.7.19 · 01:15 SGT
