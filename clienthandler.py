import socket
import threading

class MTClientHandler(threading.Thread):
    def __init__(self, clientSocket, clientAddress, clientsDict, lock):
        threading.Thread.__init__(self)
        self.__clientSocket = clientSocket
        self.__clientAddress = clientAddress
        self.__clientsDict = clientsDict
        self.__lock = lock # Lock per sincronizzare l'accesso ai dati condivisi
        #inizializza i dati del gioco per il client
        self.game_data = {"word": "", "errors": 0, "guessed_word": "", "turn": 1}

    #eseguiamo il thread per gestire le richieste del client
    def run(self):
        try:
            #ciclo infinito per gestire le richieste del client
            while True:
                #riceviamo i dati dal client (in lettura)
                data = self.__clientSocket.recv(1500)
                #se il client ha chiuso la connessione/il server non riceve i dati esco dal ciclo
                if not data:
                    break
                #facciamo la decodifica dei dati ricevuti e avvio il processo 
                #di lettura della lettera che i client proveranno ad indovinare
                letter = data.decode("utf-8")

                self.read(letter.strip().lower())  # Elabora la lettera

        except Exception as ex:
            #ae c'è un errore durante la comunicazione con il client, stampalo
            print(f"Errore con il client {self.__clientAddress}: {e}")
        finally:
            #chiudi la connessione del client al termine
            self.__clientSocket.close()

    def read(self, letter):
         #se la lettera è corretta, aggiorna la parola indovinata
        if letter in self.game_data["word"]:
            self.game_data["guessed_word"] = self.updateWord(letter)
            self.notify("Giusta")  #notifica che la lettera è giusta
        else:
            #se la lettera è sbagliata, incrementa gli errori
            self.game_data["errors"] += 1
            self.notify("Sbagliata")  #notifica che la lettera è sbagliata
            if self.game_data["errors"] >= 6:
                self.notify("Hai Perso!")  #se il numero di errori raggiunge 6, il client ha perso
                self.game_data["guessed_word"] = self.game_data["word"]  # Riveliamo la parola
        #invia lo stato attuale del gioco al client
        self.sendStatusGame()

      # Aggiorna la parola indovinata con le lettere corrette
    def updateWord(self, letter):
        guessed = list(self.game_data["guessed_word"])  # Converte la parola indovinata in lista
        for i, char in enumerate(self.game_data["word"]):
            if char == letter:
                guessed[i] = letter  # Sostituisce la lettera indovinata nella posizione corretta
        return "".join(guessed)  # Ritorna la parola aggiornata come stringa

    # Invia una notifica al client tramite UDP
    def notify(self, status):
        message = f"Notifica: {status}"  # Crea il messaggio di notifica
        self.sendUDP(message)  # Invia la notifica tramite UDP

    # Invia il messaggio UDP al client
    def sendUDP(self, message):
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Crea un socket UDP
        udp_socket.sendto(message.encode(), self.__clientAddress)  # Invia il messaggio al client

    # Invia lo stato attuale del gioco al client via TCP
    def sendStatusGame(self):
        message = f"Parola attuale: {self.game_data['guessed_word']} - Errori: {self.game_data['errors']}"
        self.__clientSocket.send(message.encode())  # Invia il messaggio al client

