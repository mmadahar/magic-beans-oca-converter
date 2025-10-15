# Magic Beans to OCA Conversion Guide

## Overview

**Magic Beans True Target** generates custom target curves and exports them as WAV files containing FIR filter coefficients. This guide shows you how to import these filters into your Audyssey OCA files.

## Important Differences: Magic Beans vs. Audyssey

### Different EQ Methodologies

**Magic Beans:**
- Creates custom target curves tailored to your specific room and speakers
- Exports 65,536-tap FIR filters (very high resolution)
- Uses different normalization (first coefficient ~1.2 instead of ~0.72)
- Designed for use with CamillaDSP, miniDSP, or similar convolution engines

**Audyssey MultEQ:**
- Uses proprietary room correction algorithms
- Applies 16,321-tap FIR filters (or 16,055 for large speakers)
- Normalized with first coefficient ~0.72
- Runs on the receiver's built-in DSP

### Why Convert?

You may want to use Magic Beans filters in your Audyssey system to:
1. Apply custom target curves (Harman, flat, personal preference)
2. Use higher-resolution room correction measurements
3. Combine Magic Beans' flexibility with Audyssey's convenience

⚠️ **Update**: Analysis shows this conversion is **SAFE**! See [FINDINGS.md](FINDINGS.md) for detailed analysis.

---

## ✅ Safety Verification (October 2024)

Comprehensive analysis of your Magic Beans filters reveals:
- **All 7 filters analyzed**: SAFE or MOSTLY_SAFE for truncation
- **Energy loss**: 0.00% when truncating from 65K to 16K taps
- **99%+ energy**: Contained in first ~250 samples
- **Built-in safety checks**: Tools now validate before truncation

**See [FINDINGS.md](FINDINGS.md) for complete analysis report.**

---

## Your Magic Beans Files

You have WAV filter files in the `mb_cdsp/` folder:

```
mb_cdsp/
├── Filters for Front Left.wav
├── Filters for Front Right.wav
├── Filters for Surround Back Left.wav
├── Filters for Surround Back Right.wav
├── Filters for Front Height Left.wav
├── Filters for Front Height Right.wav
├── Filters for LFE.wav
└── Speaker Levels.yml
```

Each WAV file contains:
- **65,536 samples** (FIR filter taps)
- **48,000 Hz** sample rate
- **IEEE Float 32-bit** format
- **Mono** channel

---

## Conversion Process

### Step 1: Check Your OCA Channels

First, see what channel lengths you need:

```bash
uv run python main.py compare-channels
```

Output shows:
- **Small speakers (S)**: Need 16,321 taps
- **Large speakers (E)**: Need 16,055 taps

### Step 2: Extract and Preview Magic Beans Filters

Preview a filter before conversion:

```bash
uv run python wav_to_oca.py "mb_cdsp/Filters for Front Left.wav" --preview
```

