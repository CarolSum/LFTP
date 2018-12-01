import socket
import enum
import random


delimeter = '$'
SERVER_ADDR = '127.0.0.1'
SERVER_PORT = '9000'
BUFFER_SIZE = 1024

MAX_DATA_LENGTH = 512   # Total length/pkt must less than 1024

class Header():
  def __init__(self, seqNum = 0, ackNum = 0, rwnd = 0, checksum = 0, ACK = 0, SYN = 0, FIN = 0):
    self.seqNum = seqNum
    self.ackNum = ackNum
    self.ACK = ACK
    self.SYN = SYN
    self.FIN = FIN
    self.rwnd = rwnd
    self.checksum = checksum

  def to_string(self):
    return (str(self.seqNum) + delimeter + str(self.ackNum) + delimeter + 
      str(self.ACK) + delimeter + str(self.SYN) + delimeter + 
      str(self.FIN) + delimeter + str(self.rwnd) + delimeter + str(self.checksum))

class Segment():
  def __init__(self, header, data):
    self.header = header
    self.data = data
  
  def to_string(self):
    return self.header.to_string() + delimeter + str(self.data)

class LFTP():
  def __init__(self, port = 9000, type = 0):
    # initial data
    self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if type == 0:
      self.socket.bind(('127.0.0.1', port))
      print('Server run on 9000...')
    self.MSS = 1
    self.windowSize = 4
    self.socket.settimeout(3) # 设置timeout 3s

  def rdp_send(self, data, c_addr):
    # 将data按MAX_DATA_LENGTH划分
    packets = [data[x*MAX_DATA_LENGTH:x*MAX_DATA_LENGTH+MAX_DATA_LENGTH] for x in range(int(len(data)/MAX_DATA_LENGTH)+1)]
    seq_num = 0
    for index,packet in enumerate(packets):
      header = Header(seqNum=seq_num)
      segment = Segment(header=header,data=packet)
      self.socket.sendto(segment.to_string().encode(), c_addr)
      while True:
        try:
          rcv_data,rcv_addr = self.socket.recvfrom(BUFFER_SIZE)
        except:
          # 发生超时
          print('Send: Receive ACK TIMEOUT...Trying to resend seg-%d to (%s:%s)...' % index, c_addr)
          self.socket.sendto(segment.to_string().encode(), c_addr)
          continue
        _data = rcv_data.decode()
        _ACK = _data.split(delimeter)[2]
        _ackNum = _data.split(delimeter)[1]
        if(int(_ACK) == 1 and int(_ackNum) == seq_num):
          print('Send: Segment-%d sent successfully!' % index)
          seq_num += 1
          break
    return True

  def rdp_recv(self, filename, s_addr):
    data = ''
    seq_num = random.randint(1,10)
    cnt = 3
    while True:
      try:
        rcv_data,rcv_addr = self.socket.recvfrom(BUFFER_SIZE)
      except:
        if cnt > 0:
          print('Receive packet TIMEOUT...')
          cnt-=1
          continue
        else:
          print('Nothing Received. Finish.')
          return data
      _data = rcv_data.decode()
      header = Header(seqNum=seq_num, ackNum=_data.split(delimeter)[0], ACK=1)
      segment = Segment(header, '')
      self.socket.sendto(segment.to_string().encode(), rcv_addr)
      data += _data.split(delimeter)[7]
      break
    return data

  def connect(self, addr = SERVER_ADDR, port = SERVER_PORT):
    header = Header()
    pass

  def listen(self):
    # while True:
    #   print(self.rdp_recv())
    pass

  def accept(self):
    pass

  def __del__(self):
    # teardown
    self.socket.close()
    pass