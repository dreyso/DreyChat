import socket
import threading
import select
import queue
from typing import Dict, Any, List, Optional, Tuple

class Server(threading.Thread):
    
    # Start up server thread
    def __init__(self, HOST: str, PORT: int, CONN_BACKLOG_SIZE: int) -> None:
        threading.Thread.__init__(self)

        # Let main thread signal when to close server
        self._closing: threading.Event = threading.Event() 

        # Open a non-blocking, reusable (avoid wait timeout), ipv4 TCP listening socket
        self._serverSocket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._serverSocket.setblocking(False)
        self._serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._serverSocket.bind((HOST, PORT))
        self._serverSocket.listen(CONN_BACKLOG_SIZE)

        self._sockets = [self._serverSocket]

        self.recieveQueue: queue.Queue = queue.Queue()    # Queue of pairs, {id, message}
        self.sendQueuesLock: threading.Lock = threading.Lock()
        self.sendQueues: Dict[int, queue.Queue] = {}    # dict: key = id, value = queue
        self.removeQueue: queue.Queue = queue.Queue()

        self.start()

    def closeServer(self):
        self._closing.set()

    def closeSocket(self, socket: socket.socket) -> None:
        # Remove from interface
        self.sendQueuesLock.acquire()
        del self.sendQueues[id(socket)]
        self.removeQueue.put(id(socket), block=True, timeout=None)
        self.sendQueuesLock.release()

        # Remove socket
        self._sockets.remove(socket)
        socket.close()

    def read(self, readable: list):
        
        # Handle inputs
        for iSocket in readable:
            # Skip already closed sockets
            if iSocket not in self._sockets:
                continue

            # Accept pending connection
            if iSocket  == self._serverSocket:
                newSocket, _ = iSocket.accept()
                newSocket.setblocking(False)
                self._sockets.append(newSocket)

                # Add connection to interface
                self.sendQueuesLock.acquire()
                self.sendQueues[id(newSocket)] = queue.Queue()
                self.sendQueuesLock.release()
                continue

            # Read message from socket, catch forcible disconnections
            message = None
            try:
                message = iSocket.recv(1024)
            except:
                self.closeSocket(iSocket)
                continue

            # Put incoming data on queue
            if message:
                self.recieveQueue.put((id(iSocket), message))
                #print("recvd")

            # Closed connections send empty messages
            else:
                self.closeSocket(iSocket)

    def write(self, writable: list):
        # Handle outputs
        for iSocket in writable:
            # Skip if there is nothing to send or if the socket has already been closed
            if iSocket not in self._sockets or self.sendQueues[id(iSocket)].empty():
                continue
            
            try:
                iSocket.sendall(self.sendQueues[id(iSocket)].get())
                #print("sent")

            except:
                self.closeSocket(iSocket)
                continue

    def handle(self, exceptional: list):
        # Handle "exceptional conditions"
        for iSocket in exceptional:
            # Skip already closed sockets
            if iSocket not in self._sockets:
                continue
            self.closeSocket(iSocket)

    # Run thread
    def run(self):
        # Start the server
        while not self._closing.is_set():
            # Block until a socket becomes readable, writable, or throws an exception
            # Times out after 1 second
            readable, writable, exceptional = select.select(self._sockets, self._sockets, self._sockets, 1)
            
            self.read(readable)
            self.write(writable)
            self.handle(exceptional)
