import socket
import struct
import subprocess
import time


def wake_on_lan(macaddress):
    if len(macaddress) == 12:
        pass
    elif len(macaddress) == 12 + 5:
        sep = macaddress[2]
        macaddress = macaddress.replace(sep, '')
    else:
        raise ValueError('Incorrect MAC address format')

    data = ''.join(['FFFFFFFFFFFF', macaddress * 20])
    send_data = ''

    for i in range(0, len(data), 2):
        send_data = ''.join([send_data,
                             struct.pack('B', int(data[i: i + 2], 16))])

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(send_data, ('<broadcast>', 7))


def ping(ip_address, n_packets=1, wait_before=0):
    param = '-c ' + str(n_packets)
    time.sleep(wait_before)
    command = ['ping', param, ip_address]
    return subprocess.call(command) == 0

