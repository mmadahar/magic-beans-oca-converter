# OCA JSON Toolkit

A comprehensive Python toolkit for analyzing Audyssey `.oca` calibration files and converting Magic Beans FIR filters for Denon/Marantz AV receivers.

## What is This?

This toolkit helps you work with A1 Evo Express `.oca` files, including:

- 🔄 **Convert** Magic Beans WAV filters to OCA format (65K → 16K taps)
- 📊 **Analyze** FIR filter coefficients and frequency response
- 🔍 **Inspect** OCA calibration data and channel configurations
- ✅ **Verify** filter quality with comprehensive FFT analysis
- 📈 **Export** data for external analysis (CSV, plots, reports)

## Quick Start

### Installation

This project uses `uv` for Python environment management:

```bash
# Clone or navigate to the project
cd oca_json

# uv will automatically create a virtual environment and install dependencies
uv sync
```

### Convert Magic Beans Filters (Recommended)

**Single command to do everything:**

```bash
uv run python src/main.py
```

This will:
1. Convert all Magic Beans WAV files in `mb/convolution/` to OCA JSON format
2. Run comprehensive FFT analysis (time-domain + frequency-domain)
3. Generate detailed analysis report with plots in `reports/`

### Analyze Existing OCA Files

```bash
# View overall configuration
uv run python src/oca_file_analyzer.py summary

# List all channels with their properties
uv run python src/oca_file_analyzer.py list-channels

# Inspect a specific channel's filter in detail
uv run python src/oca_file_analyzer.py inspect-filter 0

# Compare filters across all channels
uv run python src/oca_file_analyzer.py compare-channels

# Export filter to CSV for analysis
uv run python src/oca_file_analyzer.py export-filter 0 channel_0.csv
```

### Verify Minimum Phase (Optional)

Verify that filters are minimum phase (required for Audyssey OCA compatibility):

```bash
uv run python src/verify_minimum_phase.py mb/convolution/"Filters for Front Left.wav"
```

## Project Structure

```
oca_json/
├── src/                              # All Python source code
│   ├── main.py                       # Workflow orchestrator (WAV → OCA → FFT)
│   ├── oca_file_analyzer.py          # OCA file analyzer
│   ├── wav_to_oca.py                 # WAV converter
│   ├── verify_minimum_phase.py       # Phase verification tool
│   └── comprehensive_fft_analysis.py # FFT analysis
├── docs/                             # All documentation
│   ├── README.md                     # This file
│   ├── OCA_FORMAT.md                 # Technical OCA specification
│   ├── MAGIC_BEANS_GUIDE.md          # Magic Beans conversion guide
│   ├── MINIMUM_PHASE_VERIFICATION.md # Phase compatibility explained
│   └── QUICK_REFERENCE.md            # Command cheat sheet
├── reports/                          # Generated analysis reports
├── input/                            # Input OCA files
├── mb/                               # Magic Beans source files
│   ├── convolution/                  # WAV filters (65,536 taps)
│   └── rew/                          # REW files (reference)
└── output/                           # All generated outputs
    ├── filters/                      # Converted JSON filters
    ├── data/                         # CSV data exports
    └── plots/                        # Analysis plots
```

## What's Inside an OCA File?

An `.oca` file contains:

- **Receiver configuration**: Model, EQ type, amp assignments
- **Speaker setup**: 8 channels with distances, trim levels, crossovers
- **FIR filters**: ~16,000 coefficients per channel for room correction
- **Dual filter sets**: Main filter + low-volume variant (Dynamic EQ)

### Example Output

```
======================================================================
OCA FILE SUMMARY
======================================================================

A1 Evo Express Version: 2
Receiver Model: Marantz SR6012
EQ Type: 2
Total Channels: 8

Number of Subwoofers: 2
LPF for LFE: 120
Bass Mode: LFE
======================================================================
```

## Understanding the Filters

Each channel has a **16,321-coefficient FIR filter** (or 16,055 for effect speakers). These represent:

- **Minimum phase FIR filters** for room correction
- **Time-domain impulse response** of your calibrated system
- **Frequency response shaping** to target curve
- **Invertible corrections** (unique to minimum phase)

### Why Minimum Phase Matters

Audyssey OCA requires **minimum phase filters** because:

- Only minimum phase responses can be inverted while remaining causal and stable
- Natural room acoustics are minimum phase
- No pre-ringing artifacts (sound before actual event)
- Minimum group delay for given magnitude response

**Magic Beans filters are minimum phase** (verified by mathematical proof), making them fully compatible with Audyssey OCA. See [MINIMUM_PHASE_VERIFICATION.md](MINIMUM_PHASE_VERIFICATION.md) for details.

## Magic Beans Conversion

### Why Truncation is Safe

Magic Beans exports 65,536-tap filters (1,365ms at 48kHz). OCA accepts 16,321 taps (340ms at 48kHz).

Analysis shows:
- 99.99% of energy in first 1,000 samples
- Samples 16,321-65,536 are essentially zero
- High frequencies (18 kHz) perfectly preserved (< 0.002 dB difference)
- Low frequencies show minimal difference (0.01-0.1 dB)

**Truncation removes only the silent tail** with negligible impact on frequency response.