**What to look for:**
- Total samples: 65,536 (will be truncated)
- First coefficient: ~1.2 (higher than Audyssey's 0.72)
- Trailing zeros: Shows where the active filter ends

### Step 3: Convert with Target Length

Extract and truncate to OCA-compatible length:

```bash
# For Small speakers (16,321 taps)
uv run python wav_to_oca.py "mb_cdsp/Filters for Front Left.wav" \
  --target-length 16321 \
  --output filters/front_left.json

# For Large speakers (16,055 taps)
uv run python wav_to_oca.py "mb_cdsp/Filters for Front Height Left.wav" \
  --target-length 16055 \
  --output filters/front_height_left.json
```

### Step 4: Compare with Original OCA

See how Magic Beans differs from Audyssey:

```bash
uv run python wav_to_oca.py "mb_cdsp/Filters for Front Left.wav" \
  --target-length 16321 \
  --compare-oca A1EvoExpress_v2_Oct14_1933.oca \
  --channel 0
```

**Key differences you'll see:**
- Magic Beans first coeff: ~1.20 (higher gain)
- Audyssey first coeff: ~0.72
- Magic Beans has larger coefficient values overall
- Different frequency response characteristics

---

## Understanding the Truncation

### Why Truncate from 65,536 to 16,321?

**Magic Beans (65,536 taps):**
- At 48kHz: ~1,365ms filter length
- Very high frequency resolution (~0.73 Hz per bin)
- Can capture very fine room details

**Audyssey OCA (16,321 taps):**
- At 48kHz: ~340ms filter length
- Lower resolution (~2.94 Hz per bin)
- Sufficient for typical room correction

**What happens when we truncate:**
- We keep the first 16,321 samples (most important part)
- Discard the last ~49,000 samples (mostly near-zero tail)
- Lose some fine detail but keep main correction

### Is This Safe?

✅ **Safe if:**
- Active filter region ends before 16,321 samples (check "Active region" in preview)
- Most energy is in the first few hundred samples
- Trailing zeros indicate the filter has decayed

⚠️ **Risky if:**
- Active region extends past 16,321 samples (rare)
- Significant coefficients are being cut off
- You see abrupt changes near sample 16,321

**Check this with:**
```bash
uv run python wav_to_oca.py "mb_cdsp/Filters for Front Left.wav" --preview
```

Look for: `Active region: 0 to 63842` - if the endpoint is < 20,000, truncation is safe.

---

## Normalization Considerations

### Should You Normalize?

**Magic Beans filters have different gain than Audyssey:**

| Property | Magic Beans | Audyssey |
|----------|-------------|----------|
| First coefficient | ~1.2 | ~0.72 |
| Overall gain | Higher | Lower |
| Peak values | Up to 1.2 | Up to 0.72 |

### Option 1: Keep Magic Beans Normalization (Recommended)

**Don't renormalize** - use the filter as-is:

```bash
uv run python wav_to_oca.py "mb_cdsp/Filters for Front Left.wav" \
  --target-length 16321 \
  --output front_left.json
```

**Why:**
- Preserves Magic Beans' intended frequency response
- Maintains the custom target curve calibration
- Filter already optimized for your room

**Trade-off:**
- Louder output (may need to adjust receiver volume)
- Different from Audyssey's convention
- May clip if combined with loud source material

### Option 2: Normalize to Audyssey Convention

If you want to match Audyssey's gain, you could scale manually:

```python
import json
import numpy as np

# Load Magic Beans filter
with open('front_left.json', 'r') as f:
    mb_filter = np.array(json.load(f))

# Calculate scaling factor
current_peak = np.abs(mb_filter).max()  # ~1.2
target_peak = 0.72  # Audyssey convention
scale = target_peak / current_peak  # ~0.6

# Apply scaling
normalized_filter = mb_filter * scale

# Save
with open('front_left_normalized.json', 'w') as f:
    json.dump(normalized_filter.tolist(), f)
```

**Trade-off:**
- Changes the frequency response (reduces all corrections)
- May not match Magic Beans' intended target curve
- More conservative (less likely to clip)

**Our recommendation:** Try Option 1 first at low volume, adjust receiver trim if needed.

---

## Channel Mapping

Map your Magic Beans WAV files to OCA channels:

| Magic Beans File | OCA Channel | Type | Taps | Notes |
|------------------|-------------|------|------|-------|
| Filters for Front Left.wav | 0 | S (Small) | 16,321 | Main left |
| Filters for Front Right.wav | 1 | S (Small) | 16,321 | Main right |
| Filters for Surround Back Left.wav | 2 | S (Small) | 16,321 | Surround |
| Filters for Surround Back Right.wav | 3 | S (Small) | 16,321 | Surround |
| (Use existing for channels 4-5) | 4-5 | S (Small) | 16,321 | Or duplicate |
| Filters for Front Height Left.wav | 6 | E (Large) | 16,055 | Height/Atmos |
| Filters for Front Height Right.wav | 7 | E (Large) | 16,055 | Height/Atmos |

**Check your specific setup:**
```bash
uv run python main.py list-channels
```

---

## Importing into OCA File

### Batch Convert All Channels

```bash
# Create output directory
mkdir -p filters_converted

# Small speakers (16,321 taps)
uv run python wav_to_oca.py "mb_cdsp/Filters for Front Left.wav" \
  --target-length 16321 --output filters_converted/ch0.json

uv run python wav_to_oca.py "mb_cdsp/Filters for Front Right.wav" \
  --target-length 16321 --output filters_converted/ch1.json

uv run python wav_to_oca.py "mb_cdsp/Filters for Surround Back Left.wav" \
  --target-length 16321 --output filters_converted/ch2.json

uv run python wav_to_oca.py "mb_cdsp/Filters for Surround Back Right.wav" \
  --target-length 16321 --output filters_converted/ch3.json

# Large speakers (16,055 taps)
uv run python wav_to_oca.py "mb_cdsp/Filters for Front Height Left.wav" \
  --target-length 16055 --output filters_converted/ch6.json

uv run python wav_to_oca.py "mb_cdsp/Filters for Front Height Right.wav" \
  --target-length 16055 --output filters_converted/ch7.json
```

### Inject into OCA File

```python
import json
import shutil

# Backup original
shutil.copy('A1EvoExpress_v2_Oct14_1933.oca', 'original_backup.oca')

# Load OCA file
with open('A1EvoExpress_v2_Oct14_1933.oca', 'r') as f:
    oca = json.load(f)

# Load and inject filters
channels_to_update = [0, 1, 2, 3, 6, 7]

for ch_num in channels_to_update:
    filter_file = f'filters_converted/ch{ch_num}.json'

    with open(filter_file, 'r') as f:
        new_filter = json.load(f)

    # Update both filter and filterLV
    oca['channels'][ch_num]['filter'] = new_filter
    oca['channels'][ch_num]['filterLV'] = new_filter  # Or keep original

    print(f"✓ Updated channel {ch_num}")

# Save modified OCA
with open('magic_beans_modified.oca', 'w') as f:
    json.dump(oca, f, indent=2)

print("\n✓ Magic Beans filters imported to OCA file!")
```

---

## Testing Protocol

### Phase 1: Single Channel Test

**Start with ONE channel only:**

```python
# Test Front Left only
oca['channels'][0]['filter'] = front_left_magic_beans_filter
# Keep all other channels with original Audyssey filters
```

**Test at low volume:**
1. Upload modified OCA to receiver
2. Play familiar test track
3. Listen for:
   - Distortion or clipping
   - Harsh high frequencies
   - Missing bass
   - Imbalance between left/right

### Phase 2: Stereo Pair Test

If single channel sounds good:

```python
# Add Front Right
oca['channels'][0]['filter'] = front_left_filter
oca['channels'][1]['filter'] = front_right_filter
```

**Listen for:**
- Stereo imaging
- Tonal balance
- Consistent sound between speakers

### Phase 3: Full System

If stereo pair works well, add remaining channels progressively.

### Phase 4: Volume Testing

Test at multiple volume levels:
- Quiet (-40 dB)
- Normal listening (-20 dB)
- Reference (0 dB)
- Loud (+10 dB if safe)

**Stop immediately if you hear:**
- Clipping/distortion
- Harsh treble
- Rattling/buzzing
- Any concerning sounds

---

## Validation Checklist

Before uploading to receiver:

### Filter Validation
- [ ] Correct number of taps (16,321 or 16,055)
- [ ] No NaN or infinite values
- [ ] First coefficient reasonable (0.5 - 1.5 range)
- [ ] Smooth decay without discontinuities
- [ ] JSON file is valid

### OCA File Validation
- [ ] Original file backed up
- [ ] JSON structure intact
- [ ] All other settings unchanged (distance, trim, xover)
- [ ] File size reasonable (~same as original)
- [ ] Can load in JSON validator

### Testing Preparation
- [ ] Start with ONE channel only
- [ ] Test at LOW volume first (-40 dB)
- [ ] Have original OCA ready to reload
- [ ] Know how to quickly revert on receiver

---

## Troubleshooting

### Problem: Sound is too loud / clipping

**Cause**: Magic Beans filters have higher gain (first coeff ~1.2 vs 0.72)

**Solutions**:
1. Reduce receiver master volume by ~4-6 dB
2. Normalize filters to 0.72 (see Option 2 above)
3. Adjust channel trim levels in OCA file

### Problem: Lost bass response

**Cause**: Truncation cut off low-frequency tail, or crossover mismatch

**Solutions**:
1. Check that crossover in OCA matches Magic Beans setup
2. Ensure Magic Beans included high-pass filtering at crossover
3. Try using original Audyssey filter for LFE channel

### Problem: Harsh high frequencies

**Cause**: Magic Beans may have different HF target than Audyssey

**Solutions**:
1. Check Magic Beans target curve settings
2. Re-export from Magic Beans with gentler HF rolloff
3. Apply manual HF cut in receiver tone controls

### Problem: Inconsistent sound across channels

**Cause**: Mixed Magic Beans and Audyssey filters

**Solutions**:
1. Update all main channels together (don't mix methodologies)
2. Ensure all Magic Beans files exported with same settings
3. Check that channel mapping is correct

---

## Advanced: FilterLV Considerations

The `filterLV` array is for Audyssey Dynamic EQ (volume-dependent correction).

### Strategy 1: Use Same Filter (Disable Dynamic EQ)
```python
oca['channels'][0]['filterLV'] = oca['channels'][0]['filter']
```
Result: Consistent sound at all volumes (bypasses dynamic EQ)

### Strategy 2: Keep Audyssey FilterLV
```python
# Don't modify filterLV, only update 'filter'
oca['channels'][0]['filter'] = magic_beans_filter
# filterLV stays as original Audyssey
```
Result: Magic Beans at reference volume, Audyssey dynamic EQ at low volume

### Strategy 3: Custom Low-Volume Filter
If you have separate Magic Beans filters for low volume, use those.

---

## LFE (Subwoofer) Channel

You have `Filters for LFE.wav` - this is for subwoofer correction.

**Considerations:**
- OCA file might handle LFE differently than main channels
- Subwoofer already has its own processing (crossover, bass management)
- May want to keep Audyssey's LFE filter

**Recommendation:**
- Test main speakers first
- Add LFE filter last after confirming others work
- Consider keeping Audyssey LFE if Magic Beans causes issues

---

## Frequency Response Comparison

Want to visualize the difference? Create this script:

```python
import numpy as np
import json
from scipy.fft import fft, fftfreq
import matplotlib.pyplot as plt

# Load both filters
with open('filters_converted/ch0.json', 'r') as f:
    mb_filter = np.array(json.load(f))

with open('A1EvoExpress_v2_Oct14_1933.oca', 'r') as f:
    oca = json.load(f)
    aud_filter = np.array(oca['channels'][0]['filter'])

# Compute frequency responses
sample_rate = 48000
freqs = fftfreq(len(mb_filter), 1/sample_rate)[:len(mb_filter)//2]

mb_freq_resp = fft(mb_filter)[:len(mb_filter)//2]
aud_freq_resp = fft(aud_filter)[:len(aud_filter)//2]

mb_mag_db = 20*np.log10(np.abs(mb_freq_resp))
aud_mag_db = 20*np.log10(np.abs(aud_freq_resp))

# Plot
plt.figure(figsize=(12, 6))
plt.semilogx(freqs[1:], mb_mag_db[1:], label='Magic Beans', linewidth=2)
plt.semilogx(freqs[1:], aud_mag_db[1:], label='Audyssey', linewidth=2)
plt.xlabel('Frequency (Hz)')
plt.ylabel('Magnitude (dB)')
plt.title('Frequency Response Comparison: Magic Beans vs Audyssey')
plt.legend()
plt.grid(True, alpha=0.3)
plt.xlim(20, 20000)
plt.tight_layout()
plt.savefig('frequency_response_comparison.png', dpi=150)
print("✓ Saved frequency_response_comparison.png")
```

---

## Safety Warnings

⚠️ **CRITICAL SAFETY INFORMATION**

1. **Always backup original OCA file** before modification
2. **Test at LOW volume first** (< -30 dB on receiver)
3. **One channel at a time** for initial testing
4. **Listen for any distortion** - stop immediately if heard
5. **Magic Beans filters may be louder** than Audyssey - adjust volume down
6. **Different EQ philosophy** - results may differ from expectations
7. **Experimental process** - no guarantees it will work perfectly
8. **Can damage speakers** if filter causes clipping or excessive excursion

**If in doubt:** Don't do it. Audyssey already provides excellent room correction.

---

## Comparison: Magic Beans vs REW Correction Text Files

You have both:
- `mb/` folder with REW correction.txt files (frequency, dB pairs)
- `mb_cdsp/` folder with Magic Beans WAV files (FIR coefficients)

**Which should you use?**

| Aspect | Magic Beans WAV | REW correction.txt |
|--------|-----------------|-------------------|
| Format | Ready-to-use FIR coefficients | Frequency-domain target curve |
| Resolution | 65,536 taps (very high) | 123 frequency points |
| Processing | Already convolved | Needs FFT conversion |
| Accuracy | Exact Magic Beans intent | Approximation via interpolation |
| Ease | Direct extraction | Requires conversion |

**Recommendation:** Use the Magic Beans WAV files (`mb_cdsp/`) directly - they're already optimized FIR filters.

The REW correction.txt files are useful for:
- Understanding what corrections are being applied
- Generating filters with different lengths
- Creating custom variants

---

## References

- **Magic Beans Audio**: https://magicbeansaudio.com
- **OCA Format Guide**: See [OCA_FORMAT.md](OCA_FORMAT.md)
- **WAV Converter Tool**: [wav_to_oca.py](wav_to_oca.py)
- **AVS Forum Discussion**: Search "Magic Beans True Target"

---

**Document Version**: 1.0
**Last Updated**: October 2024
**Author**: Generated via Claude Code analysis

**Disclaimer**: This is experimental. Magic Beans and Audyssey use different calibration philosophies. Use at your own risk. Always backup original files and test incrementally at low volume.
