import asyncio
import websockets
import json
import os
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes

SECRET_KEY = b"NEXUS_SECURE_2026_KEY_32BYTES!!"

clients = {}

# ================= AES =================

def encrypt(data: str):
    iv = get_random_bytes(16)
    cipher = AES.new(SECRET_KEY, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(data.encode(), AES.block_size))
    return base64.b64encode(iv + encrypted).decode()

def decrypt(data: str):
    raw = base64.b64decode(data)
    iv = raw[:16]
    encrypted = raw[16:]
    cipher = AES.new(SECRET_KEY, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(encrypted), AES.block_size).decode()

# ================= Handler =================

async def handler(websocket):
    username = None
    try:
        async for message in websocket:
            try:
                decrypted = decrypt(message)
                data = json.loads(decrypted)
            except:
                continue

            if data["type"] == "login":
                username = data["username"]
                clients[username] = websocket
                await websocket.send(encrypt(json.dumps({
                    "type": "system",
                    "msg": "登录成功"
                })))

            elif data["type"] == "msg":
                target = data["to"]
                if target in clients:
                    await clients[target].send(encrypt(json.dumps({
                        "type": "msg",
                        "from": username,
                        "msg": data["msg"]
                    })))

    except:
        pass
    finally:
        if username in clients:
            del clients[username]

# ================= Main =================

async def main():
    port = int(os.environ.get("PORT", 10000))
    server = await websockets.serve(handler, "0.0.0.0", port)
    print("Secure Nexus Chat 启动，端口", port)
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
