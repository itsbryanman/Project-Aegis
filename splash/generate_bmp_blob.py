#!/usr/bin/env python3
#
# Copyright (C) 2024 Project Aegis
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Generates an NVIDIA Tegra bmp.blob from PNG images.
# The bmp.blob format is used by the cboot bootloader on Tegra T210
# (NVIDIA SHIELD TV) to display boot splash screens.
#
# Blob format (V2):
#   Header (48 bytes):
#     - magic[16]: "NVIDIA__BLOB__V2"
#     - version: uint32
#     - blob_size: uint32
#     - header_size: uint32
#     - num_entries: uint32
#     - blob_type: uint32 (1 = BMP)
#     - uncomp_size: uint32
#     - padding[2]: uint32
#   Entry (56 bytes each):
#     - name[40]: entry name (null-padded)
#     - data_offset: uint32
#     - data_length: uint32
#     - padded_size: uint32
#     - instance: uint32

import argparse
import io
import struct
import sys

from PIL import Image

BLOB_MAGIC = b"NVIDIA__BLOB__V2"
BLOB_VERSION = 2
BLOB_TYPE_BMP = 1
HEADER_SIZE = 48
ENTRY_SIZE = 56
ALIGNMENT = 4


def pad_to_alignment(size, alignment=ALIGNMENT):
    remainder = size % alignment
    if remainder == 0:
        return size
    return size + (alignment - remainder)


def png_to_bmp_bytes(png_path):
    """Convert a PNG image to BMP format in memory."""
    img = Image.open(png_path)
    # Convert RGBA to RGB (BMP doesn't support alpha in this context)
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (0, 0, 0))
        bg.paste(img, mask=img.split()[3])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    buf = io.BytesIO()
    img.save(buf, format="BMP")
    return buf.getvalue()


def create_blob_entry(name, data_offset, data_length, instance=0):
    """Create a single blob entry (56 bytes)."""
    name_bytes = name.encode("ascii")[:39].ljust(40, b"\x00")
    padded = pad_to_alignment(data_length)
    return struct.pack("<40sIIII", name_bytes, data_offset, data_length, padded, instance)


def create_bmp_blob(entries, output_path):
    """
    Create a bmp.blob file.

    entries: list of (name, bmp_data_bytes, instance) tuples
    output_path: path to write the blob
    """
    num_entries = len(entries)
    header_total = HEADER_SIZE + (ENTRY_SIZE * num_entries)
    data_offset = pad_to_alignment(header_total)

    # Calculate offsets for each entry
    entry_info = []
    current_offset = data_offset
    for name, bmp_data, instance in entries:
        length = len(bmp_data)
        padded = pad_to_alignment(length)
        entry_info.append((name, current_offset, length, padded, instance, bmp_data))
        current_offset += padded

    blob_size = current_offset

    # Build header
    header = struct.pack(
        "<16sIIIII8s",
        BLOB_MAGIC,
        BLOB_VERSION,
        blob_size,
        header_total,
        num_entries,
        BLOB_TYPE_BMP,
        b"\x00" * 8,
    )

    with open(output_path, "wb") as f:
        # Write header
        f.write(header)

        # Write entries
        for name, offset, length, padded, instance, _ in entry_info:
            f.write(create_blob_entry(name, offset, length, instance))

        # Pad to data start
        current_pos = HEADER_SIZE + (ENTRY_SIZE * num_entries)
        if current_pos < data_offset:
            f.write(b"\x00" * (data_offset - current_pos))

        # Write BMP data
        for _, _, length, padded, _, bmp_data in entry_info:
            f.write(bmp_data)
            padding_needed = padded - length
            if padding_needed > 0:
                f.write(b"\x00" * padding_needed)

    return blob_size


def main():
    parser = argparse.ArgumentParser(description="Generate NVIDIA Tegra bmp.blob from PNG images")
    parser.add_argument("--input", "-i", required=True, help="Input PNG file for boot splash")
    parser.add_argument("--output", "-o", required=True, help="Output bmp.blob file")
    args = parser.parse_args()

    print(f"Converting {args.input} to BMP format...")
    bmp_data = png_to_bmp_bytes(args.input)
    print(f"  BMP size: {len(bmp_data)} bytes")

    # The primary boot splash entry is named "nvidia" for cboot compatibility
    entries = [
        ("nvidia", bmp_data, 0),
    ]

    print(f"Creating bmp.blob with {len(entries)} entries...")
    blob_size = create_bmp_blob(entries, args.output)
    print(f"  Blob size: {blob_size} bytes")
    print(f"  Written to: {args.output}")


if __name__ == "__main__":
    main()
