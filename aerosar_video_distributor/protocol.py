import struct
import socket

try:
    from config import MAX_FRAME_SIZE
except ImportError:
    MAX_FRAME_SIZE = 5 * 1024 * 1024

# Header format: [4 bytes frame_id] [8 bytes timestamp] [4 bytes payload_size]
# Using network byte order (big-endian)
HEADER_FORMAT = ">IQI"
HEADER_SIZE = 16

def create_packet(frame_id: int, timestamp: int, jpeg_bytes: bytes) -> bytes:
    payload_size = len(jpeg_bytes)
    header = struct.pack(HEADER_FORMAT, frame_id, timestamp, payload_size)
    return header + jpeg_bytes

def read_exact(sock: socket.socket, size: int) -> bytes | None:
    data = bytearray()
    while len(data) < size:
        packet = sock.recv(size - len(data))
        if not packet:
            return None
        data.extend(packet)
    return bytes(data)

def read_header(sock: socket.socket) -> tuple[tuple[int, int, int], bytes] | None:
    header_data = read_exact(sock, HEADER_SIZE)
    if not header_data:
        return None
    return struct.unpack(HEADER_FORMAT, header_data), header_data

def read_packet(sock: socket.socket):
    """Reads header and payload. Returns (frame_id, timestamp, jpeg_bytes, raw_packet) or None if disconnected."""
    header_info = read_header(sock)
    if not header_info:
        return None
        
    header, header_data = header_info
    frame_id, timestamp, payload_size = header
    
    if payload_size > MAX_FRAME_SIZE or payload_size < 0:
        print(f"[ERROR] Invalid payload size: {payload_size}")
        return None
        
    jpeg_bytes = read_exact(sock, payload_size)
    if not jpeg_bytes:
        return None
        
    raw_packet = header_data + jpeg_bytes
    return frame_id, timestamp, jpeg_bytes, raw_packet

def send_packet(sock: socket.socket, frame_id: int, timestamp: int, jpeg_bytes: bytes) -> bool:
    packet = create_packet(frame_id, timestamp, jpeg_bytes)
    return send_raw_packet(sock, packet)

def send_raw_packet(sock: socket.socket, raw_packet: bytes) -> bool:
    try:
        sock.sendall(raw_packet)
        return True
    except (ConnectionError, OSError):
        return False
