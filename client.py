import socket
import threading
import time

class Client:
    def __init__(self, server_ip, server_TCPport, server_UDPport):
        self.server_ip = server_ip
        self.server_TCPport = server_TCPport
        self.server_UDPport = server_UDPport
        self.client_socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.is_chooser = False

    def connect(self):
        try:
            self.client_socket_tcp.connect((self.server_ip, self.server_TCPport))
            print(f"Connesso al server TCP su {self.server_ip}:{self.server_TCPport}")
            self.receive_messages_tcp()
            self.receive_notifications_udp()
        except Exception as e:
            print(f"Errore di connessione al server: {e}")

    def send_message_tcp(self, message):
        try:
            self.client_socket_tcp.send(message.encode())
        except Exception as e:
            print(f"Errore nell'invio al server: {e}")

    def receive_messages_tcp(self):
        thread = threading.Thread(target=self._receive_tcp)
        thread.daemon = True
        thread.start()

    def _receive_tcp(self):
        while True:
            try:
                data = self.client_socket_tcp.recv(1500)
                if not data:
                    print("Connessione al server TCP chiusa.")
                    break
                message = data.decode()
                print(f"Ricevuto dal server TCP: {message}")
                if message == "SEI_IL_GIOCATORE_CHE_SCEGLIE_LA_PAROLA":
                    self.is_chooser = True
                    word = input("Inserisci la parola da indovinare: ")
                    self.send_message_tcp(f"PAROLA:{word}")
                    self.is_chooser = False
                elif message == "ATTESA_SCELTA_PAROLA":
                    print("In attesa che il giocatore scelga la parola...")
                elif message == "INIZIO_GIOCO":
                    print("Il gioco è iniziato! Indovina le lettere.")
            except Exception as e:
                print(f"Errore nella ricezione TCP: {e}")
                break

    def receive_notifications_udp(self):
        thread = threading.Thread(target=self._receive_udp)
        thread.daemon = True
        thread.start()

    def _receive_udp(self):
        self.udp_socket.bind(('', self.server_UDPport))
        while True:
            try:
                data, addr = self.udp_socket.recvfrom(1024)
                print(f"Notifica UDP dal server ({addr}): {data.decode()}")
            except Exception as e:
                print(f"Errore nella ricezione UDP: {e}")
                break

    def send_guess(self, letter):
        if not self.is_chooser:
            self.send_message_tcp(letter)
        else:
            print("Sei il giocatore che ha scelto la parola, non puoi indovinare.")

    def close_connection(self):
        self.client_socket_tcp.close()
        self.udp_socket.close()