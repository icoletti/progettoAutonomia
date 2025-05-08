import socket
import threading
import random
import time
from clienthandler import MTClientHandler

# Creiamo la classe Server per gestire le connessioni e la logica del gioco
class Server:
    # Definiamo il costruttore della classe Server
    def __init__(self, TCPport, UDPport):
        # Indirizzo IP su cui il server si metterà in ascolto (tutte le interfacce)
        self.__ipAddress = "0.0.0.0"
        # Porta TCP per le comunicazioni principali con i client
        self.__TCPport = TCPport
        # Porta UDP per l'annuncio del server e potenziali notifiche veloci
        self.__UDPport = UDPport
        # Creiamo un socket TCP/IP per gestire le connessioni dei client
        self.__TCPsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Dizionario per tenere traccia dei client connessi, usando l'indirizzo come chiave e l'handler come valore
        self.__clients = {}
        # Lock per sincronizzare l'accesso alle risorse condivise (come la lista dei client) in ambiente multi-threading
        self.__lock = threading.Lock()
        # Flag per indicare se una partita è attualmente in corso
        self.__game_started = False
        # La parola che deve essere indovinata
        self.__word_to_guess = ""
        # L'indirizzo del client che ha scelto la parola
        self.__chooser_address = None

    # Metodo per avviare il server e metterlo in ascolto di nuove connessioni
    def Start(self):
        connection = False
        try:
            # Tentiamo di associare (bind) il socket TCP all'indirizzo IP e alla porta specificati
            self.__TCPsocket.bind((self.__ipAddress, self.__TCPport))
            # Abilitiamo il server ad accettare connessioni, specificando un backlog di 8 connessioni in attesa
            self.__TCPsocket.listen(8)
            connection = True
            print(f"Server TCP in ascolto su {self.__ipAddress}:{self.__TCPport}")
        except Exception as e:
            print(f"Errore nell'avvio del server TCP: {e}")

        # Se la connessione TCP è avvenuta con successo
        if connection:
            # Avviamo un thread separato per gestire il broadcasting UDP, annunciando la presenza del server
            broadcastingUDP_Thread = threading.Thread(target=self.__BroadcastingUDP, args=())
            broadcastingUDP_Thread.start()
            print(f"Server UDP in broadcasting su {self.__ipAddress}:{self.__UDPport}")

            # Ciclo infinito per accettare nuove connessioni TCP in arrivo
            while True:
                # Accettiamo una nuova connessione. clientSocket è un nuovo socket dedicato a questa connessione,
                # clientAddress è una tupla contenente l'IP e la porta del client connesso.
                clientSocket, clientAddress = self.__TCPsocket.accept()
                print(f"Connessione accettata da {clientAddress}")
                # Acquisiamo il lock per modificare in modo sicuro la lista dei client
                with self.__lock:
                    self.__clients[clientAddress] = None # Inizialmente l'handler è None
                # Creiamo un'istanza di MTClientHandler per gestire la comunicazione con questo specifico client
                clientHandler = MTClientHandler(clientSocket, clientAddress, self, self.__lock)
                # Associamo l'handler al client nella nostra lista
                with self.__lock:
                    self.__clients[clientAddress] = clientHandler
                # Avviamo il thread del client handler, rendendo possibile la comunicazione parallela
                clientHandler.start()

    # Metodo eseguito nel thread per inviare periodicamente messaggi broadcast UDP
    def __BroadcastingUDP(self):
        # Creiamo un socket UDP
        __UDPsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Impostiamo l'opzione SO_BROADCAST per poter inviare messaggi a tutti sulla rete locale
        __UDPsocket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        # Il messaggio da inviare, contenente l'indicazione del server disponibile e la porta TCP
        message = f"SERVER_AVAILABLE:{self.__TCPport}"
        while True:
            try:
                # Inviamo il messaggio di broadcast a tutti gli indirizzi sulla porta UDP specificata
                __UDPsocket.sendto(message.encode(), ('255.255.255.255', self.__UDPport))
                # Aspettiamo 5 secondi prima di inviare il prossimo annuncio
                time.sleep(5)
            except Exception as e:
                print(f"Errore nel volantinaggio UDP: {e}")
                break

    # Metodo per inviare un messaggio a tutti i client connessi, escludendone eventualmente uno
    def broadcast_message(self, message, exclude=None):
        # Acquisiamo il lock per iterare in modo sicuro sulla lista dei client
        with self.__lock:
            # Iteriamo su tutti i client connessi
            for addr, handler in self.__clients.items():
                # Verifichiamo che l'handler esista e che l'indirizzo non sia quello da escludere
                if handler and addr != exclude:
                    # Chiamiamo il metodo dell'handler del client per inviare il messaggio
                    handler.send_message(message)

    # Metodo chiamato dal client handler del giocatore scelto per impostare la parola da indovinare
    def set_word_to_guess(self, word, address):
        # Acquisiamo il lock per controllare e modificare lo stato del gioco
        with self.__lock:
            # Verifichiamo che il gioco non sia già iniziato e che l'indirizzo corrisponda al giocatore scelto
            if not self.__game_started and address == self.__chooser_address:
                # Convertiamo la parola in minuscolo e la memorizziamo
                self.__word_to_guess = word.lower()
                # Impostiamo il flag di gioco iniziato a True
                self.__game_started = True
                print(f"Parola da indovinare impostata da {address}: {self.__word_to_guess}")
                # Invia a tutti i client (tranne chi ha scelto) l'inizio del gioco
                self.broadcast_message("INIZIO_GIOCO", exclude=address)
                # Inizializza lo stato del gioco per tutti i client
                for addr, handler in self.__clients.items():
                    if handler:
                        # Crea una stringa di underscore della lunghezza della parola da indovinare
                        initial_guessed_word = "_" * len(self.__word_to_guess)
                        # Aggiorna la parola nel game_data dell'handler
                        handler.game_data["word"] = self.__word_to_guess
                        # Aggiorna la parola indovinata (inizialmente tutta underscore)
                        handler.game_data["guessed_word"] = initial_guessed_word
                        # Invia lo stato iniziale del gioco al client
                        handler.send_status_game()
                return True
            return False

    # Metodo chiamato dal client handler quando un giocatore tenta di indovinare una lettera
    def guess_letter(self, letter, address):
        # Acquisiamo il lock per accedere allo stato del gioco
        with self.__lock:
            # Verifichiamo che il gioco sia iniziato e che il giocatore non sia quello che ha scelto la parola
            if self.__game_started and address != self.__chooser_address:
                # Otteniamo l'handler del client che ha fatto il tentativo
                handler = self.__clients.get(address)
                if handler:
                    # Chiamiamo il metodo dell'handler per processare il tentativo
                    handler.process_guess(letter)
                    return True
            return False

    # Metodo per selezionare casualmente un client connesso come il giocatore che inserirà la parola
    def select_random_chooser(self):
        # Acquisiamo il lock per accedere alla lista dei client
        with self.__lock:
            # Verifichiamo che ci siano client connessi
            if self.__clients:
                # Scegliamo casualmente un indirizzo dalla lista delle chiavi (gli indirizzi dei client)
                self.__chooser_address = random.choice(list(self.__clients.keys()))
                print(f"Giocatore scelto per inserire la parola: {self.__chooser_address}")
                # Otteniamo l'handler del client scelto
                chooser_handler = self.__clients.get(self.__chooser_address)
                if chooser_handler:
                    # Invia un messaggio speciale al client scelto per fargli sapere che deve scegliere la parola
                    chooser_handler.send_message("SEI_IL_GIOCATORE_CHE_SCEGLIE_LA_PAROLA")
                # Invia un messaggio a tutti gli altri client per informarli che è in corso la scelta della parola
                self.broadcast_message("ATTESA_SCELTA_PAROLA", exclude=self.__chooser_address)
            else:
                print("Nessun client connesso per scegliere la parola.")

    # Metodo per rimuovere un client dalla lista quando si disconnette
    def remove_client(self, address):
        # Acquisiamo il lock per modificare in modo sicuro la lista dei client
        with self.__lock:
            # Verifichiamo se l'indirizzo del client è presente nella lista
            if address in self.__clients:
                # Rimuoviamo il client dalla lista
                del self.__clients[address]
                print(f"Client {address} disconnesso.")
                # Se non ci sono più client connessi e una partita era in corso, resettiamo lo stato del gioco
                if not self.__clients and self.__game_started:
                    self.__game_started = False
                    self.__word_to_guess = ""
                    self.__chooser_address = None
                    print("Tutti i client disconnessi, gioco resettato.")
                # Se il client che si è disconnesso era colui che doveva scegliere la parola e il gioco era iniziato
                elif address == self.__chooser_address and self.__game_started:
                    print("Il giocatore che ha scelto la parola si è disconnesso. Resetto il gioco.")
                    self.__game_started = False
                    self.__word_to_guess = ""
                    self.__chooser_address = None
                    self.broadcast_message("GIOCO_RESETTATO_PER_DISCONNESSIONE_SCELTA")
                    # Se ci sono ancora client, selezioniamo un nuovo giocatore per scegliere la parola
                    if self.__clients:
                        self.select_random_chooser()
                # Se il chooser si disconnette prima di scegliere la parola e ci sono altri client
                elif not self.__game_started and self.__clients:
                    self.select_random_chooser() # Seleziona un nuovo chooser

# Blocco principale per avviare il server se lo script viene eseguito direttamente
if __name__ == "__main__":
    TCP_PORT = 5000
    UDP_PORT = 5001
    # Creiamo un'istanza della classe Server
    server = Server(TCP_PORT, UDP_PORT)
    # Avviamo il server
    server.Start()