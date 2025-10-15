# REW to OCA Conversion Guide

## Overview

This guide explains how to convert Room EQ Wizard (REW) correction curves into FIR filter coefficients compatible with Audyssey OCA files, allowing you to upload custom target curves to your Denon/Marantz receiver.

## What You Need

✅ REW "correction.txt" export files from Magic Beans or similar tool
✅ The `rew_to_fir.py` converter script (included)
✅ Your original `.oca` calibration file (for reference and modification)
✅ Python with numpy and scipy (`uv` handles this automatically)

## Understanding the Files

### REW Correction File Format

REW correction files contain frequency-magnitude pairs:

```
42.3794852422151 0
55.3881821644389 -0.506196538406454
58.1274340250607 -1.48141190591162
...
19057.5011931763 3
```

- **Column 1**: Frequency (Hz)
- **Column 2**: Magnitude correction (dB)

These represent the desired frequency response adjustments to correct your room acoustics.

### OCA Filter Format

OCA files contain **time-domain FIR filter coefficients**:

- **16,321 taps** for Small speakers (with crossover)
- **16,055 taps** for Large speakers (full-range)
- **Causal filters** with main coefficient at index 0
- **Normalized** with first coefficient typically ~0.72

---

## Conversion Process

### Step 1: Generate FIR Filters from REW

Convert each channel's REW correction file to FIR coefficients:

```bash
# For a Small speaker (with crossover) - 16,321 taps
uv run python rew_to_fir.py "mb/ Front Left correction.txt" --taps 16321 --output front_left_fir.json

# For a Large speaker (full-range) - 16,055 taps
uv run python rew_to_fir.py "mb/ Front Height Left correction.txt" --taps 16055 --output front_height_left_fir.json
```

### Step 2: Preview Before Saving

Always preview first to check the filter looks reasonable:

```bash
uv run python rew_to_fir.py "mb/ Front Left correction.txt" --preview
```

**What to look for:**
- ✅ First coefficient around 0.72 (main gain)
- ✅ Subsequent coefficients small (< 0.05 typically)
- ✅ Gradual decay toward the end
- ⚠️ No extreme spikes or discontinuities

### Step 3: Compare with Original OCA

Compare your generated filter with the existing Audyssey calibration:

```bash
uv run python rew_to_fir.py "mb/ Front Left correction.txt" --compare-oca A1EvoExpress_v2_Oct14_1933.oca --channel 0
```

This helps you understand how different your custom curve is from the Audyssey original.

---

## Conversion Parameters

### Number of Taps

**Critical**: Must match the speaker type in your OCA file!

- **16,321 taps**: Small speakers (type "S" with crossover)
- **16,055 taps**: Large speakers (type "E" full-range)

```bash
# Check your OCA file to see which channels need which length
uv run python main.py compare-channels
```

### Sample Rate

Default is **48,000 Hz** (48 kHz), which is standard for Audyssey:

```bash
uv run python rew_to_fir.py "mb/ Front Left correction.txt" --sample-rate 48000
```

You shouldn't need to change this unless your receiver uses a different rate.

### Window Function

The converter applies gentle tapering to the end of the filter. You can choose:

- **hann** (default) - Good balance, smooth rolloff
- **hamming** - Slightly less attenuation
- **blackman** - More aggressive sidelobe suppression
- **bartlett** - Linear taper

```bash
uv run python rew_to_fir.py "mb/ Front Left correction.txt" --window blackman
```

For Audyssey-style causal filters, the choice matters less since we only taper the last 5%.

---

## Importing into OCA File

Once you've generated your FIR filter JSON files, you can import them into your OCA file.

### Manual Method (Python Script)

Create a script to load and replace filters:

```python
import json

# Load OCA file
with open('A1EvoExpress_v2_Oct14_1933.oca', 'r') as f:
    oca_data = json.load(f)

# Load generated FIR filter
with open('front_left_fir.json', 'r') as f:
    new_filter = json.load(f)

# Replace channel 0's filter (Front Left)
oca_data['channels'][0]['filter'] = new_filter

# Optionally, use the same filter for filterLV (low-volume variant)
# Or create a separate filter for dynamic EQ
oca_data['channels'][0]['filterLV'] = new_filter

# Save modified OCA file
with open('modified.oca', 'w') as f:
    json.dump(oca_data, f)

print("✓ Modified OCA file saved!")
```

### Automated Tool (Future Enhancement)

