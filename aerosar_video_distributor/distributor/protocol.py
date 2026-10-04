"""
Define the network packet format.
Every frame must contain:
- frame_id
- timestamp
- payload_size
- width
- height
- JPEG image payload
"""

import struct

# Format:
# Q: unsigned long long (8 bytes) for frame_id
# Q: unsigned long long (8 bytes) for timestamp_ns
# I: unsigned int (4 bytes) for payload_size
# I: unsigned int (4 bytes) for width
# I: unsigned int (4 bytes) for height
# Total size: 8 + 8 + 4 + 4 + 4 = 28 bytes
HEADER_FORMAT = "!QQIII"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

def pack_header(frame_id, timestamp_ns, payload_size, width, height):
    """Packs the frame metadata into a binary header."""
    return struct.pack(HEADER_FORMAT, frame_id, timestamp_ns, payload_size, width, height)

def unpack_header(header_bytes):
    """Unpacks the binary header into frame metadata."""
    return struct.unpack(HEADER_FORMAT, header_bytes)
