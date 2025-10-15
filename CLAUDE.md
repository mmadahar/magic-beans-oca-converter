# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python toolkit for analyzing and modifying Audyssey room calibration files (`.oca` format) from A1 Evo Express for Denon/Marantz AV receivers. The tools enable:

- Analyzing existing OCA calibration files
- Converting Magic Beans WAV filters to OCA format
- Converting REW correction files to FIR filters
- Performing FFT analysis to verify filter conversions

## Project Structure

```
oca_json/
├── src/                      # All Python source code
│   ├── main.py              # Workflow orchestrator (WAV → OCA → FFT)
│   ├── oca_file_analyzer.py # OCA file analyzer
│   ├── wav_to_oca.py        # WAV to OCA converter
│   ├── analyze_filter.py    # Filter analysis utilities
│   └── comprehensive_fft_analysis.py  # FFT analysis
├── docs/                     # All documentation
├── reports/                  # Generated analysis reports
├── input/                    # Input OCA files
├── mb/                       # Magic Beans source files
│   ├── convolution/         # WAV files (65,536 taps)
│   └── rew/                 # REW files (reference only)
└── output/                   # All generated outputs
    ├── filters/             # Converted JSON filters
    ├── data/                # CSV exports
    └── plots/               # Analysis plots
```

## Package Management

This project uses **`uv`** for all Python operations. Never use `pip` or `python` directly.

**All commands must be prefixed with `uv run`:**

```bash
# Correct
uv run python src/main.py

# Incorrect - Do NOT use
python src/main.py
pip install numpy
```

Dependencies are managed in `pyproject.toml`:
- `numpy>=1.24.0` - Array operations
- `scipy>=1.10.0` - Signal processing, WAV I/O, FFT
- `matplotlib>=3.7.0` - Plotting for FFT analysis

To sync dependencies after modifying `pyproject.toml`:
```bash
uv sync
```

## Core Architecture

### 1. OCA File Structure

OCA files are **JSON files** containing:
- Receiver metadata (model, version, amp assignment)
- Channel configuration (8 channels typical)
- **FIR filter coefficients** per channel:
  - `filter`: Array of 16,321 floats (Small speakers) or 16,055 floats (Large/Effect speakers)
  - `filterLV`: Low-volume variant for Audyssey Dynamic EQ

**Critical lengths:**
- Small speakers (type `S`): **16,321 taps** at 48kHz
- Large speakers (type `E`): **16,055 taps** at 48kHz

### 2. Time-Domain vs Frequency-Domain

**Key concept:** FIR filter coefficients are stored in **time domain** (impulse response), but their effect is understood in **frequency domain** (frequency response).

- **Time domain**: Array of 16K+ samples representing impulse response over ~340ms
- **Frequency domain**: FFT of time domain gives frequency response (magnitude/phase vs frequency)
- **Conversion**: Use `scipy.fft.fft()` to convert time → frequency

**Energy distribution:**
- 99%+ of filter energy is in first ~100-500 samples
- Remaining samples decay to near-zero
- This is why truncating 65K → 16K taps is safe

### 3. Tool Architecture

**Four main tools:**

#### A. Workflow Orchestrator (`src/main.py`) ⭐ PRIMARY TOOL
**Complete pipeline that runs everything automatically.**

Single command workflow:
1. Scans `mb/convolution/` for Magic Beans WAV files
2. Converts each WAV → OCA JSON filter (output/filters/)
3. Runs comprehensive FFT analysis
4. Generates detailed analysis report (reports/)

Usage:
```bash
uv run python src/main.py
```

This is the **recommended way** to process Magic Beans filters. It handles the entire workflow automatically.

#### B. OCA File Analyzer (`src/oca_file_analyzer.py`)
Single-file analyzer with `OCAAnalyzer` class. Operates directly on `.oca` files.

Commands:
- `summary` - High-level file overview
- `list-channels` - All channels with metadata
- `inspect-filter <N>` - Detailed filter stats for channel N
- `chunk-filter <N>` - Read filter in chunks (for large files)
- `export-filter <N> <file>` - Export to CSV
- `compare-channels` - Side-by-side channel comparison

Usage pattern:
```bash
uv run python src/oca_file_analyzer.py <command> [args]
```

#### C. WAV to OCA Converter (`src/wav_to_oca.py`)
Extracts FIR coefficients from Magic Beans WAV files (65,536 taps) and truncates to OCA length.

**Critical functions:**
- `load_wav_filter()` - Loads WAV, handles int16/int32/float32
- `check_truncation_safety()` - Validates truncation won't destroy filter
- `truncate_or_pad()` - Adjusts to target length with safety checks

Safety system:
- Analyzes active filter region
- Calculates energy loss percentage
- Blocks truncation if >1% energy would be lost
- `--force` flag overrides (use cautiously)

Usage:
```bash
# Preview filter
uv run python src/wav_to_oca.py "path/to/filter.wav" --preview

# Convert with target length
uv run python src/wav_to_oca.py "path/to/filter.wav" --target-length 16321 --output output.json

# Compare with existing OCA
uv run python src/wav_to_oca.py "path/to/filter.wav" --compare-oca file.oca --channel 0
```

