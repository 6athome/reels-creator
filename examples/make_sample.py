"""Generate original synthetic PNGs for an offline smoke test."""
import argparse
from pathlib import Path
import struct
import zlib


def chunk(kind, payload):
    return (struct.pack(">I", len(payload)) + kind + payload +
            struct.pack(">I", zlib.crc32(kind + payload)))


def image(color, index):
    width, height = 270, 480
    data = bytearray()
    for y in range(height):
        data.append(0)
        for x in range(width):
            inside = (x - 80 - index * 35) ** 2 + (y - 205) ** 2 < 65 ** 2
            data.extend((223, 192, 154) if inside else tuple(min(255, c + y // 20) for c in color))
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(data)) + chunk(b"IEND", b"")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    args.folder.mkdir(parents=True, exist_ok=True)
    for i, color in enumerate(((57, 43, 61), (49, 75, 71), (98, 62, 53)), 1):
        path = args.folder / f"{i:02d} 샘플 사진.png"
        with path.open("xb") as file:
            file.write(image(color, i))
        print(path)


if __name__ == "__main__":
    main()
