from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import socket
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GATEWAY_IP = '127.0.0.1'
GATEWAY_TCP_PORT = 10000

def send_to_gateway(request_dict):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((GATEWAY_IP, GATEWAY_TCP_PORT))
            s.sendall(json.dumps(request_dict).encode())
            response_data = s.recv(4096)
            return json.loads(response_data.decode())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/devices")
async def get_devices():
    request = {"action": "LIST_DEVICES"}
    response = send_to_gateway(request)
    return response

@app.post("/api/devices/{device_id}/command")
async def send_device_command(device_id: str, command_req: dict):
    action = command_req.get("action")
    request = {
        "action": "COMMAND",
        "device_id": device_id,
        "command_action": action
    }
    response = send_to_gateway(request)
    return response