**NOTE:** For batch conversion, use `src/main.py` instead which handles all channels automatically.

#### D. Comprehensive FFT Analysis (`src/comprehensive_fft_analysis.py`)
**Verification tool.** Performs both time-domain and frequency-domain analysis.

**Why this exists:** The earlier `batch_convert_and_analyze.py` had a bug where it compared truncated data to itself (always showing 0.000000 dB difference). This fixed version compares:
- Original 65K-tap WAV FFT (32,768 frequency bins)
- Truncated 16K-tap OCA FFT (8,160 frequency bins)
- Uses interpolation for fair comparison

**Output structure:**
```
output/
├── data/{channel}/
│   ├── original_coeffs_65536.csv
│   ├── truncated_coeffs_16321.csv
│   ├── discarded_coeffs_49215.csv
│   ├── original_fft_32768_bins.csv
│   ├── truncated_fft_8160_bins.csv
│   ├── fft_comparison.csv
│   └── metadata.json
├── plots/
│   ├── time_domain/
│   ├── frequency_domain/
│   └── energy_analysis/
└── DETAILED_ANALYSIS_REPORT.md
```

Usage:
```bash
uv run python src/comprehensive_fft_analysis.py
# No arguments - processes all WAV files in mb/convolution/
```

**NOTE:** This is automatically run by `src/main.py` as part of the workflow.

### 4. Channel Mapping

When converting Magic Beans files to OCA, use this mapping (hardcoded in `comprehensive_fft_analysis.py`):

| WAV File | OCA Channel | Type | Taps |
|----------|-------------|------|------|
| Filters for Front Left.wav | 0 | S | 16,321 |
| Filters for Front Right.wav | 1 | S | 16,321 |
| Filters for Surround Back Left.wav | 2 | S | 16,321 |
| Filters for Surround Back Right.wav | 3 | S | 16,321 |
| Filters for Front Height Left.wav | 6 | E | 16,055 |
| Filters for Front Height Right.wav | 7 | E | 16,055 |
| Filters for LFE.wav | - | S | 16,321 |

**Note:** Channels 4-5 may not have matching WAV files.

### 5. File Organization

```
mb/
├── convolution/          # Magic Beans WAV files (65,536 taps)
└── rew/                  # REW correction.txt files (frequency, dB pairs)

output/
├── filters/              # Converted OCA JSON filters
├── data/                 # Raw CSV exports for verification
├── plots/                # FFT analysis plots
├── fft/                  # Legacy plot structure
└── DETAILED_ANALYSIS_REPORT.md
```

## Common Tasks

### Full Workflow - Convert All Magic Beans Filters ⭐ RECOMMENDED

**Single command to do everything:**

```bash
uv run python src/main.py
```

This will:
1. Convert all WAV files in `mb/convolution/` to OCA JSON
2. Run comprehensive FFT analysis
3. Generate detailed report in `reports/`

### Analyze an Existing OCA File

```bash
# Quick overview
uv run python src/oca_file_analyzer.py summary

# See all channels
uv run python src/oca_file_analyzer.py compare-channels

# Deep dive on channel 0
uv run python src/oca_file_analyzer.py inspect-filter 0
```

### Convert Individual WAV Files (Advanced)

**If you need to convert a single file manually:**

1. **Preview and verify safety:**
```bash
uv run python src/wav_to_oca.py "mb/convolution/Filters for Front Left.wav" --preview
```

2. **Convert:**
```bash
uv run python src/wav_to_oca.py "mb/convolution/Filters for Front Left.wav" \
  --target-length 16321 \
  --output output/filters/ch0_front_left.json
```

**For most users, use `src/main.py` instead which handles everything automatically.**

### Run FFT Analysis Only (Advanced)

**If you already have converted filters and just want analysis:**

```bash
uv run python src/comprehensive_fft_analysis.py
```

This will:
1. Convert all WAV files in `mb/convolution/`
2. Export all intermediate data to `output/data/`
3. Generate 42 plots showing time/frequency analysis
4. Create `DETAILED_ANALYSIS_REPORT.md` with findings

**Key metrics to check in output:**
- `discarded_energy_percent` should be < 0.1%
- `max_difference_db` (FFT) should be < 1 dB
- High frequencies (12-20 kHz) should show < 0.01 dB difference

### Inject Filters into OCA File

**Manual process (Python):**

```python
import json

# Load OCA
with open('original.oca', 'r') as f:
    oca = json.load(f)

# Load converted filter
with open('output/filters/ch0_front_left.json', 'r') as f:
    new_filter = json.load(f)

# Replace channel 0 filter
oca['channels'][0]['filter'] = new_filter
oca['channels'][0]['filterLV'] = new_filter  # Or keep original filterLV

# Save modified OCA
with open('modified.oca', 'w') as f:
    json.dump(oca, f, indent=2)
```

## Phase Compatibility - CRITICAL INFORMATION

### Magic Beans vs Audyssey OCA: Phase Response Verification

**Question**: Are Magic Beans convolution filters compatible with Audyssey OCA minimum phase filters?

