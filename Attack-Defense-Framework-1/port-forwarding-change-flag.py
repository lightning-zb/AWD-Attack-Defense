#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Tcp Port Forwarding (Reverse Proxy)
# Author : WangYihang <wangyihanger@gmail.com>


import socket
import threading
import sys
import random
import string
import hashlib
import time
from base64 import b32encode

data_recoder = {}


def md5(data):
    return hashlib.md5(data).hexdigest()

def hash_host_port(host, port):
    return md5("%s:%d" % (host, port))

def get_mine_flag():
    flag_path = "/var/www/html/flag.txt"
    with open(flag_path) as f:
        flag = f.read().strip()
    return flag

def random_string(length, charset):
    return "".join([random.choice(charset) for i in range(length)])

def handle(buffer):
    charset = "abcdef0123456789"
    flag = get_mine_flag()
    fake_flag = "flag{%s}" % (random_string(32, charset))
    VALID = False
    # Plain flag replacement
    if flag in buffer:
        print "[+] Attack detected! (Plain)"
        print "[+] Replacing [%s] => [%s]" % (flag, fake_flag)
        buffer = buffer.replace(flag, fake_flag)
        VALID = True
    # Base64 encoded flag replacment
    base64_encoded_flag0 = flag.encode("base64").replace("\n", "").replace("=", "")
    base64_encoded_fake_flag0 = fake_flag.encode("base64").replace("\n", "").replace("=", "")
    if base64_encoded_flag0 in buffer:
        print "[+] Attack detected! (Base64 Padding 0)"
        print "[+] Replacing [%s] => [%s]" % (base64_encoded_flag0, base64_encoded_fake_flag0)
        buffer = buffer.replace(base64_encoded_flag0, base64_encoded_fake_flag0)
        VALID = True
    base64_encoded_flag1 = flag[1:].encode("base64").replace("\n", "").replace("=", "")
    base64_encoded_fake_flag1 = fake_flag[1:].encode("base64").replace("\n", "").replace("=", "")
    if base64_encoded_flag1 in buffer:
        print "[+] Attack detected! (Base64 Padding 1)"
        print "[+] Replacing [%s] => [%s]" % (base64_encoded_flag1, base64_encoded_fake_flag1)
        buffer = buffer.replace(base64_encoded_flag1, base64_encoded_fake_flag1)
        VALID = True
    base64_encoded_flag2 = flag[2:].encode("base64").replace("\n", "").replace("=", "")
    base64_encoded_fake_flag2 = fake_flag[2:].encode("base64").replace("\n", "").replace("=", "")
    if base64_encoded_flag2 in buffer:
        print "[+] Attack detected! (Base64 Padding 2)"
        print "[+] Replacing [%s] => [%s]" % (base64_encoded_flag2, base64_encoded_fake_flag2)
        buffer = buffer.replace(base64_encoded_flag2, base64_encoded_fake_flag2)
        VALID = True
    # Base32 encoded flag replacment
    base32_encoded_flag0 = b32encode(flag).replace("\n", "").replace("=", "")
    base32_encoded_fake_flag0 = b32encode(fake_flag).replace("\n", "").replace("=", "")
    if base32_encoded_flag0 in buffer:
        print "[+] Attack detected! (Base32 Padding 0)"
        print "[+] Replacing [%s] => [%s]" % (base32_encoded_flag0, base32_encoded_fake_flag0)
        buffer = buffer.replace(base32_encoded_flag0, base32_encoded_fake_flag0)
        VALID = True
    return (VALID, buffer)

def save_payloads(payloads, attacker_host, attacker_port):
    now_time = get_time_human()
    filename = "%s.txt" % (attacker_host)
    print "[!] Saving payload to localfile : [%s]" % (filename)
    with open(filename, "a+") as f:
        f.write("-" * 32 + "\n")
        f.write("[%s:%d]\n" % (attacker_host, attacker_port))
        f.write("[%s]\n" % (now_time))
        f.write("-" * 32 + "\n")
        for payload in payloads:
            if payload[0]:
                f.write("->-> %s\n" % (repr(payload[1])))
            else:
                f.write("<-<- %s\n" % (repr(payload[1])))
        f.write("-" * 32 + "\n")

