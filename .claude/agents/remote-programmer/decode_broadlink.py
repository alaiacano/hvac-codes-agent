#!/usr/bin/env python3
"""
Decode Broadlink IR hex codes into Mitsubishi HVAC protocol bytes.

Usage:
    python3 decode_broadlink.py <hex_code> [<hex_code2> ...]
    python3 decode_broadlink.py --json <json_file>

The --json option reads a JSON file with key-value pairs of name: hex_code.
"""

import sys
import json
import argparse

TICK = 30.45  # µs per Broadlink timing unit


def decode_broadlink_to_timings(hex_code):
    """Decode Broadlink hex string to list of timing values in µs."""
    data = bytes.fromhex(hex_code)
    if data[0] != 0x26:
        print(
            f"  Warning: byte 0 = 0x{data[0]:02x}, expected 0x26 (IR)", file=sys.stderr
        )
    ir_data = data[4:]
    timings = []
    i = 0
    while i < len(ir_data):
        if ir_data[i] == 0x00:
            if i + 2 < len(ir_data):
                val = (ir_data[i + 1] << 8) | ir_data[i + 2]
                timings.append(val * TICK)
                i += 3
            else:
                break
        else:
            timings.append(ir_data[i] * TICK)
            i += 1
    return timings


def timings_to_frames(timings):
    """Extract bit frames from IR timings using Mitsubishi protocol thresholds."""
    frames = []
    i = 0
    while i < len(timings) - 1:
        mark = timings[i]
        if mark > 2000:  # Header mark (~3400µs)
            i += 2  # Skip header mark + space
            frame_bits = []
            while i < len(timings) - 1:
                mark = timings[i]
                space = timings[i + 1] if i + 1 < len(timings) else 0
                if mark > 2000 or space > 20000:
                    break
                frame_bits.append(1 if space > 800 else 0)
                i += 2
            if frame_bits:
                frames.append(frame_bits)
        else:
            i += 1
    return frames


def bits_to_bytes(bits):
    """Convert bit list to bytes (LSB first, as Mitsubishi uses)."""
    result = []
    for i in range(0, len(bits), 8):
        byte_bits = bits[i : i + 8]
        if len(byte_bits) == 8:
            result.append(sum(b << j for j, b in enumerate(byte_bits)))
    return result


def decode_mitsubishi_frame(byte_data):
    """Decode an 18-byte Mitsubishi HVAC frame into human-readable fields."""
    if len(byte_data) < 18:
        return None
    if byte_data[0] != 0x23 or byte_data[1] != 0xCB or byte_data[2] != 0x26:
        return None

    mode_map = {0x08: "HEAT", 0x18: "COOL", 0x20: "AUTO", 0x10: "DRY", 0x28: "FAN"}

    power = bool(byte_data[5] & 0x20)
    mode_byte = byte_data[6]
    mode = mode_map.get(mode_byte, f"UNKNOWN(0x{mode_byte:02x})")
    temp_c = (byte_data[7]) + 16
    checksum_calc = sum(byte_data[:17]) & 0xFF
    checksum_ok = checksum_calc == byte_data[17]

    return {
        "bytes_hex": " ".join(f"{b:02x}" for b in byte_data),
        "power": "ON" if power else "OFF",
        "mode": mode,
        "mode_byte": f"0x{mode_byte:02x}",
        "temp_c": temp_c,
        "temp_f": round(temp_c * 9 / 5 + 32, 1),
        "temp_byte": f"0x{byte_data[7]:02x}",
        "mode_extra": f"0x{byte_data[8]:02x}",
        "fan": f"0x{byte_data[9]:02x}",
        "vane_vert": f"0x{byte_data[10]:02x}",
        "byte11": f"0x{byte_data[11]:02x}",
        "byte12": f"0x{byte_data[12]:02x}",
        "wide_vane": f"0x{byte_data[13]:02x}",
        "byte14": f"0x{byte_data[14]:02x}",
        "byte15": f"0x{byte_data[15]:02x}",
        "byte16": f"0x{byte_data[16]:02x}",
        "checksum": f"0x{byte_data[17]:02x}",
        "checksum_calc": f"0x{checksum_calc:02x}",
        "checksum_ok": checksum_ok,
        "raw_bytes": list(byte_data),
    }


def decode_broadlink_hex(hex_code):
    """Full pipeline: Broadlink hex -> Mitsubishi HVAC protocol decode."""
    timings = decode_broadlink_to_timings(hex_code)
    frames = timings_to_frames(timings)
    results = []
    for frame in frames:
        byte_data = bits_to_bytes(frame)
        decoded = decode_mitsubishi_frame(byte_data)
        if decoded:
            results.append(decoded)
    return results


def print_decoded(name, decoded):
    """Pretty-print a decoded frame."""
    print(f"\n{'=' * 60}")
    print(f"  {name}")
    print(f"{'=' * 60}")
    d = decoded
    print(f"  Bytes:     {d['bytes_hex']}")
    print(f"  Power:     {d['power']}")
    print(f"  Mode:      {d['mode']} ({d['mode_byte']})")
    print(f"  Temp:      {d['temp_c']}°C / {d['temp_f']}°F (byte={d['temp_byte']})")
    print(f"  Mode ext:  {d['mode_extra']}")
    print(f"  Fan:       {d['fan']}")
    print(f"  Vane:      {d['vane_vert']}")
    print(f"  Wide vane: {d['wide_vane']}")
    print(f"  Byte14:    {d['byte14']}")
    print(f"  Byte15:    {d['byte15']}")
    print(f"  Byte16:    {d['byte16']}")
    cs_status = "✓" if d["checksum_ok"] else f"✗ expected {d['checksum_calc']}"
    print(f"  Checksum:  {d['checksum']} {cs_status}")


def compare_codes(decoded_list):
    """Compare multiple decoded frames and flag differences."""
    if len(decoded_list) < 2:
        return
    print(f"\n{'=' * 60}")
    print("  COMPARISON — fields that differ between codes")
    print(f"{'=' * 60}")
    fields = [
        "fan",
        "vane_vert",
        "mode_extra",
        "wide_vane",
        "byte14",
        "byte15",
        "byte16",
    ]
    reference = decoded_list[0]
    has_diff = False
    for field in fields:
        vals = set(d[1][field] for d in decoded_list)
        if len(vals) > 1:
            has_diff = True
            print(f"\n  ⚠ {field} differs:")
            for name, d in decoded_list:
                print(f"    {name:30s} -> {d[field]}")
    if not has_diff:
        print("\n  ✓ All non-temperature bytes are consistent across codes")


def main():
    parser = argparse.ArgumentParser(
        description="Decode Broadlink IR hex codes (Mitsubishi HVAC)"
    )
    parser.add_argument("hex_codes", nargs="*", help="Broadlink hex code strings")
    parser.add_argument("--json", "-j", help="JSON file with name: hex_code pairs")
    args = parser.parse_args()

    codes = {}
    if args.json:
        with open(args.json) as f:
            codes = json.load(f)
    elif args.hex_codes:
        for i, hc in enumerate(args.hex_codes):
            codes[f"code_{i}"] = hc
    else:
        parser.print_help()
        sys.exit(1)

    all_decoded = []
    for name, hex_code in codes.items():
        results = decode_broadlink_hex(hex_code)
        if results:
            print_decoded(name, results[0])
            all_decoded.append((name, results[0]))
        else:
            print(f"\n  {name}: Failed to decode (not a valid Mitsubishi HVAC frame)")

    if len(all_decoded) > 1:
        compare_codes(all_decoded)


if __name__ == "__main__":
    main()
