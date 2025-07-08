from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import socket
from proto import smart_city_pb2
from google.protobuf.json_format import MessageToDict

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

@app.get("/api/devices")
async def get_devices():
    request_proto = smart_city_pb2.ClientGatewayRequest()
    request_proto.list_devices = "LIST"
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((GATEWAY_IP, GATEWAY_TCP_PORT))
            s.sendall(request_proto.SerializeToString())
            
            response_bytes = s.recv(4096)
            if not response_bytes:
                return {"devices": []}
            
            response_proto = smart_city_pb2.GatewayClientResponse()
            response_proto.ParseFromString(response_bytes)
            
            response_dict = MessageToDict(response_proto, preserving_proto_field_name=True)
            return response_dict

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro de comunicação com o Gateway: {e}")

@app.post("/api/devices/{deviceId}/command")
async def send_device_command(deviceId: str, command_req: dict):
    action = command_req.get("action")
    
    request_proto = smart_city_pb2.ClientGatewayRequest()
    request_proto.command_device.device_id = deviceId
    request_proto.command_device.action = action

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((GATEWAY_IP, GATEWAY_TCP_PORT))
            s.sendall(request_proto.SerializeToString())
            s.recv(1024) 
            return {"status": "success", "message": "Comando enviado."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na comunicação com o Gateway: {e}")