A batch converter tool could:
1. Read all REW correction files in a directory
2. Match them to OCA channels by name
3. Generate and inject all filters at once
4. Validate all constraints

---

## Channel Mapping

Your `mb/` folder contains corrections for various channels. Here's how to map them:

| REW File | OCA Channel | Speaker Type | Taps Needed |
|----------|-------------|--------------|-------------|
| Front Left correction.txt | Channel 0 | Small (S) | 16,321 |
| Front Right correction.txt | Channel 1 | Small (S) | 16,321 |
| Surround Back Left correction.txt | Channel 2 | Small (S) | 16,321 |
| Surround Back Right correction.txt | Channel 3 | Small (S) | 16,321 |
| (Other surround) | Channels 4-5 | Small (S) | 16,321 |
| Front Height Left correction.txt | Channel 6 | Large (E) | 16,055 |
| Front Height Right correction.txt | Channel 7 | Large (E) | 16,055 |

**Check your specific setup:**

```bash
uv run python main.py list-channels
```

---

## Batch Conversion Example

Convert all channels at once:

```bash
# Small speakers (16,321 taps)
uv run python rew_to_fir.py "mb/ Front Left correction.txt" --taps 16321 --output filters/ch0.json
uv run python rew_to_fir.py "mb/ Front Right correction.txt" --taps 16321 --output filters/ch1.json
uv run python rew_to_fir.py "mb/ Surround Back Left correction.txt" --taps 16321 --output filters/ch2.json
uv run python rew_to_fir.py "mb/ Surround Back Right correction.txt" --taps 16321 --output filters/ch3.json

# Large speakers (16,055 taps)
uv run python rew_to_fir.py "mb/ Front Height Left correction.txt" --taps 16055 --output filters/ch6.json
uv run python rew_to_fir.py "mb/ Front Height Right correction.txt" --taps 16055 --output filters/ch7.json
```

---

## Validation Checklist

Before uploading to your receiver, verify:

### Filter Characteristics
- [ ] Correct number of taps (16,321 or 16,055)
- [ ] First coefficient ~0.5 to 0.9 (typically 0.72)
- [ ] No extreme values (> 1.0 in absolute value)
- [ ] Smooth decay without discontinuities
- [ ] Mean close to zero (~0.00004)

### OCA File Integrity
- [ ] Backup original OCA file
- [ ] JSON structure remains valid
- [ ] All other fields unchanged (distance, trim, crossover, etc.)
- [ ] FilterLV array updated (or copied from filter)
- [ ] File size reasonable (~same as original)

### Testing Protocol
- [ ] Modify ONE channel initially
- [ ] Test at LOW volume first
- [ ] Listen for distortion or clipping
- [ ] Compare A/B with original calibration
- [ ] If successful, proceed to other channels

---

## Technical Details

### How the Conversion Works

1. **Load REW file**: Read frequency-magnitude pairs (Hz, dB)

2. **Interpolate to uniform grid**: Create N frequency bins from 0 Hz to Nyquist (24 kHz @ 48kHz sample rate)

3. **Convert dB to linear**: `gain = 10^(dB/20)`

4. **Create complex spectrum**: Assume zero phase (minimum-phase conversion done implicitly)

5. **Inverse FFT**: Transform frequency-domain to time-domain
   ```python
   impulse_response = np.fft.irfft(magnitude_spectrum, n=n_taps)
   ```

6. **Make causal**: Shift peak to the beginning (Audyssey-style)

7. **Taper the tail**: Apply gentle smoothing to last 5% to reduce ringing

8. **Normalize**: Scale so first coefficient matches Audyssey convention (~0.72)

### Why Causal Filters?

Audyssey uses **causal** (non-symmetric) filters rather than linear-phase:

