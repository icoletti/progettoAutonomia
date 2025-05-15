import socket
import threading
import time

# Classe Client per gestire la connessione al server e l'interazione dell'utente
class Client:
    # Costruttore della classe Client
    def __init__(self, server_ip, server_TCPport, server_UDPport):
        # Indirizzo IP del server a cui connettersi
        self.server_ip = server_ip
        # Porta TCP del server per la comunicazione principale
        self.server_TCPport = server_TCPport
        # Porta UDP del server per ricevere notifiche (usata ma non inviata direttamente dal client in questa versione)
        self.server_UDPport = server_UDPport
        # Socket TCP per la comunicazione con il server
        self.client_socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Socket UDP per ricevere notifiche dal server
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Flag per indicare se questo client è il giocatore che ha scelto la parola
        self.is_chooser = False

    # Metodo per connettersi al server TCP e avviare i thread di ricezione
    def connect(self):
        try:
            # Tenta di stabilire una connessione con il server utilizzando l'IP e la porta TCP
            self.client_socket_tcp.connect((self.server_ip, self.server_TCPport))
            print(f"Connesso al server TCP su {self.server_ip}:{self.server_TCPport}")
            # Avvia un thread separato per ricevere messaggi TCP dal server in modo non bloccante
            self.receive_messages_tcp()
            # Avvia un thread separato per ricevere notifiche UDP dal server in modo non bloccante
            self.receive_notifications_udp()
        except Exception as e:
            print(f"Errore di connessione al server: {e}")

    # Metodo per inviare un messaggio al server tramite la connessione TCP
    def send_message_tcp(self, message):
        try:
            # Codifica il messaggio in bytes (UTF-8 è una codifica standard) e lo invia tramite il socket TCP
            self.client_socket_tcp.send(message.encode())
        except Exception as e:
            print(f"Errore nell'invio al server: {e}")

    # Metodo per avviare un thread dedicato alla ricezione di messaggi TCP dal server
    def receive_messages_tcp(self):
        # Crea un nuovo thread che esegue il metodo _receive_tcp
        thread = threading.Thread(target=self._receive_tcp)
        # Imposta il thread come demone. Questo significa che il thread terminerà quando il programma principale termina.
        thread.daemon = True
        # Avvia l'esecuzione del thread
        thread.start()

    # Metodo eseguito nel thread per ricevere continuamente messaggi TCP dal server
    def _receive_tcp(self):
        while True:
            try:
                # Riceve fino a 1500 byte di dati dal server
                data = self.client_socket_tcp.recv(1500)
                # Se non riceve dati, la connessione con il server è stata chiusa
                if not data:
                    print("Connessione al server TCP chiusa.")
                    break
                # Decodifica i dati ricevuti da bytes a stringa
                message = data.decode()
                print(f"Ricevuto dal server TCP: {message}")
                # Gestisce i messaggi specifici ricevuti dal server
                # rischioso  perchè la codifica la fa sul testo e non su una codifica IMPORTANTE MI HA DETTO IL PROF CHE è UNA FOLLIA  
                if message == "SEI IL GIOCATORE CHE SCEGLIE LA PAROLA":
                    # Se il server comunica che questo client deve scegliere la parola, imposta il flag
                    self.is_chooser = True
                    # Richiede all'utente di inserire la parola
                    word = input("Inserisci la parola da indovinare: ")
                    # Invia la parola al server con il prefisso "PAROLA:"
                    print("tutto ok ")
                    self.send_message_tcp(f"PAROLA:{word}")
                    # Resetta il flag di chooser dopo aver inviato la parola
                    self.is_chooser = False
                    print("tutto bho ")
                elif message == "ATTESA SCELTA PAROLA":
                    # Se il server comunica che si è in attesa della scelta della parola da parte di un altro giocatore
                    print("In attesa che il giocatore scelga la parola...")
                elif message == "INIZIO GIOCO":
                    # Se il server comunica che il gioco è iniziato
                    print("Il gioco è iniziato! Indovina le lettere.")
                elif message.startswith("Parola attuale:"):
                    # Stampa lo stato attuale della parola indovinata
                    print(message)
                elif message.startswith("Notifica:"):
                    # Stampa le notifiche dal server (es. "Giusta", "Sbagliata", "Hai Perso!")
                    print(message)
                elif message == "HAI VINTO":
                    # Stampa un messaggio di vittoria
                    print("Hai indovinato la parola! Congratulazioni!")
                elif message.startswith("LA PAROLA ERA:"):
                    # Stampa la parola corretta quando si perde o la partita termina
                    correct_word = message[len("LA PAROLA ERA:"):]
                    print(f"La parola era: {correct_word}")
                elif message == "HAI PERSO":
                    # Stampa un messaggio di sconfitta
                    print("Hai esaurito i tentativi! Hai perso.")
            except Exception as e:
                print(f"Errore nella ricezione TCP: {e}")
                break

    # Metodo per avviare un thread dedicato alla ricezione di notifiche UDP dal server
    def receive_notifications_udp(self):
        # Crea un nuovo thread per la ricezione UDP
        thread = threading.Thread(target=self._receive_udp)
        # Imposta il thread come demone
        thread.daemon = True
        # Avvia il thread UDP
        thread.start()

    # Metodo eseguito nel thread per ricevere continuamente notifiche UDP dal server
    def _receive_udp(self):
        self.udp_socket.bind(('', self.server_UDPport))
        while True:
            try:
                # Riceve fino a 1024 byte di dati UDP. La recvfrom() restituisce sia i dati che l'indirizzo del mittente.
                data, addr = self.udp_socket.recvfrom(1024)
                # Decodifica i dati ricevuti e li stampa, insieme all'indirizzo del server da cui provengono.
                print(f"Notifica UDP dal server ({addr}): {data.decode()}")
            except Exception as e:
                print(f"Errore nella ricezione UDP: {e}")
                break

    # Metodo per inviare un tentativo di indovinare una lettera al server
    def send_guess(self, letter):
        # Verifica che questo client non sia il giocatore che ha scelto la parola (non può indovinare)
        if not self.is_chooser:
            # Invia la lettera al server tramite la connessione TCP
            self.send_message_tcp(letter)
        else:
            print("Sei il giocatore che ha scelto la parola, non puoi indovinare.")

    # Metodo per chiudere la connessione TCP e il socket UDP con il server
    def close_connection(self):
        self.client_socket_tcp.close()
        self.udp_socket.close()