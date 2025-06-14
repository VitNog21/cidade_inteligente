import socket
import struct
from proto import smart_city_pb2

MCAST_GRP = '224.1.1.1'
MCAST_PORT = 5007
GATEWAY_TCP_PORT = 10000

DEVICE_ID = "lamp_01"
DEVICE_IP = "192.168.0.102"
DEVICE_PORT = 20002

status = "OFF"

def handle_commands(conn):
    global status
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            
            command = smart_city_pb2.Command()
            command.ParseFromString(data)
            
            if command.action in ["TURN_ON", "TURN_OFF"]:
                status = command.action.replace("TURN_", "")
                print(f"{DEVICE_ID}: Status alterado para {status}")
                
                response_packet = smart_city_pb2.DiscoveryPacket()
                response_packet.info.id = DEVICE_ID
                response_packet.info.type = smart_city_pb2.DeviceType.LAMP
                response_packet.info.status = status
                response_packet.ip_address = DEVICE_IP
                response_packet.port = DEVICE_PORT
                
                conn.send(response_packet.SerializeToString())
                
    except ConnectionResetError:
        print(f"{DEVICE_ID}: Conexão com Gateway perdida.")
    finally:
        conn.close()

def listen_for_discovery():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', MCAST_PORT))
    
    mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    print(f"{DEVICE_ID}: Aguardando descoberta...")
    data, addr = sock.recvfrom(1024)
    gateway_ip = addr[0]
    
    request = smart_city_pb2.GatewayRequest()
    request.ParseFromString(data)

    if request.action == "DISCOVER":
        print(f"{DEVICE_ID}: Gateway em {gateway_ip}. Conectando via TCP...")
        tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            tcp_sock.connect((gateway_ip, GATEWAY_TCP_PORT))
            
            packet = smart_city_pb2.DiscoveryPacket()
            packet.info.id = DEVICE_ID
            packet.info.type = smart_city_pb2.DeviceType.LAMP
            packet.info.status = status
            packet.ip_address = DEVICE_IP
            packet.port = DEVICE_PORT
            
            tcp_sock.send(packet.SerializeToString())
            handle_commands(tcp_sock)
        except Exception as e:
            print(f"Falha ao conectar com o Gateway: {e}")
        finally:
            tcp_sock.close()

if __name__ == "__main__":
    listen_for_discovery()