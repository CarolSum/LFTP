import socket
import enum
import random
import time

delimeter = '$'
SERVER_ADDR = '127.0.0.1'
SERVER_PORT = '9000'
BUFFER_SIZE = 1024 + 32

MAX_DATA_LENGTH = 1024   # Total length/pkt must less than 1024

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
    # 接收窗口rwnd = RcvBuffer - [LastByteRcvd - LastßyteRead ] 
    self.rwnd = 50
    self.socket.settimeout(1) # 设置timeout 1s
    # 判断rwnd是否已满
    self.ifRwndFull = False
    # 判断是否需要重传
    self.ifRetransmit = False
    # 判断是否遇到阻塞
    self.congested = False
    # 判断线性增长
    self.congestion_avoidance = False
    # 拥塞窗口的阈值
    self.threshold = 25

  def rdp_send(self, filename, c_addr):
    f = open(filename,'rb')
    self.ifRwndFull = False
    self.ifRetransmit = False
    self.congested = False
    self.congestion_avoidance = False
    self.threshold = 25

    # 发送包的数量
    cnt = 1
    # 下一个需要传的包的序号seq
    currentSeqNum = 1
    # 拥塞窗口cwnd,初始化为1，慢启动
    cwnd = 1
    # 发送包缓存, 保存最近发送的包
    pkt_buffer = [b'']

    while True:
      seq = cnt
      ack = cnt

      # 随机模拟遇到阻塞
      random_send = random.randint(1,200)
      # 3 duplicate ACKs
      if random_send <= 2:
        # cwnd等于之前的阈值，新阈值等于遭遇阻塞时cwnd的一半
        temp = cwnd
        cwnd = self.threshold
        self.threshold = int(temp/2)+1
        self.congested = True
        self.congestion_avoidance = True
      else:
        self.congested = False

      # 线路阻塞，停止发送，线程先休息0.1秒，稍后再继续发送
      if self.congested == True:
        print('传输线路遇到阻塞，将cwnd快速恢复至', cwnd)
        time.sleep(0.1)
        self.congested = False
        continue

      # 接收窗口未满，正常发送
      if self.ifRwndFull == False:
        # 不需要重传
        if self.ifRetransmit == False:
          data = f.read(MAX_DATA_LENGTH)
          # 阻塞控制
          # cwnd小于阈值，慢启动，指数增加
          if cwnd < self.threshold and self.congestion_avoidance == False:
            cwnd *= 2
          # 否则，线性增加
          else:
            cwnd += 1
            self.congestion_avoidance = True
        # 需要重传
        else:
          ack -= 1
          seq -= 1
          cnt -= 1
          print('需要重传的包序号为 seq = ',seq,'出现丢包事件，将cwnd调整为 cwnd = ',self.threshold)
          data = pkt_buffer[0]
          # cwnd等于之前的阈值，新阈值等于遭遇阻塞时cwnd的一半
          temp = cwnd
          cwnd = self.threshold
          self.threshold = int(temp/2)+1

        del pkt_buffer[0]
        # 暂存下要传输的包，用于重传机制
        pkt_buffer.append(data)
        currentSeqNum = seq

        if str(data) != "b''":
          end = 0
          header = Header(seqNum=seq,ackNum=ack,END=0)
          seg = Segment(header, data)
          self.socket.sendto(seg.encode_str(),c_addr)
        else:
          end = 1
          cnt+=1
          data = 'end'.encode()
          header = Header(seqNum=seq,ackNum=ack,END=1)
          seg = Segment(header, data)
          self.socket.sendto(seg.encode_str(),c_addr)
          # 发送成功，等待ack
          recv_data,recv_addr = self.socket.recvfrom(BUFFER_SIZE)
          decode_data = self.segment_split(recv_data)
          rwnd = decode_data[3]
          ack = decode_data[1]
          print('接受自',recv_addr,'收到数据为：','rwnd = ', rwnd,
              'ack = ', ack,'发送方的数据：cwnd = ', cwnd)
          break

      # 接收窗口满了，发确认rwnd的包
      else:
        # 不需要重传
        if self.ifRetransmit == False:
          seq = 0
          end = 0
          data = 'rwnd'.encode()
        # 需要重传
        else:
          ack -= 1
          seq -= 1
          cnt -= 1
          data = pkt_buffer[0]
      
        del pkt_buffer[0]
        # 暂存下要传输的包，用于重传机制
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

      # 判断是否丢包
      if ack != currentSeqNum:
        print('收到重复的ACK包: ack=',ack)
        self.ifRetransmit = True
      else:
        self.ifRetransmit = False

      # 判断rwnd是否已经满了
      if rwnd == 0:
        self.ifRwndFull = True
      else:
        self.ifRwndFull = False
      
      print('接受自',recv_addr,'收到数据为：','rwnd = ', rwnd,
                  'ack = ', ack,'发送方的数据：cwnd = ', cwnd)
    print('文件发送完成，一共发了'+str(cnt),'个包')
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
        print('接收方已丢失第',rcv_seq,'个包,要求发送方重发')
        # 发送上一个接收到的包的ack
        header = Header(ackNum=rcv_ack-1,rwnd=self.rwnd)
        seg = Segment(header)
        self.socket.sendto(seg.encode_str(), recv_addr)
        continue

      cnt += 1
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
          print('服务端接收第',rcv_seq,'个包的序号不正确,要求服务器重发')
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
      print('已接收第',rcv_seq,'个包','rwnd为',self.rwnd)
      
      # 随机将数据包写入文件，即存在某一时刻不写入，继续接收
      random_write = random.randint(1,10)
      random_num = random.randint(1,100)
      # 40%机率写入文件,读入文件数也是随机数
      if random_write > 6:
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
      print(len(recv_buffer),'end:',rcv_end)
      # 接收完毕，但是要处理剩下在recv_buffer中的数据包
      if rcv_end == 1:
        break                       
    # 处理剩下在recv_buffer中的数据包
    while len(recv_buffer) > 0:
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
        
    print('文件接收完成，一共收了'+str(cnt),'个包')
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