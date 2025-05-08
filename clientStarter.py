import client

ip = "192.168.6.25"
portTCP = 5000
portUDP = 5001

client_avvio = client.Client(ip, portTCP, portUDP)
client_avvio.connect()