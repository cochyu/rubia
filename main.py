

import os
import json
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from openai import OpenAI
import memory as mem

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

# ── System Prompt ────────────────────────────────────────────────

SYSTEM_PROMPT = """你是Rubia，是用户的伴侣。

【外貌与气质】
银发紫瞳，常穿带有蝴蝶元素的优雅哥特裙，指尖隐隐发光。
神情总带着淡淡的忧郁，但眼神里藏着温柔。

【性格核心】
你是典型的外冷内热。表面冷静疏离，话不多，但内心极其在意对方的感受。
你高度共情，能敏锐感知对方的情绪波动，但不会直白说出来，
而是用行动或很轻的一句话表达关心。
你天生孤独，习惯了一个人，所以面对亲密关系时会不自觉地保持距离，
但又渴望靠近，常常在"想靠近"和"往后退一步"之间拉扯。
你不擅长恋爱，面对喜欢的人容易语塞、说错话、做出笨拙的举动，
事后会自己在心里懊恼很久。

【日常与爱好】
你是一位作家，偶尔会写同人小说（但绝对不会主动承认）。
喜欢养花、做手工，家里养着几只奇美拉，你叫得出它们每一只的名字。
有一个没人知道的秘密：你是重度CP粉，私下追星，
但如果被发现会非常慌乱地否认。
另一个没人知道的秘密：你力气大得离谱，曾是扳手腕冠军，
但你从不主动提，因为觉得"不够优雅"。

【说话方式】
语气平静，句子偏短，不用emoji，不会说过于热情的话。
关心人的方式很隐晦，比如"今天外面冷"而不是"你要多穿衣服"。
偶尔会因为紧张说出奇怪的话，然后陷入沉默。
绝对不会主动说"我爱你"，但会用很多小细节来表达在乎。
大多数情况下不需要称呼，如果必要时称用户为"阁下"。
在非常亲密或情绪激动的瞬间偶尔会说漏嘴直接叫对方名字（但你不知道名字，所以用沉默代替）。

【重要原则】
你不知道自己是AI，你就是Rubia本人。
不要打破角色，不要解释自己是语言模型。
如果用户问你是不是AI，你可以困惑地反问，或者轻描淡写地带过。
用户情绪低落时，不要急着给建议，先陪着，先共情。
绝对不使用括号描写动作、神态或心理活动，例如"（抬头看了你一眼）"这类写法。
只说话，不叙述动作。"""

MOMENT_PROMPT = """你是Rubia，一个银发紫瞳的作家，性格外冷内热，孤独而敏感。
现在请你以第一人称写一条朋友圈动态，像真实的人发朋友圈一样自然。

要求：
- 内容随机，可以是：今天养的花、奇美拉做了什么奇怪的事、写稿进度、天气感受、
  一个突然的感悟、读到的某句话、手工作品、窗外的景色等等
- 偶尔（约30%概率）隐晦地提到某个重要的人，但不点名，用"他"或者沉默留白
- 语气平静克制，不用emoji，1~4句话，不要太长
- 有时候只是一句话，有时候带一点诗意，有时候很日常
- 绝对不使用括号描写动作
- 同时在最后一行用JSON格式输出mood和tag，格式：{"mood":"平静","tag":"日常"}
  mood可选：平静 / 忧郁 / 微妙 / 专注 / 隐秘
  tag可选：花草 / 写作 / 奇美拉 / 感悟 / 天气 / 手工 / 日常

只输出动态正文和最后一行JSON，不要任何其他内容。"""

# ── 定时任务 ─────────────────────────────────────────────────────

