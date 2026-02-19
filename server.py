# -*- coding: utf-8 -*-
"""
Secure Nexus Chat 服务端 - 增强版
功能：
- 登录 / 注册 / 用户管理
- 私聊 / 群聊（自动创建）
- 文件传输（Base64）
- E2E 加密兼容客户端
- 在线用户列表广播
- 群聊接口（动态创建/查询）
"""
import asyncio, websockets, json, base64, os, bcrypt, time, traceback

USERS_FILE = "users.json"
GROUPS_FILE = "groups.json"
MESSAGES_FILE = "messages.json"

# -----------------------------
# 数据管理
# -----------------------------
def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

USERS = load_json(USERS_FILE)
GROUPS = load_json(GROUPS_FILE)
MESSAGES = load_json(MESSAGES_FILE)

# { websocket: username }
CONNECTED = {}

# -----------------------------
# 用户管理
# -----------------------------
async def handle_register(ws, data):
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        await ws.send(json.dumps({"type":"error","msg":"用户名或密码为空"}))
        return
    if username in USERS:
        await ws.send(json.dumps({"type":"error","msg":"用户名已存在"}))
        return
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    USERS[username] = hashed
    save_json(USERS_FILE, USERS)
    await ws.send(json.dumps({"type":"success","msg":"注册成功"}))
    print(f"[注册] 用户 {username}")

async def handle_login(ws, data):
    username = data.get("username")
    password = data.get("password")
    if username not in USERS or not bcrypt.checkpw(password.encode(), USERS[username].encode()):
        await ws.send(json.dumps({"type":"error","msg":"用户名或密码错误"}))
        return
    CONNECTED[ws] = username
    token = str(time.time())
    await ws.send(json.dumps({"type":"login_success","token":token}))
    await broadcast_online()
    print(f"[登录] 用户 {username} 上线")

# -----------------------------
# 广播在线用户
# -----------------------------
async def broadcast_online():
    users = list(CONNECTED.values())
    msg = json.dumps({"type":"online_users","users":users})
    for ws in CONNECTED:
        await ws.send(msg)

# -----------------------------
# 私聊
# -----------------------------
async def handle_private(ws, data):
    to_user = data.get("to")
    sender = data.get("from")
    msg = data.get("msg")
    for client, name in CONNECTED.items():
        if name == to_user:
            await client.send(json.dumps({"type":"private","from":sender,"msg":msg}))
    MESSAGES.setdefault(sender, []).append({"to":to_user,"msg":msg,"time":time.time()})
    save_json(MESSAGES_FILE, MESSAGES)

async def handle_file(ws, data):
    to_user = data.get("to")
    sender = data.get("from")
    fname = data.get("filename")
    fcontent = data.get("file")
    for client, name in CONNECTED.items():
        if name == to_user:
            await client.send(json.dumps({"type":"file","from":sender,"filename":fname,"file":fcontent}))
    MESSAGES.setdefault(sender, []).append({"to":to_user,"msg":f"[File: {fname}]", "time":time.time()})
    save_json(MESSAGES_FILE, MESSAGES)

# -----------------------------
# 群聊管理
# -----------------------------
async def handle_group_msg(ws, data):
    group = data.get("group")
    sender = data.get("from")
    msg = data.get("msg")
    members = GROUPS.get(group, [])
    for client, name in CONNECTED.items():
        if name in members and name != sender:
            await client.send(json.dumps({"type":"group_msg","group":group,"from":sender,"msg":msg}))

async def handle_group_file(ws, data):
    group = data.get("group")
    sender = data.get("from")
    fname = data.get("filename")
    fcontent = data.get("file")
    members = GROUPS.get(group, [])
    for client, name in CONNECTED.items():
        if name in members and name != sender:
            await client.send(json.dumps({"type":"group_file","group":group,"from":sender,"filename":fname,"file":fcontent}))

# -----------------------------
# 动态创建群聊
# -----------------------------
async def handle_create_group(ws, data):
    group_name = data.get("group")
    members = data.get("members", [])
    members = list(set(members))  # 去重
    if group_name in GROUPS:
        await ws.send(json.dumps({"type":"error","msg":"群聊已存在"}))
        return
    GROUPS[group_name] = members
    save_json(GROUPS_FILE, GROUPS)
    await ws.send(json.dumps({"type":"success","msg":f"群 {group_name} 创建成功"}))
    print(f"[群聊创建] {group_name} 包含成员 {members}")

# -----------------------------
# 消息分发
# -----------------------------
async def handler(ws, path):
    try:
        async for message in ws:
            try:
                data = json.loads(message)
                typ = data.get("type")
                if typ == "register":
                    await handle_register(ws, data)
                elif typ == "login":
                    await handle_login(ws, data)
                elif typ == "private_msg":
                    await handle_private(ws, data)
                elif typ == "file":
                    await handle_file(ws, data)
                elif typ == "group_msg":
                    await handle_group_msg(ws, data)
                elif typ == "group_file":
                    await handle_group_file(ws, data)
                elif typ == "create_group":
                    await handle_create_group(ws, data)
            except Exception as e:
                print("消息处理错误:", e, traceback.format_exc())
    except websockets.ConnectionClosed:
        pass
    finally:
        if ws in CONNECTED:
            username = CONNECTED[ws]
            del CONNECTED[ws]
            await broadcast_online()
            print(f"[下线] 用户 {username}")

# -----------------------------
# 启动服务
# -----------------------------
async def main():
    server = await websockets.serve(handler, "0.0.0.0", 10000)
    print("Secure Nexus Chat 服务启动，端口 10000")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
