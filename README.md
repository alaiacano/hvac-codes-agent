This is a claude code agent that is able to decipher and produce Mitsubishi mini split IR remote programming codes. It uses the sonnet model which should be sufficient.

This is useful for configuring the [Homebridge Broadlink RM](https://github.com/lprhodes/homebridge-broadlink-rm) plugin for Homebridge, allowing you to control your split units with HomeKit. 

I won't summarize the full setup yet, but it's roughly:

```
iPhone (Home app) -> Homebridge -> BroadLink RM4 Mini IR Universal Remote Control -> Mitsubishi Split Unit
```

I've only tested it with thie `12,000 BTU Mitsubishi M-Series 17.2 SEER2 Single Zone Floor Mount Mini Split Heat Pump System - R454B | SUZ-AA12NL / MFZ-KX12NL` units.

Example interaction:

```
> can you decode this mitsubishi hex code for me? use the remote-programmer agent. 26005a0270390e2b0e2b0e0e0e0e0e0e0e2b0e0e0e0e0e2b0e2b0e0e0e2b0e0e 
0e0e0e2b0e2b0e0e0e2b0e2b0e0e0e0e0e2b0e0e0e0e0e2b0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e2b0e0e0e0e0e0e0e0 
e0e0e0e2b0e0e0e0e0e0e0e0e0e0e0e0e0e2b0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e2b0e2b0e2b0e2b0e0e0e2b0e2b0e0e0e2b0e2b0e2b0e 
2b0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e2b0e0e0e0e0e0e0e0e0e0e0e2b0e0e0e0e0e0e0 
e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e2b0e2b0e0e0e2b0e2b0e0e0e2b0e0e0e00047d70390e2b0e2b0e0e0e0e0e0e0e2b0e0e0e0e0e2b0e2b0e0e0e2b 
0e0e0e0e0e2b0e2b0e0e0e2b0e2b0e0e0e0e0e2b0e0e0e0e0e2b0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e2b0e0e0e0e0e0 
e0e0e0e0e0e2b0e0e0e0e0e0e0e0e0e0e0e0e0e2b0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e2b0e2b0e2b0e2b0e0e0e2b0e2b0e0e0e2b0e2b0e 
2b0e2b0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e2b0e0e0e0e0e0e0e0e0e0e0e2b0e0e0e0e0 
e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e2b0e2b0e0e0e2b0e2b0e0e0e2b0e0e0e0d050000000000000000000000                             

⏺ remote-programmer(Decode Mitsubishi IR hex code)
  ⎿  Done (1 tool use · 11.2k tokens · 32s)
  (ctrl+o to expand)

⏺ Here's what the decoded code represents:

  ┌────────────────────────┬────────────────┐
  │        Setting         │     Value      │
  ├────────────────────────┼────────────────┤
  │ Power                  │ ON             │
  ├────────────────────────┼────────────────┤
  │ Mode                   │ Heat           │
  ├────────────────────────┼────────────────┤
  │ Temperature            │ 20°C (68°F)    │
  ├────────────────────────┼────────────────┤
  │ Fan Speed              │ Auto           │
  ├────────────────────────┼────────────────┤
  │ Vane (vertical)        │ Closed/fixed   │
  ├────────────────────────┼────────────────┤
  │ Wide Vane (horizontal) │ Default/center │
  └────────────────────────┴────────────────┘

  The frame was transmitted twice (standard for Mitsubishi IR) and both copies match — it's a clean capture.
```

You can also ask it to produce a full Homebridge Broadlink configuration file, given a small number of codes. See the Homebridge Broadlink plugin docs for details on how to do that.