**Answer**: ✅ **YES - Both use minimum phase FIR filters**

#### Evidence:

**Magic Beans WAV Files** (verified via impulse response analysis):
- Peak coefficient at sample 0 (first sample)
- 100% of energy concentrated in first ~1000 samples
- Asymmetric impulse response
- Causal filter (all energy at start, not centered)
- **Conclusion**: Minimum phase FIR

**Audyssey OCA** (confirmed via technical documentation):
- Explicitly converts all speaker responses to minimum phase
- Inverts minimum phase response over target curve
- Uses minimum phase because "only minimum phase response is truly invertible"
- **Conclusion**: Minimum phase FIR

#### Why This Matters:

**Linear phase FIR filters** would cause:
- Pre-ringing artifacts (sound before the actual event)
- Excessive latency (delay required for symmetric response)
- Increased coefficient count (symmetric impulse requires more samples)
- Incompatibility with Audyssey's inversion algorithm

**Minimum phase FIR filters** provide:
- Causal response (no pre-ringing)
- Minimum group delay for given magnitude response
- Natural acoustic behavior (matches room acoustics)
- Directly invertible for room correction
- Efficient coefficient usage

#### Allpass Filters:

Allpass filters affect phase without changing magnitude response. They are not directly relevant to this WAV→OCA conversion because:
1. Both systems use minimum phase (phase is already minimized)
2. OCA filters contain magnitude correction only
3. Phase correction is handled by Audyssey's time alignment (cross-correlation)
4. Importing magnitude-only corrections does not introduce allpass issues

**Bottom Line**: The conversion is **technically sound**. Magic Beans minimum phase convolution filters are fully compatible with Audyssey OCA's minimum phase filter architecture.

## Critical Concepts

### FIR Filter Truncation

**Why 65K → 16K truncation works:**

1. Magic Beans exports 65,536-tap filters (1,365ms at 48kHz)
2. OCA accepts 16,321 taps (340ms at 48kHz)
3. Analysis shows 99.9% of energy in first ~100 samples
4. Samples 16,321-65,536 are nearly zero (< 0.000001 magnitude)

**High-frequency preservation:**
- 18 kHz has period of 2.67 samples at 48kHz
- 16,321 taps = 6,000+ complete 18kHz cycles
- High frequencies perfectly preserved (< 0.002 dB difference)
- Low frequencies show slightly more difference (0.01-0.1 dB) due to reduced resolution, but still excellent

### Frequency Resolution vs Range

- **Range** (which frequencies can be represented): Determined by sample rate (Nyquist theorem)
  - 48kHz → max 24kHz
- **Resolution** (how precisely you can adjust each frequency): Determined by filter length
  - 65K taps → 32,768 bins → 0.732 Hz/bin
  - 16K taps → 8,160 bins → 2.941 Hz/bin

Truncation reduces resolution (fewer bins) but preserves actual frequency response.

### Safety Checks

**Before importing filters to OCA:**

1. Verify filter length matches channel type (16,321 or 16,055)
2. Check for NaN/infinite values
3. First coefficient should be reasonable (0.5-1.5 range typical)
4. Review FFT analysis for differences > 1 dB
5. **Always backup original OCA file**
6. Test at low volume first

## Documentation Files

- **`README.md`**: User-facing overview and quick start
- **`OCA_FORMAT.md`**: Deep technical documentation on OCA structure
- **`MAGIC_BEANS_GUIDE.md`**: Complete guide to Magic Beans conversion
- **`REW_CONVERSION_GUIDE.md`**: REW frequency-domain to FIR conversion
- **`QUICK_REFERENCE.md`**: Command reference cheat sheet
- **`FINDINGS.md`**: Analysis results from filter safety verification

## Known Issues

### `batch_convert_and_analyze.py` Bug

**Do NOT use `batch_convert_and_analyze.py`** - it has a critical bug where it compares truncated data to itself:

```python
# Bug (lines 243-267)
converted_coeffs = original_coeffs[:target_length]  # Truncate
original_truncated = original_coeffs[:target_length]  # Same truncation!
diff_db = mag_conv_db - mag_orig_trunc_db  # Always 0!
```

**Use `comprehensive_fft_analysis.py` instead** - it properly compares:
- Full 65K original FFT vs truncated 16K FFT
- Exports all intermediate data for verification

## Sample Rate Assumption

**All tools assume 48,000 Hz sample rate.** This is hardcoded based on:
- OCA filter spec (16,321 taps @ 48kHz = 340ms)
- Magic Beans WAV files are 48kHz
- A1 Evo Express uses 48kHz for Audyssey

If you encounter files at different sample rates, the frequency resolution calculations will be incorrect.

## Testing Philosophy

**No automated tests.** This is an analysis/conversion toolkit where correctness is verified by:

1. **FFT analysis** - Visual inspection of frequency response plots
2. **Energy distribution** - Statistical validation that discarded samples contain negligible energy
3. **Manual verification** - Exporting CSV data for independent checking in Excel/MATLAB
4. **Incremental testing** - One channel at low volume before full system

The comprehensive FFT analysis script generates complete verification data automatically.
