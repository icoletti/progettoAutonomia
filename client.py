import socket


class Client:
    def __init__(self, server_ip, server_TCPport, server_UDPport):
        self.server_ip = server_ip
        self.server_TCPport = server_TCPport
        self.server_UDPport = server_UDPport
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((server_ip, server_TCPport))

    def sendLetter(self, letter):
        self.client_socket.send(letter.encode())

    def receiveStatusGame(self):
        data = self.client_socket.recv(1500)
        print(data.decode())

    def receiveNotificationUDP(self):
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.bind(('', self.server_UDPport))
        while True:
            data, _ = udp_socket.recvfrom(1024)
            print(f"Notifica UDP ricevuta: {data.decode()}")