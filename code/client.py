from LFTP import *
import re
import os

def main():
  client = LFTP(type=1)
  print('Welcome to LFTP Client Side~')
  while True:
    print('Input Your Command: ')
    command = input('eg: LFTP [lsend | lget] [server_addr] [filename]\n')
    pattern = re.compile(r'(LFTP) (lsend|lget) (\S+) (\S+)')
    match = pattern.match(command)
    try:
        op = match.group(2)
        server_addr = match.group(3)
        filename = match.group(4)
    except:
        if command == 'quit':
          exit(0)
        print('Wrong input!')
        continue
    if op == 'lsend':
      # 发送文件
      if (os.path.exists(filename) is False):
        print('File not found.')
        continue
      with open(filename, 'rb') as f:
        # file size should be very small
        client.rdp_send(f.read())
        f.close()
      # for data in ['Michael', 'Tracy', 'Sarah']:
      #   # 发送数据:
      #   client.rdp_send(data.encode())
    elif op == 'lget':
      # 从服务器获取文件
      print('')


if __name__ == '__main__':
  main()