### Conversion Workflow

The `src/main.py` script:

1. **Scans** `mb/convolution/` for WAV files
2. **Validates** truncation safety (energy loss < 0.1%)
3. **Truncates** to target length (16,321 or 16,055 taps)
4. **Saves** to `output/filters/` as JSON
5. **Performs** FFT analysis comparing 65K original vs 16K truncated
6. **Generates** comprehensive report with 42 plots
7. **Exports** all data to CSV for independent verification

## Channel Mapping

When converting Magic Beans files to OCA:

| WAV File | OCA Channel | Type | Taps |
|----------|-------------|------|------|
| Filters for Front Left.wav | 0 | S | 16,321 |
| Filters for Front Right.wav | 1 | S | 16,321 |
| Filters for Surround Back Left.wav | 2 | S | 16,321 |
| Filters for Surround Back Right.wav | 3 | S | 16,321 |
| Filters for Front Height Left.wav | 6 | E | 16,055 |
| Filters for Front Height Right.wav | 7 | E | 16,055 |
| Filters for LFE.wav | - | S | 16,321 |

**Types:**
- **S** (Surround): 16,321 taps for small speakers
- **E** (Effect): 16,055 taps for large/height speakers

## Safety Checklist

Before importing filters to OCA:

- [ ] **Backup** original `.oca` file
- [ ] **Verify** filter length matches channel type (16,321 or 16,055)
- [ ] **Check** for NaN/infinite values (none should exist)
- [ ] **Review** FFT analysis for differences > 1 dB
- [ ] **Read** `reports/DETAILED_ANALYSIS_REPORT.md`
- [ ] **Test** at LOW volume first
- [ ] **Modify** ONE channel initially
- [ ] **Compare** before/after measurements

## Importing Filters to OCA

**Manual process (Python):**

```python
import json

# Load original OCA file
with open('input/original.oca', 'r') as f:
    oca = json.load(f)

# Load converted filter
with open('output/filters/ch0_front_left.json', 'r') as f:
    new_filter = json.load(f)

# Replace channel 0 filter
oca['channels'][0]['filter'] = new_filter
oca['channels'][0]['filterLV'] = new_filter  # Or keep original filterLV

# Save modified OCA
with open('output/modified.oca', 'w') as f:
    json.dump(oca, f, indent=2)
```

## Documentation

### Comprehensive Guides

- **[OCA_FORMAT.md](OCA_FORMAT.md)** - Deep technical documentation on OCA file structure
- **[MAGIC_BEANS_GUIDE.md](MAGIC_BEANS_GUIDE.md)** - Complete guide to Magic Beans conversion
- **[MINIMUM_PHASE_VERIFICATION.md](MINIMUM_PHASE_VERIFICATION.md)** - Phase compatibility explained with mathematical proofs
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Command reference cheat sheet

### Analysis Reports

After running `src/main.py`, check:

- **reports/DETAILED_ANALYSIS_REPORT.md** - Comprehensive FFT analysis with metrics for each channel
- **output/plots/** - 42 plots showing time-domain, frequency-domain, and energy analysis
- **output/data/** - CSV exports of all coefficients and FFT data for verification

## Troubleshooting

### Problem: "No .oca file found"
**Solution**: Run command from directory containing `.oca` file or specify path

### Problem: "WAV file not found"
**Solution**: Ensure Magic Beans WAV files are in `mb/convolution/` directory

### Problem: "Truncation may not be safe"
**Solution**: Review energy metrics - if >1% energy would be lost, investigate WAV file. Magic Beans files should show <0.0001% energy loss.

### Problem: Want to verify phase compatibility
**Solution**: Run `uv run python src/verify_minimum_phase.py <wav_file>` - all tests should confirm minimum phase

## Technical Details

### Sample Rate

All tools assume **48,000 Hz sample rate**, which is standard for:
- OCA filter specification (16,321 taps @ 48kHz = 340ms)
- Magic Beans WAV exports
- A1 Evo Express processing

### Filter Resolution

- **65K taps**: 32,768 frequency bins (0.732 Hz/bin)
- **16K taps**: 8,160 frequency bins (2.941 Hz/bin)

Truncation reduces frequency resolution but preserves actual frequency response.

### Energy Distribution

Typical Magic Beans filter:
- **50%** of energy: Sample 0 (first sample!)
- **99%** of energy: First 6-13 samples
- **99.9%** of energy: First 87-275 samples
- **99.99%** of energy: First 723-1,707 samples

This extreme concentration is characteristic of minimum phase filters and why truncation is safe.

## Next Steps

1. **Run conversion**: `uv run python src/main.py`
2. **Review report**: `reports/DETAILED_ANALYSIS_REPORT.md`
3. **Backup OCA**: Copy original `.oca` file
4. **Import filters**: Use Python script above to inject filters
5. **Test carefully**: Low volume, one channel at a time
6. **Measure results**: Use REW to verify frequency response

## Contributing

This is a personal toolkit project, but suggestions and improvements are welcome via issues.

## License

This project is for personal use. Audyssey, MultEQ, Denon, and Marantz are trademarks of their respective owners.

---

*Last updated: October 2024*
