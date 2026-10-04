"""
AEROSAR - Simple 16-Byte Length-Prefixed Video Transport Protocol

Packet Format:
[4 bytes frame_id]     -> uint32 (big-endian)
[8 bytes timestamp]    -> uint64 (big-endian)
[4 bytes payload_size] -> uint32 (big-endian)
[JPEG bytes]           -> raw JPEG image payload
Total Header Size: 16 bytes
"""
import struct
import socket
from typing import Tuple

HEADER_FORMAT = ">IQI"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # 16 bytes


def create_packet(frame_id: int, timestamp: int, jpeg_bytes: bytes) -> bytes:
    """Packs frame metadata and JPEG bytes into a single binary packet."""
    header = struct.pack(HEADER_FORMAT, frame_id, timestamp, len(jpeg_bytes))
    return header + jpeg_bytes


def read_exact(sock: socket.socket, size: int) -> bytes:
    """Receives exactly 'size' bytes from the socket or raises ConnectionError."""
    buf = bytearray()
    while len(buf) < size:
        chunk = sock.recv(size - len(buf))
        if not chunk:
            raise ConnectionError("Socket connection closed by remote peer")
        buf.extend(chunk)
    return bytes(buf)


def read_header(sock: socket.socket) -> Tuple[int, int, int]:
    """
    Reads exactly 16 bytes from socket and unpacks header.
    Returns: (frame_id, timestamp, payload_size)
    """
    header_bytes = read_exact(sock, HEADER_SIZE)
    frame_id, timestamp, payload_size = struct.unpack(HEADER_FORMAT, header_bytes)
    return frame_id, timestamp, payload_size


def read_packet(sock: socket.socket) -> Tuple[int, int, bytes]:
    """
    Reads a complete frame packet from socket.
    Returns: (frame_id, timestamp, jpeg_bytes)
    """
    frame_id, timestamp, payload_size = read_header(sock)
    jpeg_bytes = read_exact(sock, payload_size)
    return frame_id, timestamp, jpeg_bytes


def send_packet(sock: socket.socket, frame_id: int, timestamp: int, jpeg_bytes: bytes) -> None:
    """Packs and transmits a complete frame packet over the socket."""
    packet = create_packet(frame_id, timestamp, jpeg_bytes)
    sock.sendall(packet)


def send_raw_packet(sock: socket.socket, raw_packet: bytes) -> None:
    """Sends pre-assembled packet bytes directly over the socket."""
    sock.sendall(raw_packet)
