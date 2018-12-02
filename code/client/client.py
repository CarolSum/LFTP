import re
import os
import sys
import socket
sys.path.append("..")
from LFTP import *

def main():
  sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
  lftp = LFTP(sock=sock)
  print('Welcome to LFTP Client Side~')
  while True:
    print('Input Your Command: (Type "quit" to exit.)')
    command = input('eg: LFTP [lsend | lget] [server_addr:port] [filename]\n')
    pattern = re.compile(r'(LFTP) (lsend|lget) (\S+):(\S+) (\S+)')
    match = pattern.match(command)
    try:
        op = match.group(2)
        server_addr = match.group(3)    # include ip addr & port
        server_port = match.group(4)
        filename = match.group(5)
    except:
        if command == 'quit':
          exit(0)
        print('Wrong input!')
        continue
    if op == 'lsend':
      # 判断文件是否存在
      if (os.path.exists(filename) is False):
        print('File not found.')
        continue
      # 请求发送文件
      sock.sendto((op+','+filename).encode(), (server_addr,int(server_port)))
      data,s_addr = sock.recvfrom(1024)
      if data.decode() == 'SERVER: Ready to receive...':
        lftp.rdp_send(filename, s_addr)
        print(filename + ' send successfully')

    elif op == 'lget':
      # 从服务器获取文件
      sock.sendto((op+','+filename).encode(), (server_addr,int(server_port)))
      data,s_addr = sock.recvfrom(1024)
      if data.decode() == 'SERVER: FileNotFound':
        print('File Not Found On Server.')
      elif data.decode() == 'SERVER: ConnectionSetup':
        lftp.rdp_recv(filename, s_addr)
        print('Received ' + filename + ' successfully.')


if __name__ == '__main__':
  main()