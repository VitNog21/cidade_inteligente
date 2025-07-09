import socket
import threading
import time
from proto import smart_city_pb2

#definição do endereço e portas
MCAST_GRP = '224.1.1.1'
MCAST_PORT = 5007
GATEWAY_TCP_PORT = 10000
GATEWAY_UDP_PORT = 10001

devices = {} #guarda informações sobre os dispositivos conectados
device_sockets = {} #mantem as conexões TCP ativas com os dispositivos
lock = threading.Lock()

def handle_device_tcp(conn, addr):
    '''
    Conexões TCP dos dispositivos:
        - Quando um dispositivo se conecta, ele envia um pacote de descoberta com suas 
          informações, então o Gateway registra essas informações nos dicionários;
          
        - O gateway continua a ouvir dados na mesma conexão TCP, se o atuador alterar
         seu estado, ele envia um discovery_packet atualizado, atualiza também o status
         correspondente em devices.'''
    
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

    '''Gerencia conexões TCP de clientes web:
    Espera receber uma requisição do cliente. Suporta dois tipos
    de requisição:
    
        - list_devices: retorna uma lista de todos os dispositivos registrados;
        - command_device: Permite enviar um comando ("TURN_ON", "TURN_OFF"). 
    O Gateway busca a conexão TCP do dispositivo e retransmite o comando.'''
    
    try:
        data = conn.recv(1024)
        if not data:
            return

        request_proto = smart_city_pb2.ClientGatewayRequest()
        request_proto.ParseFromString(data)
        request_type = request_proto.WhichOneof('request')

        if request_type == 'list_devices':
            response_proto = smart_city_pb2.GatewayClientResponse()
            with lock:
                for device_dict in devices.values():
                    device_info_proto = response_proto.devices.add()
                    device_info_proto.id = device_dict['id']
                    device_info_proto.type = smart_city_pb2.DeviceType.Value(device_dict['type'])
                    device_info_proto.status = device_dict['status']
            
            conn.sendall(response_proto.SerializeToString())

        elif request_type == 'command_device':
            command = request_proto.command_device
            device_id = command.device_id
            
            with lock:
                device_conn = device_sockets.get(device_id)

            if device_conn:
                device_conn.send(command.SerializeToString())
            
            conn.sendall(b'')
            
    except Exception as e:
        print(f"Gateway: Erro no cliente web: {e}")
    finally:
        conn.close()

def start_tcp_server():
    '''
    - Inicia um servidor TCP principal na GATEWAY_TCP_PORT;
    - Aceita novas conexões, se a conexão vier do 127.0.0.1 (localhost), 
     ele assume que é um cliente web e delega o tratamento para handle_web_client em uma nova thread,
     caso não, assume que é um dispositivo e delega para handle_device_tcp em uma nova thread.
     Isso permite que o Gateway lide com múltiplas conexões simultaneamente sem bloquear.
     '''
    
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
    '''
    - Inicia um servidor UDP na GATEWAY_UDP_PORT
    - Este servidor é usado pra receber os dados do sensor de temperatura;
    - Ao receber dados de um sensor, ele extrai o ID do dispositivo
     e o valor do sensor, atualizando o status do dispositivo correspondente 
     dicionário devices
     '''
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
    '''
    - Envia uma mensagem de descoberta (GatewayRequest com ação "DISCOVER") via multicast UDP
    para o grupo MCAST_GRP e MCAST_PORT;
    - Esta mensagem serve para que novos dispositivos na rede saibam que há um Gateway disponível
     e possam se conectar a ele.
     '''
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    
    request = smart_city_pb2.GatewayRequest()
    request.action = "DISCOVER"
    
    sock.sendto(request.SerializeToString(), (MCAST_GRP, MCAST_PORT))

def periodic_discovery():
    '''
       Executa a função discover_devices a cada 15 segundos em um loop infinito. 
       Garantindo que o Gateway anuncie sua presença regularmente e permita que 
       novos dispositivos se registrem.
       '''
    while True:
        print("Gateway: Enviando pulso de descoberta periódica....")
        discover_devices()
        time.sleep(30)

if __name__ == "__main__":
    tcp_thread = threading.Thread(target=start_tcp_server, daemon=True)
    udp_thread = threading.Thread(target=start_udp_server, daemon=True)
    discovery_thread = threading.Thread(target=periodic_discovery, daemon=True)

    tcp_thread.start()
    udp_thread.start()
    discovery_thread.start()

    while True:
        time.sleep(1)
