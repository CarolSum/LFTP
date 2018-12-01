from LFTP import *

def main():
  server = LFTP()
  while True:
    print(server.rdp_recv())

if __name__ == '__main__':
    main()