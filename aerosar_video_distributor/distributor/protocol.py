"""
Backwards-compatibility shim for distributor.protocol -> protocol.py
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from protocol import (
    HEADER_FORMAT,
    HEADER_SIZE,
    create_packet,
    read_exact,
    read_header,
    read_packet,
    send_packet,
    send_raw_packet,
)

__all__ = [
    "HEADER_FORMAT",
    "HEADER_SIZE",
    "create_packet",
    "read_exact",
    "read_header",
    "read_packet",
    "send_packet",
    "send_raw_packet",
]
