import server

TCPport=5000
UDPport=5001

server_avvio = server.Server(TCPport, UDPport)
server_avvio.Start()