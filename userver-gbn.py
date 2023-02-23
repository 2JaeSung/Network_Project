from socket import *
from threading import Thread
from queue import Queue
import time

serverIP = '127.0.0.1' # special IP for local host
serverPort = 15000
clientPort = 15001

serverSocket = socket(AF_INET, SOCK_DGRAM)
serverSocket.bind(('', serverPort))

print('The server is ready to receive')

rcv_base = 0  # next sequence number we wait for
receive_queue = Queue() # this queue is used to receive packet from client
buffer_size = 20 # set queue size

# thread for receiving and handling acks
def handling_ack():
    global serverSocket
    global receive_queue
    global buffer_size

    while True:
        try:
            message, clientAddress = serverSocket.recvfrom(2048)
            seq_n = int(message.decode())  # extract sequence number
            if receive_queue.qsize() <= buffer_size: # if queue is not full
                receive_queue.put(seq_n)

        except BlockingIOError:
            continue


# running a thread for receiving and handling acks
th_handling_ack = Thread(target=handling_ack, args=())
th_handling_ack.start()


while True:
    time.sleep(0.005) # extract packet with certain time to act like a bandwidth
    if receive_queue.qsize() >= 1: # if queue size is not empty
        seq_n = receive_queue.get()
        if rcv_base <= seq_n: # discard already received packet
            print(seq_n)
            if seq_n == rcv_base:  # in order delivery
                rcv_base = seq_n + 1
            serverSocket.sendto(str(rcv_base - 1).encode(), (serverIP, clientPort))  # send cumulative ack

        if seq_n == 999:
            break;


th_handling_ack.join()

serverSocket.close()



