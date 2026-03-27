#!/usr/bin/env python3
"""
Generate Mitsubishi HVAC IR codes in Broadlink hex format.

Takes a known-good captured Broadlink hex code as a template and generates
codes for a range of temperatures by modifying the temperature byte and
recalculating the checksum. All other state (fan, vane, mode extras) is
preserved from the template.

Usage:
    python3 generate_codes.py \
      --template-hex "<broadlink_hex>" \
      --heat-range 16,23 \
      --cool-range 18,27 \
      --output codes.json

    python3 generate_codes.py \
      --template-hex "<broadlink_hex>" \
      --heat-range 16,23 \
      --homebridge-config \
      --off-hex "<off_broadlink_hex>" \
      --smart-set-hex "<smart_set_hex>" \
      --host 192.168.86.38 \
      --name "Living Room AC" \
      --output config.json
"""

import argparse
import json
import sys

TICK = 30.45  # µs per Broadlink timing unit


# ---- Broadlink hex <-> timing conversion ----


def decode_broadlink_to_timings(hex_code):
    data = bytes.fromhex(hex_code)
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
    frames = []
    i = 0
    while i < len(timings) - 1:
        mark = timings[i]
        if mark > 2000:
            i += 2
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


def bits_to_bytes_lsb(bits):
    result = []
    for i in range(0, len(bits), 8):
        byte_bits = bits[i : i + 8]
        if len(byte_bits) == 8:
            result.append(sum(b << j for j, b in enumerate(byte_bits)))
    return result


def bytes_to_bits_lsb(byte_list):
    bits = []
    for b in byte_list:
        for j in range(8):
            bits.append((b >> j) & 1)
    return bits


def bits_to_broadlink_timings(
    bits,
    header_mark=3400,
    header_space=1750,
    bit_mark=430,
    zero_space=430,
    one_space=1300,
    trail_mark=430,
):
    timings = [header_mark, header_space]
    for b in bits:
        timings.append(bit_mark)
        timings.append(one_space if b else zero_space)
    timings.append(trail_mark)
    return timings


def timings_to_broadlink_hex(frame1_timings, frame2_timings, gap_us=35000):
    all_timings = frame1_timings + [gap_us] + frame2_timings
    ir_bytes = []
    for t in all_timings:
        units = round(t / TICK)
        if units > 255:
            ir_bytes.append(0x00)
            ir_bytes.append((units >> 8) & 0xFF)
            ir_bytes.append(units & 0xFF)
        else:
            ir_bytes.append(max(1, units))
    ir_bytes.extend([0x0D, 0x05])
    while len(ir_bytes) % 2 != 0:
        ir_bytes.append(0x00)
    ir_bytes.extend([0x00] * 10)
    length = len(ir_bytes)
    packet = [0x26, 0x00, length & 0xFF, (length >> 8) & 0xFF] + ir_bytes
    return "".join(f"{b:02x}" for b in packet)


# ---- Mitsubishi protocol helpers ----


def extract_template(hex_code):
    """Extract the 18-byte Mitsubishi protocol frame from a Broadlink hex code."""
    timings = decode_broadlink_to_timings(hex_code)
    frames = timings_to_frames(timings)
    if not frames:
        print(
            "ERROR: Could not decode any frames from the template hex", file=sys.stderr
        )
        sys.exit(1)
    byte_data = bits_to_bytes_lsb(frames[0])
    if len(byte_data) < 18 or byte_data[0] != 0x23 or byte_data[1] != 0xCB:
        print(
            "ERROR: Decoded frame is not a valid Mitsubishi HVAC packet",
            file=sys.stderr,
        )
        sys.exit(1)
    return byte_data[:18]


def generate_code(template_bytes, temp_celsius, mode="heat"):
    """Generate a new 18-byte frame by setting temperature, mode, and checksum."""
    new_bytes = list(template_bytes)

    if mode == "heat":
        new_bytes[6] = 0x08
        new_bytes[8] = 0x00
    elif mode == "cool":
        new_bytes[6] = 0x18
        new_bytes[8] = 0x06
    elif mode == "auto":
        new_bytes[6] = 0x20
        new_bytes[8] = 0x00

    new_bytes[7] = temp_celsius - 16
    new_bytes[17] = sum(new_bytes[:17]) & 0xFF
    return new_bytes


def protocol_bytes_to_broadlink(byte_data):
    """Convert 18 protocol bytes into a full Broadlink hex string."""
    bits = bytes_to_bits_lsb(byte_data)
    bits.append(0)  # trailing stop bit
    frame_timings = bits_to_broadlink_timings(bits)
    return timings_to_broadlink_hex(frame_timings, frame_timings)


# ---- Main ----


