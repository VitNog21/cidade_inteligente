import socket
import struct
import time
import random
from proto import smart_city_pb2

MCAST_GRP = '224.1.1.1'
MCAST_PORT = 5007
GATEWAY_IP = '127.0.0.1'
GATEWAY_UDP_PORT = 10001
GATEWAY_TCP_PORT = 10000

DEVICE_ID = "temp_sensor_01"
DEVICE_IP = "192.168.0.101"
DEVICE_PORT = 20001

def send_data_periodically(tcp_conn):
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while True:
        temp = random.randint(20, 35)
        
        data = smart_city_pb2.SensorData()
        data.device_id = DEVICE_ID
        data.value = temp
        
        try:
            udp_sock.sendto(data.SerializeToString(), (GATEWAY_IP, GATEWAY_UDP_PORT))
            print(f"{DEVICE_ID}: Enviado {temp}°C para o Gateway.")
        except Exception as e:
            print(f"{DEVICE_ID}: Falha ao enviar dados. {e}")
            break
        time.sleep(15)

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
            packet.info.type = smart_city_pb2.DeviceType.TEMP_SENSOR
            packet.info.status = f"{random.randint(20, 35)}°C"
            packet.ip_address = DEVICE_IP
            packet.port = DEVICE_PORT
            
            tcp_sock.send(packet.SerializeToString())
            send_data_periodically(tcp_sock)
        except Exception as e:
            print(f"Falha ao conectar com o Gateway: {e}")
        finally:
            tcp_sock.close()

if __name__ == "__main__":
    listen_for_discovery()