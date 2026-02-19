# -*- coding: utf-8 -*-
"""
Secure Nexus Chat Server
FastAPI + WebSocket + Render 兼容
功能：
- WebSocket /ws
- 广播消息
- 支持私聊 / 群聊 (简化)
"""
import os, json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 渲染测试环境可用
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

clients = {}  # username -> websocket

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    username = None
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            # 登录注册
            if msg.get("type") in ("login", "register"):
                username = msg.get("username")
                clients[username] = ws
                await ws.send_text(json.dumps({"type":"login_success","token":"dummy_token"}))
            # 私聊
            elif msg.get("type") == "private_msg":
                to = msg.get("to")
                if to in clients:
                    await clients[to].send_text(json.dumps({
                        "type":"private",
                        "from": msg.get("from"),
                        "msg": msg.get("msg")
                    }))
            # 群聊
            elif msg.get("type") == "group_msg":
                for u, cws in clients.items():
                    if u != msg.get("from"):
                        await cws.send_text(json.dumps({
                            "type":"group_msg",
                            "group": msg.get("group"),
                            "from": msg.get("from"),
                            "msg": msg.get("msg")
                        }))
            # 文件私聊
            elif msg.get("type") == "file":
                to = msg.get("to")
                if to in clients:
                    await clients[to].send_text(json.dumps({
                        "type":"file",
                        "from": msg.get("from"),
                        "filename": msg.get("filename"),
                        "file": msg.get("file")
                    }))
            # 群文件
            elif msg.get("type") == "group_file":
                for u, cws in clients.items():
                    if u != msg.get("from"):
                        await cws.send_text(json.dumps({
                            "type":"group_file",
                            "group": msg.get("group"),
                            "from": msg.get("from"),
                            "filename": msg.get("filename"),
                            "file": msg.get("file")
                        }))
    except WebSocketDisconnect:
        if username in clients:
            del clients[username]

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
