#!/usr/bin/env python3
"""Memory-bounded UnityFS bundle writer.

UnityPy's ``BundleFile.save()`` materializes the complete uncompressed file
data (2.6 GB for Fallout Shelter 2.7.0) and then the compressed bundle. On a
machine with the game and toolchain already resident that spikes past available
RAM. This writer keeps file data and compressed blocks on temporary files and
copies them to the destination stream, so peak memory is bounded by the largest
single asset plus the LZ4 chunk size.

The layout follows UnityPy 1.25.3 ``BundleFile.save_fs``.
"""
import gc
import tempfile
from pathlib import Path

from UnityPy.files.BundleFile import BundleFile
from UnityPy.helpers import CompressionHelper
from UnityPy.streams import EndianBinaryReader, EndianBinaryWriter


def _file_data(f):
    if isinstance(f, (EndianBinaryReader, EndianBinaryWriter)):
        return f.bytes
    return f.save()


def _copy(writer, stream, chunk_size=1 << 20):
    while True:
        chunk = stream.read(chunk_size)
        if not chunk:
            return
        writer.write(chunk)


def _compress_stream(src, dst, block_info_flag):
    """Compress src -> dst in UnityFS blocks; return block metadata."""
    switch = int(block_info_flag) & 0x3F
    chunk_size = CompressionHelper.COMPRESSION_CHUNK_SIZE_MAP[switch]
    compress = CompressionHelper.COMPRESSION_MAP[switch]
    blocks = []
    size = 0

    if switch == 0:
        while True:
            chunk = src.read(1 << 20)
            if not chunk:
                break
            dst.write(chunk)
            size += len(chunk)
        return [(size, size, block_info_flag)] if size else []

    while True:
        chunk = src.read(chunk_size)
        if not chunk:
            break
        raw_size = len(chunk)
        packed = compress(chunk)
        if len(packed) > raw_size:
            dst.write(chunk)
            blocks.append((raw_size, raw_size, block_info_flag ^ switch))
        else:
            dst.write(packed)
            blocks.append((raw_size, len(packed), block_info_flag))
        size += raw_size
    if size == 0:
        blocks.append((0, 0, block_info_flag))
    return blocks


def save_bundle(bundle: BundleFile, path: Path):
    """Write a UnityFS bundle without holding its full uncompressed payload."""
    if bundle.signature != "UnityFS":
        raise NotImplementedError(f"streaming writer supports UnityFS, not {bundle.signature}")

    data_flag = int(bundle.dataflags)
    block_info_flag = int(bundle._block_info_flags)

    # UnityPy always writes directory info; encryption is not implemented.
    if block_info_flag & bundle.dataflags.UsesAssetBundleEncryption:
        block_info_flag ^= bundle.dataflags.UsesAssetBundleEncryption
    if data_flag & bundle.dataflags.UsesAssetBundleEncryption:
        data_flag ^= bundle.dataflags.UsesAssetBundleEncryption
    if not data_flag & 0x40:
        raise NotImplementedError("UnityPy always writes DirectoryInfo, so data_flag must include 0x40")

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryFile(dir=path.parent) as file_tmp, \
         tempfile.TemporaryFile(dir=path.parent) as block_tmp:
        files = []
        for name, f in bundle.files.items():
            data = _file_data(f)
            file_tmp.write(data)
            files.append((name, f.flags, len(data)))
            del data
            gc.collect()

        file_tmp.seek(0)
        block_info = _compress_stream(file_tmp, block_tmp, block_info_flag)
        block_tmp.seek(0)

        # Block info (directory + block table), compressed with the data codec.
        block_writer = EndianBinaryWriter(b"\x00" * 0x10)
        block_writer.write_int(len(block_info))
        for raw_size, packed_size, flag in block_info:
            block_writer.write_u_int(raw_size)
            block_writer.write_u_int(packed_size)
            block_writer.write_u_short(flag)
        block_writer.write_int(len(files))
        offset = 0
        for f_name, f_flag, f_len in files:
            block_writer.write_long(offset)
            block_writer.write_long(f_len)
            offset += f_len
            block_writer.write_u_int(f_flag)
            block_writer.write_string_to_null(f_name)
        block_raw = block_writer.bytes
        block_writer.dispose()
        block_raw_size = len(block_raw)
        switch = data_flag & 0x3F
        block_data = CompressionHelper.COMPRESSION_MAP[switch](block_raw)
        del block_raw

        with open(path, "wb") as out:
            writer = EndianBinaryWriter(out)
            writer.write_string_to_null(bundle.signature)
            writer.write_u_int(bundle.version)
            writer.write_string_to_null(bundle.version_player)
            writer.write_string_to_null(bundle.version_engine)

            header_pos = writer.Position
            writer.write_long(0)  # patched at end
            writer.write_u_int(len(block_data))
            writer.write_u_int(block_raw_size)
            writer.write_u_int(data_flag)

            if bundle._uses_block_alignment:
                writer.align_stream(16)

            if data_flag & 0x80:
                if data_flag & 0x200:
                    writer.align_stream(16)
                _copy(writer, block_tmp)       # compressed file data
                writer.write(block_data)       # block info
            else:
                writer.write(block_data)       # block info
                if data_flag & 0x200:
                    writer.align_stream(16)
                _copy(writer, block_tmp)       # compressed file data

            end_pos = writer.Position
            writer.Position = header_pos
            writer.write_long(end_pos)
            writer.Position = end_pos


if __name__ == "__main__":
    raise SystemExit("import save_bundle from build_patch")
