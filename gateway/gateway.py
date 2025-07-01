import socket
import threading
import json
import time
from proto import smart_city_pb2

MCAST_GRP = '224.1.1.1'
MCAST_PORT = 5007
GATEWAY_TCP_PORT = 10000
GATEWAY_UDP_PORT = 10001

devices = {}
device_sockets = {}
lock = threading.Lock()

def handle_device_tcp(conn, addr):
    device_id = None
    try:
        data = conn.recv(1024)
        if not data:
            return

        discovery_packet = smart_city_pb2.DiscoveryPacket()
        discovery_packet.ParseFromString(data)

        device_id = discovery_packet.info.id
        with lock:
            devices[device_id] = {
                "id": device_id,
                "type": smart_city_pb2.DeviceType.Name(discovery_packet.info.type),
                "status": discovery_packet.info.status,
                "address": discovery_packet.ip_address,
                "port": discovery_packet.port
            }
            device_sockets[device_id] = conn
        print(f"Gateway: Dispositivo registrado/atualizado: {devices[device_id]}")

        while True:
            data = conn.recv(1024)
            if not data:
                break
            
            response_packet = smart_city_pb2.DiscoveryPacket()
            response_packet.ParseFromString(data)
            device_id_update = response_packet.info.id
            with lock:
                if device_id_update in devices:
                    devices[device_id_update]['status'] = response_packet.info.status
                    print(f"Gateway: Estado do atuador {device_id_update} atualizado para {devices[device_id_update]['status']}")

    except ConnectionResetError:
        print(f"Gateway: Conexão com {device_id or 'dispositivo desconhecido'} perdida.")
    except Exception as e:
        print(f"Gateway: Erro na conexão com o dispositivo: {e}")
    finally:
        with lock:
            if device_id and device_id in devices:
                del devices[device_id]
                if device_id in device_sockets:
                    del device_sockets[device_id]
        conn.close()
        print(f"Gateway: Dispositivo {device_id} removido.")

def handle_web_client(conn, addr):
    try:
        data = conn.recv(1024)
        if not data:
            return

        request_proto = smart_city_pb2.ClientGatewayRequest()
        request_proto.ParseFromString(data)
        response = {}
        request_type = request_proto.WhichOneof('request')

        if request_type == 'list_devices':
            with lock:
                response = {"devices": list(devices.values())}
        
        elif request_type == 'command_device':
            command = request_proto.command_device
            device_id = command.device_id
            command_action = command.action
            
            with lock:
                device_conn = device_sockets.get(device_id)

            if device_conn:              
                device_conn.send(command.SerializeToString())
                response = {"status": "success", "message": f"Comando '{command_action}' enviado para {device_id}."}
            else:
                response = {"status": "error", "message": "Dispositivo não está conectado."}
        
        conn.sendall(json.dumps(response).encode())

    except Exception as e:
        print(f"Gateway: Erro ao manusear cliente web: {e}")
    finally:
        conn.close()


def start_tcp_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('', GATEWAY_TCP_PORT))
    server.listen(10)
    print(f"Gateway: Servidor TCP escutando na porta {GATEWAY_TCP_PORT}")

    while True:
        conn, addr = server.accept()
        if addr[0] == '127.0.0.1':
             client_thread = threading.Thread(target=handle_web_client, args=(conn, addr))
             client_thread.start()
        else:
            device_thread = threading.Thread(target=handle_device_tcp, args=(conn, addr))
            device_thread.start()

def start_udp_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(('', GATEWAY_UDP_PORT))
    print(f"Gateway: Servidor UDP escutando na porta {GATEWAY_UDP_PORT}")

    while True:
        data, addr = server.recvfrom(1024)
        sensor_data = smart_city_pb2.SensorData()
        sensor_data.ParseFromString(data)
        
        device_id = sensor_data.device_id
        with lock:
            if device_id in devices:
                devices[device_id]['status'] = f"{int(sensor_data.value)}°C"

def discover_devices():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    
    request = smart_city_pb2.GatewayRequest()
    request.action = "DISCOVER"
    
    sock.sendto(request.SerializeToString(), (MCAST_GRP, MCAST_PORT))

def periodic_discovery():
    while True:
        print("Gateway: Enviando pulso de descoberta periódica...")
        discover_devices()
        time.sleep(15)

if __name__ == "__main__":
    tcp_thread = threading.Thread(target=start_tcp_server, daemon=True)
    udp_thread = threading.Thread(target=start_udp_server, daemon=True)
    discovery_thread = threading.Thread(target=periodic_discovery, daemon=True)

    tcp_thread.start()
    udp_thread.start()
    discovery_thread.start()

    while True:
        time.sleep(1)