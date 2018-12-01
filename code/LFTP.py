import socket
import enum
import random
import time


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
  def __init__(self, sock):
    # initial data
    self.socket = sock
    self.MSS = 1
    self.windowSize = 4
    self.socket.settimeout(1) # 设置timeout 1s

  def rdp_send(self, filename, c_addr):
    f = open(filename,'rb')
    cnt = 1
    # 判断rwnd是否为0
    ifRwndFull = False
    # 判断是否需要重传
    ifRetransmit = False
    # 下一个需要传的包的序号seq
    currentSeqNum = 1

    # 拥塞窗口cwnd,初始化为1，慢启动
    cwnd = 1
    # 空列表用于暂时保存数据包
    List = []
    # 拥塞窗口的阈值threshold,初始化为25
    threshold = 25
    # 判断是否遇到阻塞
    congested = False
    # 判断线性增长
    congestion_avoidance = False


    # 添加BUFFER暂时存储上一个发送过的包，当丢包发生时执行重传操作
    packet_buffer = ['hello']

    while True:
      seq = cnt
      ack = cnt

      # 随机模拟遇到阻塞
      random_send = random.randint(1,200)
      # 3 duplicate ACKs
      if random_send <= 2:
        # cwnd等于之前的阈值，新阈值等于遭遇阻塞时cwnd的一半
        temp = cwnd
        cwnd = threshold
        threshold = int(temp/2)+1
        congested = True
        congestion_avoidance = True
      else:
        congested = False

      # 线路阻塞，停止发送，线程先休息0.1秒，稍后再继续发送
      if congested == True:
        print('传输线路遇到阻塞，将cwnd快速恢复至', cwnd)
        time.sleep(0.1)
        congested = False
        continue

      # 接收窗口未满，正常发送
      if ifRwndFull == False:
        # 不需要重传
        if ifRetransmit == False:
          data = f.read(MAX_DATA_LENGTH)

          # 阻塞控制
          # cwnd小于阈值，慢启动，指数增加
          if cwnd < threshold and congestion_avoidance == False:
            cwnd *= 2
          # 否则，线性增加
          else:
            cwnd += 1
            congestion_avoidance = True
        # 需要重传
        else:
          ack -= 1
          seq -= 1
          cnt -= 1
          print('需要重传的包序号为 seq = ',seq,'出现丢包事件，将cwnd调整为 cwnd = ',threshold)
          data = packet_buffer[0]
          # cwnd等于之前的阈值，新阈值等于遭遇阻塞时cwnd的一半
          temp = cwnd
          cwnd = threshold
          threshold = int(temp/2)+1

        del packet_buffer[0]
        # 暂存下要传输的包，用于重传机制
        packet_buffer.append(data)
        currentSeqNum = seq

        if str(data) != "b''":
          end = 0
          self.socket.sendto(packet_struct.pack(*(seq,ack,end,data)),c_addr)
        else:
          end = 1
          cnt+=1
          data = 'end'.encode('utf-8')
          self.socket.sendto(packet_struct.pack(*(seq,ack,end,data)),c_addr)
          # 发送成功，等待ack
          recv_data,recv_addr = self.socket.recvfrom(BUFFER_SIZE)
          decode_data = recv_data.decode('utf-8')
          rwnd = decode_data.split[1]
          ack = decode_data.split[0]
          print('接受自',recv_addr,'收到数据为：','rwnd = ', rwnd,
              'ack = ', ack,'发送方的数据：cwnd = ', cwnd)
          break

      # 接收窗口满了，发确认rwnd的包
      else:
        # 不需要重传
        if ifRetransmit == False:
          seq = 0
          end = 0
          data = 'rwnd'.encode('utf-8')
        # 需要重传
        else:
          ack -= 1
          seq -= 1
          cnt -= 1
          data = packet_buffer[0]
      
        del packet_buffer[0]
        # 暂存下要传输的包，用于重传机制
        packet_buffer.append(data)
        currentSeqNum = seq

        self.socket.sendto(packet_struct.pack(*(seq,ack,end,data)),c_addr)

      cnt += 1

      # 发送成功，等待ack
      recv_data,recv_addr = self.socket.recvfrom(BUFFER_SIZE)
      decode_data = recv_data.decode('utf-8')
      rwnd = decode_data.split('$')[1]
      ack = decode_data.split('$')[0]

      # 判断是否丢包
      if ack != currentSeqNum:
        print('收到重复的ACK包: ack=',ack)
        ifRetransmit = True
      else:
        ifRetransmit = False

      # 判断rwnd是否已经满了
      if rwnd == 0:
        ifRwndFull = True
      else:
        ifRwndFull = False
      
      print('接受自',recv_addr,'收到数据为：','rwnd = ', rwnd,
                  'ack = ', ack,'发送方的数据：cwnd = ', cwnd)
    print('文件发送完成，一共发了'+str(cnt),'个包')
    f.close()


  def rdp_recv(self, filename, s_addr):
    # 暂时固定文件目录
    f = open(filename,'wb')
    cnt = 1

    # 接收窗口rwnd,rwnd = RcvBuffer - [LastByteRcvd - LastßyteRead ] 
    rwnd = 50
    # 空列表用于暂时保存数据包
    List = []

    while True:
      recv_data,recv_addr = self.socket.recvfrom(BUFFER_SIZE)
      decode_data = recv_data.decode('uft-8')
      
      # 设置随机丢包，并通知客户端要求重发
      random_drop = random.randint(1,200)
      if random_drop == 11:
        print('接收方已丢失第',decode_data[0],'个包,要求发送方重发')
        # 发送上一个接收到的包的ack
        self.socket.sendto(feedback_struct.pack(*(decode_data[1]-1,rwnd)), recv_addr)
        continue

      cnt += 1
      if rwnd > 0:
        # 服务端为确认rwnd的变化，会继续发送字节为1的包，这里我设置seq为-1代表服务端的确认
        # 此时直接跳过处理这个包，返回rwnd的大小
        if decode_data[0] == 0:
          self.socket.sendto(feedback_struct.pack(*(decode_data[0],rwnd)), recv_addr)
          continue

        # 要求序号要连续，否则将该包直接丢弃，等待下一个序号包的到来
        if decode_data[1] != cnt-1:
          print('服务端接收第',decode_data[0],'个包的序号不正确,要求服务器重发')
          # 发送上一个接收到的包的ack
          self.socket.sendto(feedback_struct.pack(*(decode_data[1]-1,rwnd)), recv_addr)
          continue

        List.append(decode_data)
        rwnd -= 1
        # 接收完毕，发送ACK反馈包
        self.socket.sendto(feedback_struct.pack(*(decode_data[0],rwnd)), recv_addr)
      else:
        self.socket.sendto(feedback_struct.pack(*(decode_data[0],rwnd)), recv_addr)  
      print('已接收第',decode_data[0],'个包','rwnd为',rwnd)
      
      # 随机将数据包写入文件，即存在某一时刻不写入，继续接收
      random_write = random.randint(1,10)
      random_num = random.randint(1,100)
      # 40%机率写入文件,读入文件数也是随机数
      if random_write > 6:
        while len(List) > random_num:
          decode_data = List[0]
          seq = decode_data[0]
          ack = decode_data[1]
          end = decode_data[2]
          data = decode_data[3]
          del List[0]
          rwnd += 1
          if end != 1:
            f.write(data)
          else:
            break
      print(len(List),'end:',decode_data[2])
      # 接收完毕，但是要处理剩下在List中的数据包
      if decode_data[2] == 1:
        break                       
    # 处理剩下在List中的数据包
    while len(List) > 0:
      decode_data = List[0]
      end = decode_data[2]
      data = decode_data[3]
      del List[0]
      rwnd += 1
      if end != 1:
        f.write(data)
      else:
        break
        
    print('文件接收完成，一共收了'+str(cnt),'个包')
    f.close()
