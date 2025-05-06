import socket
import threading 
import random
import time
from clienthandler import MTClientHandler

#creiamo la classe server
class Server:
    #definiamo il costruttore della classe server
    def __init__(self, TCPport, UDPport):
        self.__ipAddress = "0.0.0.0" #mettersi in ascolto su tutte le interfacce
        self.__TCPport = TCPport
        self.__UDPport = UDPport
        self.__TCPsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__clients = {}  #lista dei client connessi
        self.__lock = threading.Lock()  #per sincronizzare l'accesso ai dati condivisi
        self.__game_started = False
        self.__word_to_guess = ""
        self.__chooser_address = None


    #avviamo il server, lo mettiamo il ascolto di richieste di connessione da parte dei clients
    def Start(self):
        connection = False
        try:
            #proviamo la bind, con il binding invio una richiesta al sistema operativo 
            #per poter legare la porta specificata (TCPport) al processo del server
            self.__TCPsocket.bind((self.__ipAddress, self.__TCPport))
            # permetto l'ascolto di 8 richieste contemporanee
            self.__TCPsocket.listen(8)
            #il legame è avvenuto, allora imposto la connessione a true
            connection = True
        except Exception as ex:
            print(f"Qualcosa non ha funzionato nell'avvio del server:{str(e)}")

            #se la connessione è avvenuta:
            if connection:
                #avvio un metodo come thread di volantinaggio UDP per trasmettere 
                #i client l'esistenza del mio server
                broadcastingUDP_Thread = threading.Thread(target=self.__BroadcastingUDP, args=())
                broadcastingUDP_Thread.start() 
                while True:
                    clientSocket, clientAddress = self.__TCPsocket.accept()
                    print(f"Connessione accettata da {clientAddress}")
                    with self.__lock:
                        self.__clients[clientAddress] = None # Inizialmente l'handler è None
                    clientHandler = MTClientHandler(clientSocket, clientAddress, self, self.__lock)
                    with self.__lock:
                        self.__clients[clientAddress] = clientHandler
                    clientHandler.start()

    # Metodo per inviare periodicamente messaggi broadcast UDP
    def __BroadcastingUDP(self):
        __UDPsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        __UDPsocket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        message = f"SERVER accessibile su:{self.__TCPport}"
        
        while True:
            try:
                __UDPsocket.sendto(message.encode(), ('255.255.255.255', self.__UDPport))
                time.sleep(5)  # ogni 5 secondi
            except Exception as e:
                print(f"Errore nel volantinaggio UDP: {e}")
                break
                #manca parte di volantinaggio udp(video prof ) 
    
    def broadcast_message(self, message, exclude=None):
        with self.__lock:
            for addr, handler in self.__clients.items():
                if handler and addr != exclude:
                    handler.send_message(message)

    
