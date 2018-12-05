import socket
import enum
import random
import time

delimeter = '$'
SERVER_ADDR = '127.0.0.1'
SERVER_PORT = '9000'
BUFFER_SIZE = 1024 + 32

MAX_DATA_LENGTH = 1024   # 数据包总大小小于或等于1024

class Header():
  def __init__(self, seqNum = 0, ackNum = 0, END = 0, rwnd = 0):
    self.seqNum = seqNum    # 0
    self.ackNum = ackNum    # 1
    self.END = END          # 2
    self.rwnd = rwnd        # 3

  def to_string(self):
    return (str(self.seqNum) + delimeter + str(self.ackNum) + delimeter + 
      str(self.END) + delimeter + str(self.rwnd))

class Segment():
  def __init__(self, header, data = "b''".encode()):
    self.header = header
    self.data = data
  
  def encode_str(self):
    return (self.header.to_string() + delimeter).encode() + self.data

class LFTP():
  def __init__(self, sock):
    # initial data
    self.socket = sock
    self.rwnd = 50               # rwnd = RcvBuffer - [LastByteRcvd - LastßyteRead ]
    self.socket.settimeout(3)    # timeout 3s
    self.ifRwndFull = False      # 记录rwnd是否已满，true-满了 false-没满
    self.ifRetransmit = False    # 记录是否需要重传，true-需要 false-不需要
    self.congested = False       # 记录是否遇到阻塞，true-是 false-否
    self.congestion_avoidance = False # 线性增长，true-是 false-否
    self.threshold = 25          # 拥塞窗口的阈值

  def rdp_send(self, filename, c_addr):
    f = open(filename,'rb')
    self.ifRwndFull = False
    self.ifRetransmit = False
    self.congested = False
    self.congestion_avoidance = False
    self.threshold = 25

    cnt = 1             # 用于发送包的数量
    currentSeqNum = 1   # 下一个需要传的包的序号seq，用于ack
    cwnd = 1            # 拥塞窗口cwnd，首次启动使用慢启动机制
    pkt_buffer = [b'']  # 发送包缓存

    while True:
      seq = cnt
      ack = cnt

      # 随机模拟遇到阻塞
      tempBoolean = self.randomFactory(1, 150, 6)
      if tempBoolean == True:
        temp = cwnd
        cwnd = self.threshold
        self.threshold = int(temp / 2) + 1
        self.congested = True
        self.congestion_avoidance = True
      else:
        self.congested = False

      # 线路阻塞，停止发送
      if self.congested == True:
        print('Congestion happend, set cwnd = ', cwnd)
        time.sleep(0.1)
        self.congested = False
        continue

      if self.ifRwndFull == False:
        if self.ifRetransmit == False:
          data = f.read(MAX_DATA_LENGTH)
          # 阻塞控制
          # 慢启动，指数增加
          if cwnd < self.threshold and self.congestion_avoidance == False:
            cwnd = cwnd * 2
          # 线性增加
          else:
            cwnd = cwnd + 1
            self.congestion_avoidance = True
        else:
          temp = cwnd
          cwnd = self.threshold
          self.threshold = int(temp/2)+1
          ack = ack - 1
          seq = seq - 1
          cnt = cnt - 1
          print('The seq of retransmited package is: seq = ',seq,'. Package has been lost, set cwnd = ',cwnd)
          data = pkt_buffer[0]
        
        del pkt_buffer[0]
        pkt_buffer.append(data)
        currentSeqNum = seq        # 更新seqNum，缓存包

        if str(data) == "b''":
          end = 1
          cnt = cnt + 1
          data = 'end'.encode()
          header = Header(seqNum=seq,ackNum=ack,END=1)
          seg = Segment(header, data)
          self.socket.sendto(seg.encode_str(),c_addr)
          
          # 发送成功，等待ack
          recv_data,recv_addr = self.socket.recvfrom(BUFFER_SIZE)
          decode_data = self.segment_split(recv_data)
          ack = decode_data[1]
          rwnd = decode_data[3]
          
          print('Recived from ',recv_addr,'which data is ','rwnd = ', rwnd,
              'ack = ', ack,'Sender data：cwnd = ', cwnd)
          break
        else:
          end = 0
          header = Header(seqNum=seq,ackNum=ack,END=0)
          seg = Segment(header, data)
          self.socket.sendto(seg.encode_str(),c_addr)

      # 接收窗口满了，发确认rwnd的包
      else:
        if self.ifRetransmit == False:
          seq = 0
          end = 0
          data = 'rwnd'.encode()
        # 需要重传
        else:
          ack = ack - 1
          seq = seq - 1
          cnt = cnt - 1
          data = pkt_buffer[0]
      
        del pkt_buffer[0]
        pkt_buffer.append(data)
        
        currentSeqNum = seq
        header = Header(seqNum=seq,ackNum=ack,END=end)
        seg = Segment(header, data)
        self.socket.sendto(seg.encode_str(),c_addr)

      cnt += 1

      # 发送成功，等待ack
      recv_data,recv_addr = self.socket.recvfrom(BUFFER_SIZE)
      decode_data = self.segment_split(recv_data)
      rwnd = decode_data[3]
      ack = decode_data[1]

      if ack != currentSeqNum:
        self.ifRetransmit = True
        print('Recived duplication ack : ack=',ack)
      else:
        self.ifRetransmit = False

      # 判断rwnd是否已经满了
      if rwnd == 0:
        self.ifRwndFull = True
      else:
        self.ifRwndFull = False
      
      print('Reciver data: ','rwnd = ', rwnd,'ack = ', ack,'Sender data：cwnd = ', cwnd)
    print('File transmition completed! Statictis: has transmited '+ str(cnt),' packages')
    f.close()


  def rdp_recv(self, filename, s_addr):
    f = open(filename,'wb')
    self.rwnd = 50
    # 接收缓存
    recv_buffer = []
    cnt = 1
    while True:
      recv_data,recv_addr = self.socket.recvfrom(BUFFER_SIZE)
      res =  self.segment_split(recv_data)     

      rcv_seq = res[0]
      rcv_ack = res[1]
      rcv_end = res[2]

      # 设置随机丢包，并通知客户端要求重发
      random_drop = random.randint(1,200)
      if random_drop == 11:
        print('Reciver has lost No. ',rcv_seq,' packages, requesting for retransmition……')
        # 发送上一个接收到的包的ack
        header = Header(ackNum=rcv_ack-1,rwnd=self.rwnd)
        seg = Segment(header)
        self.socket.sendto(seg.encode_str(), recv_addr)
        continue

      cnt = cnt + 1
      if self.rwnd > 0:
        # 服务端为确认rwnd的变化，会继续发送字节为1的包，这里我设置seq为-1代表服务端的确认
        # 此时直接跳过处理这个包，返回rwnd的大小
        if rcv_ack == 0:
          header = Header(ackNum=rcv_seq,rwnd=self.rwnd)
          seg = Segment(header)
          self.socket.sendto(seg.encode_str(), recv_addr)
          continue

        # 要求序号要连续，否则将该包直接丢弃，等待下一个序号包的到来
        if rcv_ack != cnt-1:
          print('Server has recived No. ',rcv_seq,' which is not needed, requesting for retransmition……')
          # 发送上一个接收到的包的ack
          header = Header(ackNum=rcv_ack-1,rwnd=self.rwnd)
          seg = Segment(header)
          self.socket.sendto(seg.encode_str(), recv_addr)
          continue

        recv_buffer.append(recv_data)
        self.rwnd -= 1
        # 接收完毕，发送ACK反馈包
        header = Header(ackNum=rcv_seq,rwnd=self.rwnd)
        seg = Segment(header)
        self.socket.sendto(seg.encode_str(), recv_addr)
      else:
        header = Header(ackNum=rcv_seq,rwnd=self.rwnd)
        seg = Segment(header)
        self.socket.sendto(seg.encode_str(), recv_addr)
      print('Now, recived No. ',rcv_seq,', whoes rwnd is ',self.rwnd,' the end is: ',rcv_end,'……')
      
      # 随机将数据包写入文件，即存在某一时刻不写入，继续接收
      random_write = self.randomFactory(1, 20, 6)
      random_num = random.randint(1,80)
      # 读写文件数设置为随机数
      if random_write == False:
        while len(recv_buffer) > random_num:
          recv_data = recv_buffer[0]
          split_result =  self.segment_split(recv_data)

          end = split_result[2]
          data = split_result[4]

          del recv_buffer[0]
          self.rwnd += 1
          if end != 1:
            f.write(data)
          else:
            break
      if rcv_end == 1:
        break                       
    # 成功接收之后，处理在recv_buffer中的数据包
    for recv_data in recv_buffer:
      split_result =  self.segment_split(recv_data)
      end = split_result[2]
      data = split_result[4]
      self.rwnd += 1
      if end == 1:
        break
      else:
        f.write(data)
        
    print('File transmition completed! Statictis: has transmited '+str(cnt),' packages.')
    f.close()

  # 对接收到的segment进行切分, 以分离header和data
  def segment_split(self, recv_data):
    count = 0
    begin = -1
    while count < 4:
      begin = recv_data.find('$'.encode(), begin+1)
      count+=1
    raw_data = recv_data[begin+1:]
    header_bytes = recv_data[:begin+1]

    decode_data = header_bytes.decode()
    rcv_seq = int(decode_data.split('$')[0])
    rcv_ack = int(decode_data.split('$')[1])
    rcv_end = int(decode_data.split('$')[2])
    rcv_rwnd = int(decode_data.split('$')[3])
    rcv_data = raw_data
    return [rcv_seq, rcv_ack, rcv_end, rcv_rwnd, rcv_data]

  def randomFactory(self, minA, maxB, thres):
    num = random.randint(minA, maxB)
    if num <= thres:
      return True
    else:
      return False