**Advantages:**
- No pre-ringing (sound doesn't arrive "before" the source)
- Lower latency (all energy after time=0)
- More natural transient response

**Trade-off:**
- Phase distortion (acceptable for room correction)
- Less "perfect" frequency response

The converter creates causal filters by shifting the peak to index 0, matching Audyssey's approach.

---

## Troubleshooting

### Problem: Filter has extreme values

**Cause**: REW correction curve is too aggressive (> 10 dB boost/cut)

**Solution**:
- Reduce correction range in REW (limit to ±6 dB)
- Use "house curve" targets instead of flat
- Apply filters gradually with lower gain

### Problem: Filter sounds harsh or distorted

**Cause**: High-frequency corrections too aggressive

**Solution**:
- Limit correction to < 5 kHz
- Use gentler slopes in REW
- Increase filter length if possible

### Problem: No bass after importing filter

**Cause**: Crossover not applied correctly in REW

**Solution**:
- Ensure REW correction includes high-pass filtering at crossover frequency
- Match crossover in REW to OCA channel setting (60/80/100 Hz)
- Don't apply corrections below crossover frequency

### Problem: Different sound at low vs. high volume

**Cause**: FilterLV not updated

**Solution**:
- Create separate low-volume correction in REW
- Apply dynamic EQ adjustments (bass boost at low volume)
- Or simply copy main filter to filterLV for consistent sound

---

## Advanced: FilterLV (Low-Volume Variant)

The `filterLV` array is used by Audyssey Dynamic EQ for volume-dependent correction.

### Strategy 1: Same as Main Filter
```python
oca_data['channels'][0]['filterLV'] = oca_data['channels'][0]['filter']
```
Result: Consistent tonality at all volumes (disables dynamic EQ for this channel)

### Strategy 2: Separate Low-Volume Curve
```python
# Generate low-volume filter with bass boost
uv run python rew_to_fir.py "mb/ Front Left low volume correction.txt" --output front_left_lv.json

with open('front_left_lv.json', 'r') as f:
    low_volume_filter = json.load(f)

oca_data['channels'][0]['filterLV'] = low_volume_filter
```
Result: Custom dynamic EQ that compensates for Fletcher-Munson curves

---

## Example: Complete Workflow

### 1. Export REW Corrections
In Room EQ Wizard:
- File → Export → Filter Settings → Text File
- Save as " Front Left correction.txt"

### 2. Convert to FIR
```bash
uv run python rew_to_fir.py "mb/ Front Left correction.txt" \
  --taps 16321 \
  --sample-rate 48000 \
  --window hann \
  --output front_left_fir.json \
  --compare-oca A1EvoExpress_v2_Oct14_1933.oca --channel 0
```

### 3. Import into OCA
```python
import json

# Backup original
import shutil
shutil.copy('original.oca', 'original_backup.oca')

# Load files
with open('original.oca', 'r') as f:
    oca = json.load(f)

with open('front_left_fir.json', 'r') as f:
    fir_filter = json.load(f)

# Replace channel 0 (Front Left)
oca['channels'][0]['filter'] = fir_filter
oca['channels'][0]['filterLV'] = fir_filter  # Or separate low-volume filter

# Save
with open('modified.oca', 'w') as f:
    json.dump(oca, f, indent=2)

print("✓ Modified OCA saved!")
```

### 4. Test on Receiver
- Upload `modified.oca` via MultEQ app
- Test at **low volume** first
- Listen for any distortion or artifacts
- Compare A/B with original calibration

### 5. Refine if Needed
- Adjust REW corrections based on listening
- Re-export and re-convert
- Iterate until satisfied

---

## Safety Warnings

⚠️ **IMPORTANT**: Improper filters can damage speakers!

- **Always backup original files** before modification
- **Test at low volume** initially (< -30 dB)
- **Listen for distortion** before increasing volume
- **Stop immediately** if you hear clipping or harshness
- **Use conservative corrections** (< 6 dB boost/cut)
- **Never boost high frequencies excessively** (can damage tweeters)

**Recommended approach:**
1. Start with 50% of your intended correction
2. Test thoroughly at multiple volumes
3. Gradually increase correction if needed
4. Document what works for future reference

---

## References

- **Room EQ Wizard (REW)**: https://www.roomeqwizard.com/
- **OCA Format Documentation**: See [OCA_FORMAT.md](OCA_FORMAT.md)
- **FIR Filter Design**: https://en.wikipedia.org/wiki/Finite_impulse_response
- **Audyssey Guide**: Official Denon/Marantz documentation

---

## Future Enhancements

Potential improvements to the converter:

1. **Batch processing tool**: Convert all channels automatically
2. **Frequency response plots**: Visualize before/after
3. **Automatic channel matching**: Match REW files to OCA channels by name
4. **Dynamic EQ optimizer**: Generate optimal filterLV arrays
5. **GUI interface**: Drag-and-drop conversion tool

Contributions welcome!

---

**Document Version**: 1.0
**Last Updated**: October 2024
**Author**: Generated via Claude Code analysis
