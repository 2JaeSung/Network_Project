from socket import *
from threading import Thread
import time

import matplotlib.pyplot as plt

serverIP = '127.0.0.1' # special IP for local host
serverPort = 15000
clientPort = 15001

win = 1      # window size
no_pkt = 1000 # the total number of packets to send
send_base = 0 # oldest packet sent
seq = 0        # initial sequence number
timeout_flag = 0 # timeout trigger
triple_flag = 0 # triple-ack trigger
ssthresh = 10 # ssthresh size

total_loss = 0 # total loss
triple_loss = 0 # loss due to triple duplicate ack
timeout_loss = 0 # loss due to time out

sent_time = [0 for i in range(2000)]

list_packet = [] # to make a x axis of graph (save current packet number)
list_window = [] # to make a y axis of graph (save current window value)

RTT_avg = 0
RTT_count = 0
win_avg = 0


clientSocket = socket(AF_INET, SOCK_DGRAM)
clientSocket.bind(('', clientPort))
clientSocket.setblocking(0)

# thread for receiving and handling acks
def handling_ack():
    print("thread")
    global clientSocket
    global win
    global ssthresh
    global list_packet
    global list_window
    global send_base
    global timeout_flag
    global sent_time
    global triple_flag
    global total_loss
    global triple_loss
    global timeout_loss
    global RTT_avg
    global RTT_count
    global win_avg

    alpha = 0.125
    beta = 0.25
    timeout_interval = 10  # timeout interval

    pkt_delay = 0
    dev_rtt = 0
    init_rtt_flag = 1
    pre_ack = 0 # to know value of previous ack
    ack_count = 0 # if previous ack and current ack is same increase ack_count
    
    while True:
       
        if sent_time[send_base] != 0: 
            pkt_delay = time.time() - sent_time[send_base]

        if ack_count == 3 and triple_flag == 0: # triple duplicate ack detected
            print("triple duplicate acks detected:", str(send_base), flush=True)
            triple_flag = 1
            triple_loss = triple_loss + 1
            total_loss = total_loss + 1

        if pkt_delay > timeout_interval and timeout_flag == 0:    # timeout detected
            print("timeout detected:", str(send_base), flush=True)
            print("timeout interval:", str(timeout_interval), flush=True)
            timeout_flag = 1
            timeout_loss = timeout_loss + 1
            total_loss = total_loss + 1

        try:
            ack, serverAddress = clientSocket.recvfrom(2048)
            ack_n = int(ack.decode())

            if win < ssthresh: # increase window size twice when window size is smaller than ssthresh
                win = win + 1
            else: # increase window size linearly when window size is larger than ssthresh
                win = win + (1 / win)

            if len(list_packet) == 0 or list_window[-1] > win or list_packet[-1] != ack_n: # to show graph save packet num and window size in array
                list_packet.append(ack_n)
                list_window.append(win)

            if ack_n == pre_ack: # previous ack and current ack is same
                ack_count = ack_count + 1
            else: # previous ack and current ack is different
                ack_count = 0

            pre_ack = ack_n # save previous ack

            print(ack_n, flush=True)

            RTT_avg = RTT_avg + pkt_delay # to save RTT average
            RTT_count = RTT_count + 1 # to know how many RTT is here

            if init_rtt_flag == 1:
                estimated_rtt = pkt_delay
                init_rtt_flag = 0
            else:
                estimated_rtt = (1-alpha)*estimated_rtt + alpha*pkt_delay
                dev_rtt = (1-beta)*dev_rtt + beta*abs(pkt_delay-estimated_rtt)
            timeout_interval = estimated_rtt + 4*dev_rtt
            #print("timeout interval:", str(timeout_interval), flush=True)

            
        except BlockingIOError:
            continue
            
        # window is moved upon receiving a new ack
        # window stays for cumulative ack
        send_base = ack_n + 1
        
        if ack_n == 999:
            break;

# running a thread for receiving and handling acks
th_handling_ack = Thread(target = handling_ack, args = ())
th_handling_ack.start()

while seq < no_pkt:
    while seq < send_base + win: # send packets within window
        clientSocket.sendto(str(seq).encode(), (serverIP, serverPort))
        sent_time[seq] = time.time()
        seq = seq + 1

    if timeout_flag == 0 and triple_flag == 1: # retransmission in triple duplicate ack
        seq = send_base
        clientSocket.sendto(str(seq).encode(), (serverIP, serverPort))
        sent_time[seq] = time.time()
        print("triple acks-retransmission:", str(seq), flush=True)
        seq = seq + 1
        triple_flag = 0

        ssthresh = win / 2 # set ssthresh half of window size
        win = 1 # set window size to 1

    if triple_flag == 0 and timeout_flag == 1: # retransmission in timeout
        seq = send_base
        clientSocket.sendto(str(seq).encode(), (serverIP, serverPort))
        sent_time[seq] = time.time()
        print("timeout-retransmission:", str(seq), flush=True)
        seq = seq + 1
        timeout_flag = 0

        ssthresh = win / 2 # set ssthresh half of window size
        win = 1 # set window size to 1

        
th_handling_ack.join() # terminating thread

print("done")
print("triple duplicate loss " + str(triple_loss))
print("timeout loss " + str(timeout_loss))
print("total loss rate " + str(total_loss/10) + "%")

RTT_avg = RTT_avg / RTT_count # RTT average
win_avg = sum(list_window) / len(list_window) # window size average
throughput = win_avg / RTT_avg # calculate throughput
print("throughput " + str(throughput) + "(segments/sec)")

plt.plot(list_packet, list_window)
plt.show()

clientSocket.close()


