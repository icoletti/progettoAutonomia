import socket
import threading 
import random
import time

#creiamo la classe server
class Server:
    #creoiamo il costruttore
    def __init__(self, TCPport, UDPport):
        self.__ipAddress = "0.0.0.0" #mettersi in ascolto su tutte le interfacce
        self.__TCPport = TCPport
        self.__UDPport = UDPport
        self.__TCPsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__clients = {}  # Lista dei client connessi
        self.__lock = threading.Lock()  # Per sincronizzare l'accesso ai dati condivisi

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
                #manca parte di volantinaggio udp(video prof ) 