def main():
    parser = argparse.ArgumentParser(
        description="Generate Mitsubishi HVAC IR codes in Broadlink hex format"
    )
    parser.add_argument(
        "--template-hex",
        required=True,
        help="Known-good Broadlink hex code to use as template",
    )
    parser.add_argument(
        "--heat-range",
        default="16,23",
        help="Celsius range for heat codes, e.g. 16,23 (default: 16,23)",
    )
    parser.add_argument(
        "--cool-range",
        default="18,27",
        help="Celsius range for cool codes, e.g. 18,27 (default: 18,27)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="codes.json",
        help="Output JSON file (default: codes.json)",
    )

    # Homebridge config generation
    parser.add_argument(
        "--homebridge-config",
        action="store_true",
        help="Generate a full homebridge heater-cooler config block",
    )
    parser.add_argument("--off-hex", help="Broadlink hex for the OFF command")
    parser.add_argument(
        "--smart-set-hex", help="Broadlink hex for smart set (50°F/10°C)"
    )
    parser.add_argument("--host", help="Broadlink device IP for Homebridge config")
    parser.add_argument(
        "--name", default="AC", help="Accessory name for Homebridge config"
    )

    args = parser.parse_args()

    # Extract template
    template = extract_template(args.template_hex)
    print(f"Template bytes: {' '.join(f'{b:02x}' for b in template)}")
    print(
        f"Template mode:  {'HEAT' if template[6] == 0x08 else 'COOL' if template[6] == 0x18 else 'AUTO'}"
    )
    print(
        f"Template temp:  {template[7] + 16}°C / {(template[7] + 16) * 9 / 5 + 32:.0f}°F"
    )
    print(f"Template fan:   0x{template[9]:02x}")
    print(f"Template vane:  0x{template[10]:02x}")
    print()

    # Parse ranges
    heat_min, heat_max = (int(x) for x in args.heat_range.split(","))
    cool_min, cool_max = (int(x) for x in args.cool_range.split(","))

    # Generate codes
    heat_codes = {}
    cool_codes = {}

    for temp_c in range(heat_min, heat_max + 1):
        new_bytes = generate_code(template, temp_c, mode="heat")
        hex_code = protocol_bytes_to_broadlink(new_bytes)
        heat_codes[str(temp_c)] = hex_code
        print(
            f"Heat {temp_c}°C ({temp_c * 9 / 5 + 32:.0f}°F): "
            f"bytes[7]=0x{new_bytes[7]:02x} checksum=0x{new_bytes[17]:02x} ✓"
        )

    print()
    for temp_c in range(cool_min, cool_max + 1):
        new_bytes = generate_code(template, temp_c, mode="cool")
        hex_code = protocol_bytes_to_broadlink(new_bytes)
        cool_codes[str(temp_c)] = hex_code
        print(
            f"Cool {temp_c}°C ({temp_c * 9 / 5 + 32:.0f}°F): "
            f"bytes[7]=0x{new_bytes[7]:02x} checksum=0x{new_bytes[17]:02x} ✓"
        )

    # Output
    if args.homebridge_config:
        # Add smart set as 10°C entry
        if args.smart_set_hex:
            heat_codes["10"] = args.smart_set_hex

        off_hex = args.off_hex or ""
        default_heat_key = str((heat_min + heat_max) // 2)
        default_cool_key = str((cool_min + cool_max) // 2)

        config = {
            "name": args.name,
            "type": "heater-cooler",
            "persistState": False,
            "pseudoDeviceTemperature": 20,
            "minTemperature": 10 if args.smart_set_hex else heat_min,
            "maxTemperature": cool_max,
            "heatingThresholdTemperature": int(default_heat_key),
            "coolingThresholdTemperature": int(default_cool_key),
            "data": {
                "off": off_hex,
                "heat": {
                    "on": heat_codes.get(default_heat_key, ""),
                    "off": off_hex,
                    "temperatureCodes": heat_codes,
                },
                "cool": {
                    "on": cool_codes.get(default_cool_key, ""),
                    "off": off_hex,
                    "temperatureCodes": cool_codes,
                },
            },
        }
        if args.host:
            config["host"] = args.host

        with open(args.output, "w") as f:
            json.dump(config, f, indent=4)
    else:
        output = {
            "heat_temperatureCodes": heat_codes,
            "cool_temperatureCodes": cool_codes,
        }
        with open(args.output, "w") as f:
            json.dump(output, f, indent=4)

    print(f"\nWritten to {args.output}")
    print(f"  Heat: {len(heat_codes)} codes ({heat_min}-{heat_max}°C)")
    print(f"  Cool: {len(cool_codes)} codes ({cool_min}-{cool_max}°C)")


if __name__ == "__main__":
    main()
