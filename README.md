# LFTP

LFTP -- Large File Transfer Protocol -- is designed to support large file transfer between two computers in the Internet.

## Feature

- Use UDP as the transport layer protocol 
- Realize 100% reliability as TCP
- Implement congestion control function similar as TCP
- LFTP Server side is able to support multiple clients at the same time
- Provide meaningful debug info when programs are executed

## How to run

Client Side:

Use **LFTP lsend myserver mylargefile** to send file to server and **LFTP lget myserver mylargefile** to get file from server.

Server side:

Simply setup server.py and wait for connections from clients.

## Todo

- [x] lsend & lget
- [x] segment structure
- [x] reliable data transfer
- [x] flow control
- [x] congestion control
- [x] multithread support
- [x] debug info

*Remote Connection Maybe Not Work*