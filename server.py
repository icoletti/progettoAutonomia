import socket
import threading
import random
import time
from clienthandler import MTClientHandler

# Creiamo la classe Server per gestire le connessioni e la logica del gioco
class Server:
    def __init__(self, TCPport, UDPport):
        # Indirizzo IP su cui il server ascolterà le connessioni TCP
        self.__ipAddress = "0.0.0.0"
        # Porta TCP su cui il server ascolterà
        self.__TCPport = TCPport
        # Porta UDP su cui il server invierà i broadcast di disponibilità
        self.__UDPport = UDPport
        # Socket TCP per accettare le connessioni dai client
        self.__TCPsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Dizionario per memorizzare i gestori dei client connessi (chiave: indirizzo client, valore: istanza MTClientHandler)
        self.__clients = {}
        # Lock per sincronizzare l'accesso alle risorse condivise tra i thread
        self.__lock = threading.Lock()
        # Flag per indicare se una partita è attualmente in corso
        self.__game_started = False
        # La parola che i giocatori devono indovinare
        self.__word_to_guess = ""
        # L'indirizzo del client che ha il compito di scegliere la parola
        self.__chooser_address = None

    def Start(self):
        # Flag per verificare se il binding del socket TCP ha avuto successo
        connection = False
        try:
            # Associa il socket TCP all'indirizzo IP e alla porta specificati
            self.__TCPsocket.bind((self.__ipAddress, self.__TCPport))
            # Inizia ad ascoltare le connessioni in entrata (massimo 8 connessioni in coda)
            self.__TCPsocket.listen(8)
            connection = True
            print(f"Server TCP in ascolto su {self.__ipAddress}:{self.__TCPport}")
        except Exception as e:
            print(f"Errore nell'avvio del server TCP: {e}")

        # Se il server TCP è stato avviato con successo, avvia il thread per il broadcasting UDP
        if connection:
            broadcastingUDP_Thread = threading.Thread(target=self.__BroadcastingUDP, args=())
            broadcastingUDP_Thread.start()
            print(f"Server UDP in broadcasting su {self.__ipAddress}:{self.__UDPport}")

            # Ciclo infinito per accettare nuove connessioni TCP
            while True:
                # Accetta una nuova connessione in entrata. Restituisce un nuovo socket per la connessione e l'indirizzo del client.
                clientSocket, clientAddress = self.__TCPsocket.accept()
                print(f"Connessione accettata da {clientAddress}")
                # Acquisisce il lock per accedere in modo sicuro al dizionario dei client
                with self.__lock:
                    # Inizialmente memorizza l'indirizzo del client senza un gestore associato
                    self.__clients[clientAddress] = None
                # Crea un nuovo thread per gestire la comunicazione con il client
                clientHandler = MTClientHandler(clientSocket, clientAddress, self, self.__lock)
                # Acquisisce nuovamente il lock per associare il gestore al client nel dizionario
                with self.__lock:
                    self.__clients[clientAddress] = clientHandler
                # Avvia l'esecuzione del thread del gestore del client
                clientHandler.start()

    def __BroadcastingUDP(self):
        # Crea un socket UDP
        __UDPsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Imposta l'opzione per abilitare il broadcasting
        __UDPsocket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        # Messaggio da inviare tramite broadcast (indica che il server è disponibile sulla porta TCP specificata)
        message = f"SERVER_AVAILABLE:{self.__TCPport}"
        # Ciclo infinito per inviare periodicamente il messaggio di broadcast
        while True:
            try:
                # Invia il messaggio di broadcast a tutti gli host sulla rete locale sulla porta UDP specificata
                __UDPsocket.sendto(message.encode(), ('255.255.255.255', self.__UDPport))
                # Attende 5 secondi prima di inviare il prossimo broadcast
                time.sleep(5)
            except Exception as e:
                print(f"Errore nel volantinaggio UDP: {e}")
                break

    def broadcast_message(self, message, exclude=None):
        # Acquisisce il lock per iterare in modo sicuro attraverso i client
        with self.__lock:
            # Itera su tutti i client connessi e i loro gestori
            for addr, handler in self.__clients.items():
                # Se c'è un gestore per il client e l'indirizzo non è quello da escludere
                if handler and addr != exclude:
                    # Invia il messaggio al client tramite il suo gestore
                    handler.send_message(message)

    def set_word_to_guess(self, word, address):
        # Acquisisce il lock per accedere in modo sicuro allo stato del gioco
        with self.__lock:
            # Verifica se il gioco non è ancora iniziato e se l'indirizzo corrisponde al giocatore designato per scegliere la parola
            if not self.__game_started and address == self.__chooser_address:
                # Memorizza la parola da indovinare convertendola in minuscolo
                self.__word_to_guess = word.lower()
                # Imposta il flag per indicare che il gioco è iniziato
                self.__game_started = True
                print(f"Parola da indovinare impostata da {address}: {self.__word_to_guess}")
                # Invia un messaggio a tutti gli altri client che il gioco è iniziato
                self.broadcast_message("INIZIO_GIOCO", exclude=address)
                # Inizializza lo stato del gioco per ogni client
                for addr, handler in self.__clients.items():
                    if handler:
                        # Crea una stringa di underscore della lunghezza della parola da indovinare
                        initial_guessed_word = "_" * len(self.__word_to_guess)
                        # Memorizza la parola da indovinare nel gestore del client
                        handler.game_data["word"] = self.__word_to_guess
                        # Memorizza la parola indovinata iniziale nel gestore del client
                        handler.game_data["guessed_word"] = initial_guessed_word
                        # Invia lo stato iniziale del gioco al client
                        handler.send_status_game()
                return True
            return False

    def guess_letter(self, letter, address):
        # Acquisisce il lock per accedere in modo sicuro allo stato del gioco e ai client
        with self.__lock:
            # Verifica se il gioco è iniziato e se il client che ha inviato la lettera non è quello che ha scelto la parola
            if self.__game_started and address != self.__chooser_address:
                # Ottiene il gestore del client che ha inviato la lettera
                handler = self.__clients.get(address)
                if handler:
                    # Delega la gestione del tentativo di indovinare al gestore del client
                    handler.process_guess(letter)
                    return True
            return False

    def select_random_chooser(self):
        # Acquisisce il lock per accedere in modo sicuro alla lista dei client
        with self.__lock:
            # Se ci sono client connessi
            if self.__clients:
                # Sceglie casualmente un indirizzo client dalla lista delle chiavi del dizionario dei client
                self.__chooser_address = random.choice(list(self.__clients.keys()))
                print(f"Giocatore scelto per inserire la parola: {self.__chooser_address}")
                # Ottiene il gestore del client scelto
                chooser_handler = self.__clients.get(self.__chooser_address)
                if chooser_handler:
                    # Invia un messaggio speciale al client designato per scegliere la parola
                    chooser_handler.send_message("SEI_IL_GIOCATORE_CHE_SCEGLIE_LA_PAROLA")
                # Invia un messaggio a tutti gli altri client che sono in attesa della scelta della parola
                self.broadcast_message("ATTESA_SCELTA_PAROLA", exclude=self.__chooser_address)
            else:
                print("Nessun client connesso per scegliere la parola.")

    def remove_client(self, address):
        # Acquisisce il lock per modificare in modo sicuro il dizionario dei client e lo stato del gioco
        with self.__lock:
            # Se l'indirizzo del client è presente nel dizionario
            if address in self.__clients:
                # Rimuove il client dal dizionario
                del self.__clients[address]
                print(f"Client {address} disconnesso.")
                # Se non ci sono più client connessi e il gioco era iniziato
                if not self.__clients and self.__game_started:
                    # Resetta lo stato del gioco
                    self.__game_started = False
                    self.__word_to_guess = ""
                    self.__chooser_address = None
                    print("Tutti i client disconnessi, gioco resettato.")
                # Se il client disconnesso era colui che doveva scegliere la parola e il gioco era iniziato
                elif address == self.__chooser_address and self.__game_started:
                    print("Il giocatore che ha scelto la parola si è disconnesso. Resetto il gioco.")
                    self.__game_started = False
                    self.__word_to_guess = ""
                    self.__chooser_address = None
                    self.broadcast_message("GIOCO_RESETTATO_PER_DISCONNESSIONE_SCELTA")
                    # Se ci sono ancora client connessi, seleziona un nuovo chooser
                    if self.__clients:
                        self.select_random_chooser()
                # Se il gioco non è iniziato e ci sono ancora client connessi, seleziona un nuovo chooser
                elif not self.__game_started and self.__clients:
                    self.select_random_chooser()

    def is_game_started(self):
        # Restituisce lo stato attuale del gioco (True se iniziato, False altrimenti)
        return self.__game_started

    def get_clients(self):
        """Restituisce una copia del dizionario dei client connessi."""
        with self.__lock:
            return self.__clients.copy()

    def get_client_addresses(self):
        """Restituisce una lista degli indirizzi dei client connessi."""
        with self.__lock:
            return list(self.__clients.keys())

    def is_client_connected(self, address):
        """Verifica se un client con l'indirizzo specificato è connesso."""
        with self.__lock:
            return address in self.__clients