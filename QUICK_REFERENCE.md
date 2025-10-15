# Quick Reference Guide

## Command Cheat Sheet

### View Overall Configuration
```bash
uv run python main.py summary
```
Shows: Version, model, EQ type, bass settings, channel count

### List All Channels
```bash
uv run python main.py list-channels
```
Shows: Type, distance, trim, crossover, filter lengths for all 8 channels

### Inspect Single Channel
```bash
uv run python main.py inspect-filter <channel_number>
```
Shows: Detailed stats, first/last 20 coefficients, min/max/mean

Example: `uv run python main.py inspect-filter 0`

### View Filter in Chunks
```bash
uv run python main.py chunk-filter <channel> --start <index> --size <count>
```
Example: `uv run python main.py chunk-filter 0 --start 1000 --size 50`

### Export Filter to CSV
```bash
uv run python main.py export-filter <channel> <output.csv>
```
Example: `uv run python main.py export-filter 0 front_left.csv`

### Compare All Channels
```bash
uv run python main.py compare-channels
```
Shows: Side-by-side comparison table, grouping by filter length

---

## Filter Data Quick Facts

| Property | Value | Notes |
|----------|-------|-------|
| Filter Length (Surround) | 16,321 | Type "S" speakers |
| Filter Length (Effect) | 16,055 | Type "E" speakers |
| First Coefficient Range | 0.5 - 0.9 | Main gain/normalization |
| Other Coefficients | < 0.01 | Small corrections |
| Filter Type | Linear-phase FIR | High accuracy, some latency |

---

## Channel Number Reference

Based on your file (may vary by setup):

| Channel | Type | Distance | Trim | Crossover | Description |
|---------|------|----------|------|-----------|-------------|
| 0 | S | 2.75m | -1.5dB | 80 Hz | Surround |
| 1 | S | 2.74m | -2.0dB | 80 Hz | Surround |
| 2 | S | 2.49m | -6.0dB | 60 Hz | Surround |
| 3 | S | 2.46m | -6.0dB | 60 Hz | Surround |
| 4 | S | 4.28m | 0.0dB | 100 Hz | Surround |
| 5 | S | 4.28m | 0.0dB | 100 Hz | Surround |
| 6 | E | 3.55m | -0.5dB | N/A | Effect/Height |
| 7 | E | 4.65m | -3.0dB | N/A | Effect/Height |

---

## Common Analysis Workflows

### Workflow 1: Quick Overview
```bash
uv run python main.py summary
uv run python main.py compare-channels
```

### Workflow 2: Deep Dive on One Channel
```bash
uv run python main.py inspect-filter 0
uv run python main.py chunk-filter 0 --start 0 --size 100
uv run python main.py export-filter 0 analysis.csv
```

### Workflow 3: Export All Channels
```bash
for i in {0..7}; do
  uv run python main.py export-filter $i channel_${i}.csv
done
```

---

## File Structure at a Glance

```json
{
  "A1EvoExpress": "2",
  "model": "Marantz SR6012",
  "channels": [
    {
      "speakerType": "S",
      "distanceInMeters": 2.75,
      "trimAdjustmentInDbs": -1.5,
      "xover": 80,
      "filter": [0.720277..., -0.002282..., ...],  // 16,321 values
      "filterLV": [...]                             // Same length
    },
    // ... 7 more channels
  ]
}
```

---

## Key Insights

### What the Numbers Mean

**First coefficient (e.g., 0.72)**
- Main gain/normalization factor
- Typically 0.5 - 0.9
- Adjusts overall level

**Subsequent coefficients (e.g., -0.0022)**
- Small frequency corrections
- Room mode compensation
- Target curve shaping
- Most are < 0.01 in absolute value

**Last coefficients (e.g., -0.0000029)**
- Tail of impulse response
- Approach zero
- Minimal contribution to response

### Filter Length Explanation

- **16,321 taps** at 48kHz = ~340ms filter
- **16,055 taps** at 48kHz = ~334ms filter
- Covers direct sound + early/late reflections
- Linear-phase design = symmetrical response

---

## Safety Checklist

Before modifying filters:

- [ ] Backup original `.oca` file
- [ ] Export current filters for reference
- [ ] Understand filter length requirements
- [ ] Validate coefficient ranges
- [ ] Test at LOW volume first
- [ ] Modify ONE channel initially
- [ ] Compare before/after measurements

---

## Next Steps

1. **Understand current state**: Run `summary` and `compare-channels`
2. **Export for analysis**: Use `export-filter` on channels of interest
3. **Visualize in Excel/Python**: Plot frequency response
4. **Read full docs**: See [OCA_FORMAT.md](OCA_FORMAT.md) for details
5. **Plan modifications**: Design target curve in REW
6. **Create new filters**: Match length and validate ranges
7. **Test carefully**: Low volume, one channel at a time

---

## Troubleshooting

**Problem**: `Error: No .oca file found`
- **Solution**: Run command from directory containing `.oca` file

**Problem**: `Channel X not found`
- **Solution**: Valid range is 0-7 (for 8 channels)

**Problem**: Exported CSV won't open
- **Solution**: Check file path and permissions

**Problem**: Want to analyze frequency response
- **Solution**: Use exported CSV with FFT in Python/MATLAB/REW

---

## Python Analysis Snippet

```python
import json
import numpy as np

# Load OCA file
with open('A1EvoExpress_v2_Oct14_1933.oca', 'r') as f:
    data = json.load(f)

# Get filter from channel 0
coeffs = np.array(data['channels'][0]['filter'])

# Basic stats
print(f"Length: {len(coeffs)}")
print(f"Max: {coeffs.max():.6f}")
print(f"Mean: {coeffs.mean():.6f}")

# Frequency response (requires scipy)
from scipy.fft import fft
freq_response = fft(coeffs)
magnitude_db = 20*np.log10(np.abs(freq_response[:len(freq_response)//2]))
```

---

## Useful Resources

- **Full documentation**: [OCA_FORMAT.md](OCA_FORMAT.md)
- **Project overview**: [README.md](README.md)
- **Main tool**: [main.py](main.py)

---

*Last updated: October 2024*