def print_payloads(payloads):
    for payload in payloads:
        if payload[0]:
            print "->-> %s" % (repr(payload[1]))
        else:
            print "<-<- %s" % (repr(payload[1]))

def get_time_human():
    return time.strftime("%I:%M:%S")

def transfer(src, dst, attacker, attacker_host, attacker_port, direction):
    global data_recoder
    attacker_hash = hash_host_port(attacker_host, attacker_port)
    src_name = src.getsockname()
    src_host = src_name[0]
    src_port = src_name[1]
    dst_name = dst.getsockname()
    dst_host = dst_name[0]
    dst_port = dst_name[1]
    while True:
        buffer = src.recv(0x400)
        if len(buffer) == 0:
            print "[-] No data received! Breaking..."
            break
        data_recoder[attacker_hash].append((direction, buffer))
        if attacker:
            dst.send(buffer)
        else:
            print "[+] %s:%d => %s:%d => Length : [%d]" % (src_host, src_port, dst_host, dst_port, len(buffer))
            result = handle(buffer)
            if result[0]:
                print "[%s]" % ("!" * 32)
                print "[!] Flag thief detected!"
                print_payloads(data_recoder[attacker_hash])
                save_payloads(data_recoder[attacker_hash], attacker_host, attacker_port)
                # Clear saved payloads
                data_recoder[attacker_hash] = []
                # print "[%s] => [%d] ===> %s" % (dst_host, dst_port, attacker_hash)
            dst.send(result[1])
    print "[+] Closing connecions! [%s:%d]" % (src_host, src_port)
    src.close()
    print "[+] Closing connecions! [%s:%d]" % (dst_host, dst_port)
    dst.close()


def server(listen_host, listen_port, remote_host, remote_port, max_connection):
    global data_recoder
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((listen_host, listen_port))
    server_socket.listen(max_connection)
    print '[+] Server started [%s:%d]' %(listen_host, listen_port)
    print '[+] Connect to [%s:%d] to get the content of [%s:%d]' %(listen_host, listen_port, remote_host, remote_port)
    while True:
        attacker_socket, attacker_address = server_socket.accept()
        attacker_host = attacker_address[0]
        attacker_port = attacker_address[1]
        print '[+] Detect connection from [%s:%s]' % (attacker_host, attacker_port)
        print "[+] Adding attacker hash to connection hashtable..."
        attacker_hash = hash_host_port(attacker_host, attacker_port)
        # print "[%s] => [%d] ===> %s" % (attacker_host, attacker_port, attacker_hash)
        print "[+] Using hash : %s" % (attacker_hash)
        data_recoder[attacker_hash] = []
        print "[+] Trying to connect the REMOTE server [%s:%d]" % (remote_host, remote_port)
        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_socket.connect((remote_host, remote_port))
        print "[+] Tunnel connected! Tranfering data..."
        # threads = []
        s = threading.Thread(target=transfer,args=(remote_socket, attacker_socket, False, attacker_host, attacker_port, False)) # D2A
        r = threading.Thread(target=transfer,args=(attacker_socket, remote_socket, True, attacker_host, attacker_port, True)) # A2D
        # threads.append(s)
        # threads.append(r)
        s.start()
        r.start()
    print "[+] Releasing resources..."
    remote_socket.close()
    local_socket.close()
    print "[+] Closing server..."
    server_socket.close()
    print "[+] Server shuted down!"

def main():
    if len(sys.argv) != 5:
        print "Usage : "
        print "\tpython %s [L_HOST] [L_PORT] [R_HOST] [R_PORT]" % (sys.argv[0])
        print "Example : "
        print "\tpython %s 127.0.0.1 8888 127.0.0.1 22" % (sys.argv[0])
        print "Author : "
        print "\tWangYihang <wangyihanger@gmail.com>"
        exit(1)
    LOCAL_HOST = sys.argv[1]
    LOCAL_PORT = int(sys.argv[2])
    REMOTE_HOST = sys.argv[3]
    REMOTE_PORT = int(sys.argv[4])
    MAX_CONNECTION = 0x10
    server(LOCAL_HOST, LOCAL_PORT, REMOTE_HOST, REMOTE_PORT, MAX_CONNECTION)

if __name__ == "__main__":
    main()

