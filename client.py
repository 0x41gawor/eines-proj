import socket
import sys



HEADER = 64
PORT = 5050
FORMAT = 'utf-8'
DISCONNECT_MESSAGE = "!DISCONNECT"
SERVER = "127.0.0.1"

ADDR = (SERVER, PORT)

client = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
client.connect(ADDR)


class Intent:
    def __init__(self, h_src, h_dst, limit):
        self.h_src = h_src
        self.h_dst = h_dst
        self.limit = limit
    
    def __str__(self):
        return "Flow [H{}<->H{}, {}ms]".format(self.h_src, self.h_dst, self.limit)
    
def get_source_host():
    return int(sys.argv[1])

def get_destination_host():
    return int(sys.argv[2])

def get_delay_value():
    return int(sys.argv[3])


def send(msg):
    message = msg.encode(FORMAT)
    msg_length = len(message)
    send_length = str(msg_length).encode(FORMAT)
    send_length += b' ' * (HEADER - len(send_length))
    client.send(send_length)
    client.send(message)

def send_message():
    sourceID = get_source_host()
    destinationID = get_destination_host()
    delay = get_delay_value()

    if(sourceID == 1 or sourceID == 2 or sourceID == 3):
        if(destinationID == 4 or destinationID == 5 or destinationID == 6):
            intent = Intent(sourceID, destinationID, delay)
            send(str(intent))
            send(DISCONNECT_MESSAGE)
        else:
            print("Wrong destination ID, can't sand this message (Try value between 4 to 6)")
    else:
         print("Wrong source ID, can't sand this message (Try value between 1 to 3)")

send_message()
