import socket
import threading

# Classe per gestire la comunicazione con un singolo client in un thread separato
class MTClientHandler(threading.Thread):
    # Costruttore della classe MTClientHandler
    def __init__(self, clientSocket, clientAddress, server_instance, lock):
        # Chiamiamo il costruttore della classe padre (threading.Thread)
        threading.Thread.__init__(self)
        # Socket specifico per la comunicazione con questo client
        self.__clientSocket = clientSocket
        # Indirizzo (IP e porta) del client connesso
        self.__clientAddress = clientAddress
        # Riferimento all'istanza del server per poter interagire con la logica globale del gioco
        self.__server = server_instance
        # Lock per sincronizzare l'accesso a risorse condivise (anche se qui principalmente usato nel server)
        self.__lock = lock
        # Dizionario per memorizzare i dati specifici del gioco per questo client
        self.game_data = {"word": "", "errors": 0, "guessed_word": "", "attempts": []}

    # Metodo eseguito quando il thread viene avviato
    def run(self):
        try:
            # Notifichiamo a tutti gli altri client che un nuovo giocatore si è connesso
            self.__server.broadcast_message(f"Nuovo giocatore connesso: {self.__clientAddress}", exclude=self.__clientAddress)
            # Al primo client che si connette, chiediamo al server di selezionare un giocatore per scegliere la parola
            # (questa logica potrebbe essere raffinata per gestire meglio l'inizio del gioco con più client)
            if not self.__server.__game_started and len(self.__server.__clients) == 1:
                self.__server.select_random_chooser()

            # Ciclo infinito per ricevere dati dal client
            while True:
                # Riceviamo fino a 1500 byte di dati dal client
                data = self.__clientSocket.recv(1500)
                # Se non riceviamo dati, significa che il client si è disconnesso o ha chiuso la connessione
                if not data:
                    break
                # Decodifichiamo i dati ricevuti da bytes a stringa, rimuovendo eventuali spazi bianchi all'inizio e alla fine
                message = data.decode("utf-8").strip()
                print(f"Ricevuto da {self.__clientAddress}: {message}")

                # Gestiamo i messaggi ricevuti dal client
                if message.startswith("PAROLA:"):
                    # Se il messaggio inizia con "PAROLA:", estraiamo la parola proposta
                    word = message[len("PAROLA:"):].strip()
                    # Chiamiamo il metodo del server per impostare la parola da indovinare, verificando se il client è il chooser
                    if self.__server.set_word_to_guess(word, self.__clientAddress):
                        # Se la parola è stata accettata, inviamo una conferma al client
                        self.send_message("PAROLA_ACCETTATA")
                    else:
                        # Altrimenti, inviamo un messaggio di errore
                        self.send_message("ERRORE: NON SEI IL GIOCATORE CHE SCEGLIE O IL GIOCO È GIA' INIZIATO")
                # Se il messaggio è di una singola lettera e il gioco è iniziato e il client non è il chooser
                elif len(message) == 1 and self.__server.__game_started and self.__clientAddress != self.__server.__chooser_address:
                    # Convertiamo la lettera in minuscolo
                    letter = message.lower()
                    # Verifichiamo se questa lettera è già stata tentata
                    if letter not in self.game_data["attempts"]:
                        # Chiamiamo il metodo del server per gestire il tentativo di indovinare la lettera
                        self.__server.guess_letter(letter, self.__clientAddress)
                        # Aggiungiamo la lettera ai tentativi effettuati
                        self.game_data["attempts"].append(letter)
                    else:
                        # Se la lettera è già stata provata, informiamo il client
                        self.send_message("HAI GIA' PROVATO QUESTA LETTERA")
                # Se il client invia un comando per richiedere lo stato attuale del gioco
                elif message == "RICHIESTA_STATO":
                    # Invia lo stato attuale del gioco al client
                    self.send_status_game()
                else:
                    # Se il comando non è riconosciuto, inviamo un messaggio di errore
                    self.send_message("COMANDO NON RICONOSCIUTO")

        except Exception as e:
            # Se si verifica un errore durante la comunicazione con il client, lo stampiamo
            print(f"Errore nella gestione del client {self.__clientAddress}: {e}")
        finally:
            # Quando il ciclo while termina (il client si disconnette), rimuoviamo il client dal server
            self.__server.remove_client(self.__clientAddress)
            # Chiudiamo la connessione con il client
            self.__clientSocket.close()

    # Metodo per processare un tentativo di indovinare una lettera
    def process_guess(self, letter):
        # Se la lettera è presente nella parola da indovinare
        if letter in self.game_data["word"]:
            # Aggiorniamo la parola indovinata mostrando la lettera corretta
            self.update_guessed_word(letter)
            # Notifichiamo al client che la lettera è giusta
            self.send_message("GIUSTO")
            # Verifichiamo se la parola è stata completamente indovinata
            if self.game_data["guessed_word"] == self.game_data["word"]:
                # Notifichiamo a tutti che il giocatore ha indovinato la parola
                self.__server.broadcast_message(f"IL GIOCATORE {self.__clientAddress} HA INDOVINATO LA PAROLA: {self.game_data['word']}")
                # Resettiamo lo stato del gioco sul server
                self.__server.__game_started = False
                # Selezioniamo un nuovo giocatore per scegliere la parola
                self.__server.select_random_chooser()
                # Invia un messaggio speciale al client che ha indovinato
                self.send_message("HAI_VINTO")
                # Invia un messaggio agli altri client che la partita è finita
                self.__server.broadcast_message(f"Partita terminata. La parola era: {self.game_data['word']}", exclude=self.__clientAddress)
        else:
            # Se la lettera non è nella parola, incrementiamo il contatore degli errori
            self.game_data["errors"] += 1
            # Notifichiamo al client che la lettera è sbagliata
            self.send_message("SBAGLIATO")
            # Verifichiamo se il numero di errori ha raggiunto il limite (ad esempio, 6 errori)
            if self.game_data["errors"] >= 6:
                # Notifichiamo al client che ha perso
                self.send_message("HAI_PERSO")
                # Notifichiamo a tutti la parola corretta
                self.__server.broadcast_message(f"Il giocatore {self.__clientAddress} ha perso. La parola era: {self.game_data['word']}", exclude=self.__clientAddress)
                # Resettiamo lo stato del gioco sul server
                self.__server.__game_started = False
                # Selezioniamo un nuovo giocatore per scegliere la parola
                self.__server.select_random_chooser()
                # Invia un messaggio speciale al client che ha perso
                self.send_message(f"LA_PAROLA_ERA:{self.game_data['word']}")
                # Invia un messaggio agli altri client che la partita è finita
                self.__server.broadcast_message(f"Partita terminata. La parola era: {self.game_data['word']}", exclude=self.__clientAddress)
        # Dopo ogni tentativo (corretto o sbagliato), inviamo lo stato attuale del gioco al client
        self.send_status_game()

    # Metodo per aggiornare la parola indovinata con la lettera corretta
    def update_guessed_word(self, letter):
        # Convertiamo la parola da indovinare e la parola indovinata in liste per una facile manipolazione
        word_list = list(self.game_data["word"])
        guessed_word_list = list(self.game_data["guessed_word"])
        # Iteriamo su ogni lettera della parola da indovinare
        for i in range(len(word_list)):
            # Se la lettera corrente corrisponde alla lettera indovinata
            if word_list[i] == letter:
                # Aggiorniamo la lettera nella parola indovinata
                guessed_word_list[i] = letter
        # Riconvertiamo la lista della parola indovinata in una stringa
        self.game_data["guessed_word"] = "".join(guessed_word_list)

    # Metodo per inviare un messaggio al client
    def send_message(self, message):
        try:
            # Codifichiamo il messaggio in bytes (UTF-8) e lo inviamo al client
            self.__clientSocket.send(message.encode("utf-8"))
        except Exception as e:
            print(f"Errore nell'invio al client {self.__clientAddress}: {e}")

    # Metodo per inviare lo stato attuale del gioco al client
    def send_status_game(self):
        # Creiamo un messaggio contenente la parola indovinata parzialmente e il numero di errori
        status = f"Parola attuale: {self.game_data['guessed_word']}, Errori: {self.game_data['errors']}"
        # Inviamo il messaggio di stato al client
        self.send_message(status) 