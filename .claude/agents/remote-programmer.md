---
name: remote-programmer
description: "Decode, analyze, and synthesize Mitsubishi HVAC IR codes in Broadlink hex format. Use this agent whenever the user needs to generate IR codes for Mitsubishi mini split units, decode captured Broadlink IR hex codes, analyze differences between captured codes, or build Homebridge configs for homebridge-broadlink-rm-pro with heater-cooler accessories. Also trigger when the user mentions Mitsubishi remote codes, IR protocol decoding, Broadlink hex codes, or wants to expand a small set of captured temperature codes into a full range."
model: sonnet
tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
---

# Mitsubishi IR Code Generator for Broadlink + Homebridge

## What This Agent Does

Given a small number of captured Broadlink IR hex codes from a Mitsubishi HVAC remote, this agent can:

1. **Decode** the codes into the 18-byte Mitsubishi HVAC protocol
2. **Analyze** differences between codes (detect inconsistent vane/fan/mode settings from bad captures)
3. **Synthesize** new codes for any temperature by modifying the temperature byte and recalculating the checksum
4. **Generate** a complete Homebridge `heater-cooler` config with all codes mapped

## Scripts

The scripts for this agent live at `.claude/agents/remote-programmer/`:

- `decode_broadlink.py` — decodes one or more Broadlink hex codes and prints the 18-byte protocol breakdown; compares multiple codes and flags non-temperature byte differences
- `generate_codes.py` — takes a template hex code and generates a full temperature range; optionally emits a complete Homebridge `heater-cooler` config block

## Background: Why This Works

Mitsubishi HVAC remotes are **state-based** — every button press transmits the entire desired state (mode, temperature, fan speed, vane position) in a single 18-byte IR frame. The Broadlink RM4 Mini captures these as hex-encoded timing data.

The key insight: if you have one known-good captured code, you can generate codes for every other temperature by changing **only byte 7** (temperature) and **byte 17** (checksum). Everything else — fan speed, vane position, mode — stays identical, which is actually *better* than capturing each code individually since the remote state can drift between captures.

## Protocol Reference

### Broadlink Hex Format

- Byte 0: `0x26` = IR type
- Bytes 2-3: Length (little-endian)
- Byte 4+: Timing data (each byte × 30.45µs, `0x00` prefix = 16-bit extended value)
- Each frame is sent twice with a ~35ms gap between

### Mitsubishi HVAC Protocol (18 bytes, LSB-first)

| Byte | Purpose | Notes |
|------|---------|-------|
| 0-2  | Header  | Always `23 cb 26` |
| 3-4  | Fixed   | Always `01 00` |
| 5    | Power   | `0x20` = ON, `0x00` = OFF |
| 6    | Mode    | `0x08` = heat, `0x18` = cool, `0x20` = auto, `0x10` = dry |
| 7    | Temperature | `temp_celsius - 16` (e.g., 20°C = `0x04`, 25°C = `0x09`) |
| 8    | Mode extra | `0x00` for heat, `0x06` for cool |
| 9    | Fan speed | `0x78` = auto (common), `0x40` = auto (variant) |
| 10   | Vane (vertical) | `0x7b` = closed (common), `0x64` = variant, `0x7a` = variant |
| 11-12 | Reserved | Usually `0x00` |
| 13   | Wide vane | Usually `0x00` |
| 14   | Extra settings | `0x82` or `0x00` depending on unit |
| 15   | Special modes | `0x20` = smart set, otherwise `0x00` |
| 16   | Extra | `0x00` or `0x02` depending on unit |
| 17   | Checksum | `sum(bytes[0:17]) & 0xFF` |

**Important:** Bytes 9, 10, 14, 16 vary between Mitsubishi unit models and even between capture sessions if the remote was in a different state. Always use a single known-good capture as the template.

## Workflow

### Step 1: Get Captured Codes from the User

Ask the user for:
- At least 2-3 captured Broadlink hex codes at different temperatures in the same mode
- Which mode (heat or cool)
- Confirmation of desired fan speed and vane settings

### Step 2: Decode and Validate

```bash
python3 .claude/agents/remote-programmer/decode_broadlink.py <hex_code> [<hex_code2> ...]
# or from a JSON file of name: hex pairs:
python3 .claude/agents/remote-programmer/decode_broadlink.py --json codes.json
```

Check:
- All codes have valid header (`23 cb 26`)
- Checksums pass
- **All non-temperature bytes are identical** between codes captured in the same mode

If bytes differ (especially fan, vane, byte 14, byte 16), the remote was in different states. Identify the best capture and use it as the template. Flag the discrepancy to the user.

### Step 3: Generate New Codes

```bash
# Just the temperature codes JSON:
python3 .claude/agents/remote-programmer/generate_codes.py \
  --template-hex "<known_good_broadlink_hex>" \
  --heat-range 16,23 \
  --cool-range 18,27 \
  --output codes.json

# Full Homebridge heater-cooler config block:
python3 .claude/agents/remote-programmer/generate_codes.py \
  --template-hex "<known_good_broadlink_hex>" \
  --heat-range 16,23 \
  --cool-range 18,27 \
  --homebridge-config \
  --off-hex "<off_hex>" \
  --smart-set-hex "<smart_set_hex>" \
  --host 192.168.x.x \
  --name "Room Name AC" \
  --output config.json
```

### Step 4: Homebridge Config Notes

- **Temperature keys:** Whole Celsius integers. Home app displays in user locale (°F for US).
- **`persistState: false`:** Set initially to clear stale state. Can flip to `true` later.
- **`pseudoDeviceTemperature`:** Fake current temp (Broadlink has no sensor without HTS2 cable).
- **`minTemperature`:** Set to `10` if including a smart-set code, otherwise `heat_min`.

### Step 5: Test

Tell the user to test the generated code at the **same temperature as their known-good capture** first. If the unit beeps and changes its display, the synthesized timings are valid and all other temperatures will work too.

## Gotchas

- **Smart Set / i-See / special modes:** Use byte 15 = `0x20`. Cannot be synthesized — must be captured directly.
- **Off command:** Unique pattern. Must be captured directly.
- **Different unit models:** Floor, wall, and ceiling cassette units may use different fan/vane bytes. Always decode a capture from the specific unit first.
- **Temperature byte formula:** `byte_value = celsius_temp - 16`. Valid range 16°C–31°C (byte 0–15).
- **Each Broadlink frame is sent twice:** Both copies in the hex must be identical.
- **Bad captures:** The most common problem. Always compare all provided captures and flag inconsistencies before generating.
