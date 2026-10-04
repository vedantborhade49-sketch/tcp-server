import struct
import socket

# Header format: [4 bytes frame_id] [8 bytes timestamp] [4 bytes payload_size]
# Using network byte order (big-endian)
HEADER_FORMAT = ">IQI"
HEADER_SIZE = 16

def create_packet(frame_id: int, timestamp: int, jpeg_bytes: bytes) -> bytes:
    payload_size = len(jpeg_bytes)
    header = struct.pack(HEADER_FORMAT, frame_id, timestamp, payload_size)
    return header + jpeg_bytes

def read_exact(sock: socket.socket, size: int) -> bytes:
    data = bytearray()
    while len(data) < size:
        packet = sock.recv(size - len(data))
        if not packet:
            return None
        data.extend(packet)
    return bytes(data)

def read_header(sock: socket.socket):
    header_data = read_exact(sock, HEADER_SIZE)
    if not header_data:
        return None
    return struct.unpack(HEADER_FORMAT, header_data)

def read_packet(sock: socket.socket):
    """Reads header and payload. Returns (frame_id, timestamp, jpeg_bytes) or None if disconnected."""
    header = read_header(sock)
    if not header:
        return None
        
    frame_id, timestamp, payload_size = header
    
    jpeg_bytes = read_exact(sock, payload_size)
    if not jpeg_bytes:
        return None
        
    return frame_id, timestamp, jpeg_bytes

def send_packet(sock: socket.socket, frame_id: int, timestamp: int, jpeg_bytes: bytes) -> bool:
    packet = create_packet(frame_id, timestamp, jpeg_bytes)
    try:
        sock.sendall(packet)
        return True
    except (ConnectionError, OSError):
        return False
