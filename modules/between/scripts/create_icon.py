"""Rasterize a simple vector icon without additional build dependencies."""
from pathlib import Path
import struct
import zlib

size = 32
pixels = bytearray()
for y in range(size):
    pixels.append(0)
    for x in range(size):
        # Two connected speech bubbles represent a link between messages.
        light = (6 <= x <= 20 and 6 <= y <= 14) or (12 <= x <= 26 and 19 <= y <= 26) or (17 <= x <= 19 and 14 <= y <= 19)
        pixels.extend((222, 240, 224, 255) if light else (18, 43, 49, 255))
def chunk(name, data):
    return struct.pack('!I', len(data)) + name + data + struct.pack('!I', zlib.crc32(name + data))
png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', size, size, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(pixels)) + chunk(b'IEND', b'')
root = Path(__file__).resolve().parents[1] / 'src-tauri/icons'
root.mkdir(parents=True, exist_ok=True)
(root / 'icon.png').write_bytes(png)
(root / 'icon.ico').write_bytes(struct.pack('<3H', 0, 1, 1) + struct.pack('<4B2H2I', size, size, 0, 0, 1, 32, len(png), 22) + png)
