from LFTP import *
import socket
import threading
import os

PORT = 9000

'''
data: 'lget,file1.txt' | 'lsend,file1.txt'
'''
def server_thread(data, addr):
  recv_data = data.decode()
  try:
    op = recv_data.split(',')[0]
    filename = recv_data.split(',')[1]
  except:
    print('Something goes wrong.')
    return
  if op == 'lget':
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if not os.path.exists(filename):
      # FileNotFound
      s.sendto('SERVER: FileNotFound'.encode(), addr)
      s.close()
    else:
      s.sendto('SERVER: ConnectionSetup'.encode(), addr)
      lftp = LFTP(sock=s)
      lftp.rdp_send(filename, addr)
      s.close()
  elif op == 'lsend':
    s.sendto('SERVER: Ready to receive...'.encode(), addr)
    lftp = LFTP(sock=s)
    lftp.rdp_recv(filename, addr)
    s.close()

def main():
  sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
  sock.bind(('127.0.0.1', PORT))
  while True:
    rcv_data, rcv_addr = sock.recvfrom(1024)
    # 多线程处理请求
    mThread = threading.Thread(target=server_thread,args=(rcv_data, rcv_addr))
    mThread.start()

if __name__ == '__main__':
    main()