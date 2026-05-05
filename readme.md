# Rubia AI 伴侣 · 启动指南

## 目录结构
```
ai-companion/
├──res/
|  └── avatar.jpg
├── .env.example     → 复制为 .env 并填入 API Key
├── main.py          → 后端主程序
├── memory.py        → 记忆系统
├── index.html       → 前端界面
└── README.md
```

## 第一次启动

### 1. 安装依赖
```bash
pip install fastapi uvicorn openai chromadb sqlite-utils python-dotenv
```

### 2. 配置 API Key
将 `.env.example` 复制为 `.env`，填入你的 DeepSeek API Key：
```
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
```

### 3. 启动
```bash
cd ai-companion
uvicorn main:app --reload --port 8000
```

### 4. 打开浏览器
访问 http://localhost:8000

---

## 日常使用

每次使用只需要：
```bash
cd ai-companion
uvicorn main:app --port 8000
```
然后打开 http://localhost:8000 即可。

---

## 记忆系统说明

**短期记忆（自动）**
- 每次对话自动保存到本地 `rubia_memory.db`
- 每次发消息会携带最近 20 条对话作为上下文

**长期记忆（手动）**
- 在左侧边栏手动输入重要信息，比如：
  - "今天聊到他工作压力很大，来自领导的打压"
  - "他喜欢喝咖啡不加糖"
  - "他提到过最近在学吉他"
- Rubia 会在相关对话中自然地调用这些记忆

---

## 数据文件位置
- `rubia_memory.db` — SQLite 对话历史
- `./chroma_db/` — 向量记忆数据库

这两个文件只在本地，不会上传任何地方。
有条件可以部署到云服务器使用域名访问
