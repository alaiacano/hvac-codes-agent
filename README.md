# Mitsubishi Mini-Split IR Codes for Homebridge + Broadlink

This repo contains a [Claude Code](https://claude.ai/code) agent that generates and decodes Mitsubishi mini-split IR codes in Broadlink hex format, for use with the [homebridge-broadlink-rm-pro](https://github.com/kiwi-cam/homebridge-broadlink-rm) plugin.

The overall control chain looks like this:

```
iPhone (Home app) → Homebridge → Broadlink RM4 Mini → Mitsubishi split unit
```

---

## What the Agent Does

The `remote-programmer` agent can:

- **Decode** a captured Broadlink hex code and tell you the mode, temperature, fan speed, and vane settings
- **Validate** captures and flag inconsistencies between them
- **Synthesize** codes for every temperature in a range from a single good capture
- **Generate** a complete `heater-cooler` config block for homebridge-broadlink-rm-pro

All you need to get started is one or two captured IR codes from your remote (one per mode: heat and cool). The agent handles the rest.

---

## Getting Started

1. Install [Claude Code](https://claude.ai/code)
2. Clone this repo and open it in Claude Code
3. Capture a raw IR code from your Mitsubishi remote using the [Broadlink app](https://www.ibroadlink.com/app/) or [`python-broadlink`](https://github.com/mjg59/python-broadlink)
4. Paste the hex code into Claude Code and ask the agent to decode it or generate a full config:

```
> use the remote-programmer agent to decode this code: 26005a0270390e2b...

> use the remote-programmer agent to generate a full homebridge heater-cooler
  config from this heat code and this cool code: ...
```

The agent will ask for anything else it needs (temperature ranges, Broadlink device IP, accessory name, etc.).

---

## What's in This Repo

- `.claude/agents/remote-programmer.md` — the agent definition and protocol reference
- `.claude/agents/remote-programmer/decode_broadlink.py` — script the agent uses to decode captures
- `.claude/agents/remote-programmer/generate_codes.py` — script the agent uses to synthesize codes and emit Homebridge config
- `codes/` — example generated configs for Mitsubishi floor-mount units (`MFZ-KX12NL`)

---

## Resources

- [homebridge-broadlink-rm-pro](https://github.com/kiwi-cam/homebridge-broadlink-rm) — Homebridge plugin
- [python-broadlink](https://github.com/mjg59/python-broadlink) — capture IR codes from a Broadlink device
- [Homebridge](https://homebridge.io/) — HomeKit bridge for non-HomeKit accessories