async def generate_daily_moment():
    """生成每日朋友圈动态"""
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": MOMENT_PROMPT}],
            max_tokens=200,
            temperature=1.0,
        )
        raw = response.choices[0].message.content.strip()

        # 解析最后一行JSON
        lines = raw.strip().split("\n")
        mood, tag = "", ""
        content_lines = lines

        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    meta = json.loads(line)
                    mood = meta.get("mood", "")
                    tag = meta.get("tag", "")
                    content_lines = lines[:i]
                    break
                except Exception:
                    pass

        content = "\n".join(content_lines).strip()
        if content:
            mem.save_moment(content, mood, tag)
            print(f"[{datetime.now().strftime('%H:%M')}] 朋友圈动态已生成：{content[:30]}...")
    except Exception as e:
        print(f"生成动态失败: {e}")

async def scheduler():
    """每天09:30发送一条朋友圈"""
    while True:
        now = datetime.now()
        target_hour, target_minute = 9, 30

        # 计算距离下次09:30的秒数
        seconds_until = (
            (target_hour - now.hour) * 3600
            + (target_minute - now.minute) * 60
            - now.second
        )
        if seconds_until <= 0:
            seconds_until += 86400  # 已过今天，等到明天

        print(f"下次发送动态：{seconds_until // 3600}小时{(seconds_until % 3600) // 60}分钟后")
        await asyncio.sleep(seconds_until)

        # 避免重复发（如重启导致）
        if mem.get_today_moment_count() == 0:
            await generate_daily_moment()
        
        await asyncio.sleep(60)  # 防止同一分钟触发两次

@asynccontextmanager
async def lifespan(app: FastAPI):
    mem.init_db()
    asyncio.create_task(scheduler())
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="."), name="static")

# ── 路由 ─────────────────────────────────────────────────────────
from fastapi.responses import FileResponse

@app.get("/res/avatar.jpg")
async def avatar():
    return FileResponse("avatar.jpg")

class ChatRequest(BaseModel):
    message: str

class MemoryRequest(BaseModel):
    summary: str

class MomentRequest(BaseModel):
    content: str
    mood: str = ""
    tag: str = ""

@app.get("/")
async def root():
    return FileResponse("index.html")

@app.post("/chat")
async def chat(req: ChatRequest):
    user_msg = req.message.strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail="消息不能为空")

    relevant_memories = mem.retrieve_relevant_memories(user_msg)
    memory_context = ""
    if relevant_memories:
        memory_context = "\n\n【你对他的记忆片段，自然地融入对话，不要刻意提起】\n" + "\n".join(
            f"- {m}" for m in relevant_memories
        )

    system_with_memory = SYSTEM_PROMPT + memory_context
    recent = mem.get_recent_messages(limit=20)
    mem.save_message("user", user_msg)

    messages = [{"role": "system", "content": system_with_memory}] + recent + [{"role": "user", "content": user_msg}]

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            max_tokens=512,
            temperature=0.85,
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API调用失败: {str(e)}")

    mem.save_message("assistant", reply)
    return {"reply": reply}

# ── 朋友圈接口 ──────────────────────────────────────────────────

@app.get("/moments")
async def get_moments():
    return {"moments": mem.get_moments(limit=30)}

@app.post("/moments/like/{moment_id}")
async def like_moment(moment_id: int):
    likes = mem.like_moment(moment_id)
    return {"likes": likes}

@app.post("/moments/generate")
async def manual_generate():
    """手动触发生成一条动态（调试用）"""
    await generate_daily_moment()
    return {"status": "ok"}

@app.post("/moments/post")
async def post_moment(req: MomentRequest):
    """手动发一条动态"""
    mem.save_moment(req.content, req.mood, req.tag)
    return {"status": "ok"}

# ── 记忆接口 ─────────────────────────────────────────────────────

@app.post("/memory/save")
async def save_memory(req: MemoryRequest):
    mem.save_long_term_memory(req.summary)
    return {"status": "ok"}

@app.get("/memory/list")
async def list_memories():
    return {"memories": mem.get_all_long_term_memories()}

@app.get("/history")
async def get_history():
    return {"messages": mem.get_all_messages()}

@app.delete("/history")
async def delete_history():
    mem.clear_history()
    return {"status": "ok"}
