# phase_shift_full_bridge_rectifier
# Phase-Shifted Full-Bridge DC-DC Converter (400 V to 13.5 V, 3 kW)

Design and SPICE verification of a phase-shifted full-bridge (PSFB) converter for a
400 VDC to 13.5 VDC, 3 kW rail. This is the same class of converter used as the
auxiliary DC-DC (LDC) in an electric vehicle, stepping the traction pack down to the
12 V system.

The design was sized by hand first, then verified in LTspice at 25%, 50% and 100%
load with real manufacturer device models rather than idealised switches.

## Design summary

| Parameter | Value |
|---|---|
| Switching frequency | 100 kHz |
| Transformer turns ratio | 22:1 |
| Leakage inductance | 4 µH |
| Output inductor | 0.4 µH |
| Output capacitance | ~1500 µF, low ESR |
| Dead time | 150 ns |
| Secondary rectifier | Full bridge, single secondary winding |
| Rated output current | 222 A |

## Results

The converter holds roughly 13.5 V across the full load range. Zero-voltage switching
is achieved on both bridge legs at 50% and 100% load, and lost on the lagging leg at
25% load, which is expected behaviour for this topology.

| | 25% load | 50% load | 100% load |
|---|---|---|---|
| Output power | 752 W | 1514 W | 2977 W |
| Output voltage | 13.52 V | 13.56 V | 13.45 V |
| Output ripple | 6.7 mV | 9.1 mV | 4.0 mV |
| Peak primary current | 3.53 A | 7.18 A | 12.73 A |
| RMS secondary current | 58.3 A | 116.1 A | 223.1 A |
| Leading leg ZVS | yes | yes | yes |
| Lagging leg ZVS | no | yes | yes |

## Two findings worth highlighting

**The ZVS threshold depends entirely on the real device capacitance.** Using the
Si7336ADP's actual 860 pF output capacitance, the charge-balance and resonant-energy
criteria bracket the ZVS threshold between 4.6 A and 8.3 A of primary current. The
simulation brackets it independently between 3.53 A and 7.18 A. Combining the two puts
the real threshold at 4.6 to 7.2 A, which places the practical soft-switching floor
near 40% load rather than 25%. An earlier version of this design assumed a generic
200 pF, which would have predicted comfortable ZVS at every load point and contradicted
the waveforms outright.

**The secondary needs about eight paralleled MOSFETs per rectifier position.** At
223 A RMS, a single Si7336ADP per position dissipates 358 W when hot and sits five
times over its current rating. Eight per position brings that to 45 W and 20 A per
device. That is 32 transistors on the secondary, and it drives PCB layout, gate drive
and cost far more than anything on the 400 V side.

Full semiconductor loss budget at rated load comes to 88 W, or about 97% efficiency.
That figure excludes magnetics, so it should be read as an upper bound.

## Known issue in the simulation schematic

The primary bridge in the LTspice schematic is populated with the Si7336ADP, a 30 V
part, sitting on a 400 V bus. SPICE simulates it without complaint because the standard
MOSFET model has no avalanche breakdown, so the simulated converter behaviour is valid,
but the part is a stand-in. A real build needs a 650 V superjunction device there. The
Si7336ADP is a sound choice on the secondary, where it blocks about 18.2 V.

## Repository layout

```
scripts/
  build_report.py   generates the design report as a .docx
  losses.py         ZVS threshold, paralleling study and full loss budget
figures/            LTspice waveform captures and the schematic (not yet added)
report/             generated report output (not yet added)
```

## Running the scripts

```bash
pip install python-docx
python scripts/losses.py          # prints the loss and ZVS analysis
python scripts/build_report.py    # builds the report, needs figures/ populated
```

`losses.py` runs standalone and needs no inputs. `build_report.py` expects the LTspice
captures in an `imgs/` directory relative to where it runs.

## References

Device data is from the [Vishay Si7336ADP datasheet](https://www.vishay.com/docs/73152/si7336adp.pdf)
(document 73152).
