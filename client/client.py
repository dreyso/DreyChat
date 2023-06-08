import socket
import threading
import select
import queue

class Client(threading.Thread):
    
    # Start up client thread
    def __init__(self, HOST, PORT, sendQueue, recvQueue):
        threading.Thread.__init__(self)
        self.closing = threading.Event() # Let main thread signal when to close connection

        self.HOST = HOST
        self.PORT = PORT

        # Open a non-blocking, reusable (avoid wait timeout), ipv4 TCP socket
        self.clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clientSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sendQueue = sendQueue
        self.recvQueue = recvQueue
    
    def connect(self) -> bool:
        # Ensure socket times out during lengthy connects
        self.clientSocket.settimeout(5)
        try:
            self.clientSocket.connect((self.HOST, self.PORT))
        # socket.error is thrown when the server is offline
        except socket.error as err:
            #print(str(err))
            return False
        
        self.clientSocket.setblocking(False)

        # Start thread that runs client
        self.start()
        return True
    
    def disconnect(self):
        self.closing.set()

    # Returns false if the server closed the connection
    def read(self) -> bool:
        
        # Read message from socket
        message = self.clientSocket.recv(1024)

        # Closed connections send empty messages
        if not message:
            return False
        
        self.recvQueue.put(message)
        return True

    def write(self):
        # Skip if there is nothing to send
        if self.sendQueue.empty():
            return
        
        self.clientSocket.sendall(self.sendQueue.get())

    # Run thread
    def run(self):
        # Select works on lists
        sockets = [self.clientSocket]

        while True:
            # Block until the socket becomes readable, writable, or throws an exception
            # Times out after 1 second
            readable, writable, _ = select.select(sockets, sockets, [], 1)

            try:
                if readable:
                    if not self.read():
                        print('Server terminated the connection.')
                        break

                if writable:
                    self.write()

            # Catch abrupt disconnections
            except OSError as err: 
                print("Error: connection abruptly closed")
                break

            # User decided to quit
            if self.closing.is_set():
                break

        # Close connection
        self.clientSocket.close()