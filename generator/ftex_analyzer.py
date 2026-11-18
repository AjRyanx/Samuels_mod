#!/usr/bin/env python3
"""Simple .ftex file analyzer to understand the format."""
import struct

def analyze_ftex(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()

    print(f"File: {filepath}")
    print(f"Size: {len(data)} bytes")
    
    # Parse header (based on what we saw from the inspect function)
    if data[:4] == b'FTEX':
        print("Magic: FTEX")
        fmt = struct.unpack_from('<H', data, 8)[0]
        width = struct.unpack_from('<H', data, 10)[0]
        height = struct.unpack_from('<H', data, 12)[0]
        mips = data[16]
        print(f"Format: {fmt:#x} (size_code)")
        print(f"Size: {width}x{height}")
        print(f"MIPs: {mips}")

        # Check what's after header (what we saw in the first 64 bytes)
        print(f"First 64 bytes (hex): {data[:64].hex(' ')}")
        
        # Let's check the actual data at these offsets
        print(f"\nHeader structure:")
        print(f"- Magic: {data[:4]}")
        print(f"- Bytes 4-7: {data[4:8].hex()}")
        print(f"- Bytes 8-9: {data[8:10].hex()}")
        print(f"- Bytes 10-11: {data[10:12].hex()}")
        print(f"- Byte 12: {hex(data[12])}")
        print(f"- Byte 13: {hex(data[13])}")
        print(f"- Byte 14: {hex(data[14])}")
        print(f"- Byte 15: {hex(data[15])}")
        
        # Try to find where the MIP table starts
        # Based on the format, we should check if there's a block size table
        # The original ftex_io.py had: BYTES_PER_BLOCK = {0xB: 16, ...}
        
        print(f"\nChecking for block size table at byte 20:")
        if len(data) >= 20:
            print(f"  Byte 20: {hex(data[20])}")
            print(f"  Byte 21: {hex(data[21])}")
            print(f"  Byte 22: {hex(data[22])}")
            print(f"  Byte 23: {hex(data[23])}")
            
            # Let's check what the bytes around the MIP table should be
            print(f"\nChecking potential MIP table location:")
            for i in range(32, min(32 + 4*12, len(data)), 4):
                offset = struct.unpack_from('<I', data, i)[0]
                print(f"  Offset at {i}: {hex(offset)} (size: {len(data) - offset if offset < len(data) else 'N/A'})")

if __name__ == "__main__":
    analyze_ftex("C:\\Program Files (x86)\\SP Football Life 2027\\SiderAddons\\livecpk\\ENG-Chelsea\\Asset\\model\\character\\parts\\manager\\sourceimages\\#windx11\\manager_bsm.ftex")