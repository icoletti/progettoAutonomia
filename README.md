# IMPYCCATHON 

Progetto di autonomia


Architettura del Gioco dell’Impiccato con Elezione del Master (Random)
Schema generale:


       Client1 ———— TCP ———— Server ———— TCP ———— Client2

               ↑                      ↑
               
              UDP                    UDP
              
               ↓                      ↓
               
           Elezione Master casuale (UDP Broadcast)


Fasi del gioco:
1. Connessione Client-Server
I client si collegano via TCP


Server mantiene lista dei client connessi



2. Elezione del Master (Random)
Server sceglie a caso un client tra quelli collegati


Comunica a tutti via UDP:


"Il client X è il MASTER"
Solo il Master inserisce la parola segreta (via TCP)


Gli altri diventano giocatori


Oppure: i client si "sfidano" via UDP → chi risponde prima a un messaggio speciale diventa Master (modalità carina da fare)

3. Gioco
I giocatori mandano lettere via TCP al Server


Server aggiorna lo stato


Mutex per proteggere la parola segreta e il numero di errori


Server manda via TCP a tutti lo stato aggiornato:


Parola nascosta con lettere scoperte


Errori fatti


Turno attuale


UDP per:


Notifica "Lettera Giusta!"


Notifica "Lettera Sbagliata!"


Notifica "Hai Vinto!" o "Hai Perso!"



4. Fine partita
Server comunica a tutti il risultato


Possibilità di rigiocare con nuovo Master eletto


