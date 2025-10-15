#!/usr/bin/env python3
"""
WAV to OCA Converter - Extract FIR filter coefficients from WAV files

Magic Beans and similar tools export FIR filters as WAV files. This script
extracts the coefficients and prepares them for injection into OCA files.

Usage:
    uv run python wav_to_oca.py "mb_cdsp/Filters for Front Left.wav" --preview
    uv run python wav_to_oca.py "mb_cdsp/Filters for Front Left.wav" --output front_left_fir.json
"""

import numpy as np
import json
import argparse
from scipy.io import wavfile


def load_wav_filter(wav_file):
    """
    Load FIR filter coefficients from a WAV file

    Parameters:
    -----------
    wav_file : str
        Path to WAV file containing FIR coefficients

    Returns:
    --------
    coeffs : np.ndarray
        Filter coefficients
    sample_rate : int
        Sample rate from WAV header
    """
    # Load WAV file using scipy
    sample_rate, data = wavfile.read(wav_file)

    # Convert to float if needed
    if data.dtype == np.int16:
        coeffs = data.astype(float) / 32768.0  # Normalize to [-1, 1]
        print(f"  Format: 16-bit signed integer (converted to float)")
    elif data.dtype == np.int32:
        coeffs = data.astype(float) / 2147483648.0
        print(f"  Format: 32-bit signed integer (converted to float)")
    elif data.dtype == np.float32 or data.dtype == np.float64:
        coeffs = data.astype(float)
        print(f"  Format: {data.dtype} (IEEE Float)")
    else:
        raise ValueError(f"Unsupported data type: {data.dtype}")

    print(f"WAV file properties:")
    print(f"  Sample rate: {sample_rate} Hz")
    print(f"  Total samples: {len(coeffs)}")

    # Handle multi-channel (just use first channel)
    if len(coeffs.shape) > 1:
        n_channels = coeffs.shape[1]
        print(f"  Channels: {n_channels} (using first channel)")
        coeffs = coeffs[:, 0]
    else:
        print(f"  Channels: 1 (mono)")

    return coeffs, sample_rate


def analyze_filter(coeffs):
    """Analyze filter coefficient statistics"""
    print(f"\nFilter Statistics:")
    print(f"  Total coefficients: {len(coeffs)}")
    print(f"  First coefficient: {coeffs[0]:.10f}")
    print(f"  Max value: {coeffs.max():.10f} at index {coeffs.argmax()}")
    print(f"  Min value: {coeffs.min():.10f} at index {coeffs.argmin()}")
    print(f"  Mean: {coeffs.mean():.10f}")
    print(f"  Std dev: {coeffs.std():.10f}")
    print(f"  RMS: {np.sqrt(np.mean(coeffs**2)):.10f}")

    # Check for zeros at start/end
    leading_zeros = 0
    for c in coeffs:
        if abs(c) < 1e-10:
            leading_zeros += 1
        else:
            break

    trailing_zeros = 0
    for c in reversed(coeffs):
        if abs(c) < 1e-10:
            trailing_zeros += 1
        else:
            break

    print(f"  Leading zeros: {leading_zeros}")
    print(f"  Trailing zeros: {trailing_zeros}")
    print(f"  Active region: {leading_zeros} to {len(coeffs) - trailing_zeros - 1}")


def check_truncation_safety(coeffs, target_length):
    """
    Check if truncation is safe before performing it

    Returns:
    --------
    is_safe : bool
        Whether truncation is safe
    risk_level : str
        Risk assessment
    warning_msg : str
        Warning message if unsafe
    """
    # Find active region (above -120dB threshold)
    peak = np.abs(coeffs).max()
    threshold = peak * (10 ** (-120 / 20))
    significant = np.abs(coeffs) > threshold

    if not np.any(significant):
        return True, "SAFE", ""

    active_end = len(coeffs) - np.argmax(significant[::-1]) - 1

    # Calculate energy distribution
    energy = coeffs ** 2
    cumulative_energy = np.cumsum(energy)
    total_energy = cumulative_energy[-1]
    energy_dist = cumulative_energy / total_energy * 100

    energy_at_target = energy_dist[target_length - 1] if target_length <= len(coeffs) else 100.0
    energy_loss = 100.0 - energy_at_target

    # Determine safety
    if active_end < target_length:
        return True, "SAFE", ""
    elif energy_at_target >= 99.0:
        return True, "MOSTLY_SAFE", "⚠️  Active region extends slightly beyond truncation, but 99%+ energy preserved"
    elif energy_at_target >= 95.0:
        warning = f"⚠️  WARNING: {energy_loss:.2f}% energy loss. Consider using --force to proceed anyway."
        return False, "MODERATE_RISK", warning
    else:
        warning = f"🛑 DANGER: {energy_loss:.2f}% energy loss! Truncation would destroy filter. Use --force only if you understand the risks."
        return False, "CATASTROPHIC", warning


def truncate_or_pad(coeffs, target_length, force=False):
    """
    Adjust filter length to match OCA requirements

    Parameters:
    -----------
    coeffs : np.ndarray
        Original filter coefficients
    target_length : int
        Target length (16321 or 16055)
    force : bool
        Force truncation even if unsafe

    Returns:
    --------
    adjusted_coeffs : np.ndarray or None
        Adjusted coefficients, or None if unsafe and not forced
    """
    current_length = len(coeffs)

    if current_length == target_length:
        print(f"\n✓ Filter length already matches target ({target_length})")
        return coeffs

    elif current_length > target_length:
        # Check safety before truncating
        is_safe, risk_level, warning = check_truncation_safety(coeffs, target_length)

        print(f"\n📊 Truncation Safety Check:")
        print(f"   Original length: {current_length:,} → Target: {target_length:,}")
        print(f"   Risk level: {risk_level}")

        if warning:
            print(f"   {warning}")

        if not is_safe and not force:
            print(f"\n❌ Truncation blocked for safety. Use --force to override (not recommended)")
            return None

        if is_safe:
            print(f"   ✓ Safe to truncate")
        elif force:
            print(f"   ⚠️  Forcing truncation despite safety warnings!")

        print(f"\n   Truncating from {current_length:,} to {target_length:,} coefficients")
        print(f"   Removing {current_length - target_length:,} trailing samples")
        return coeffs[:target_length]

    else:
        print(f"\n⚠️  Padding from {current_length} to {target_length} coefficients")
        print(f"   Adding {target_length - current_length} zeros at end")
        padding = np.zeros(target_length - current_length)
        return np.concatenate([coeffs, padding])


def preview_filter(coeffs, n_preview=20):
    """Preview first and last N coefficients"""
    print(f"\n{'='*70}")
    print(f"FILTER PREVIEW")
    print(f"{'='*70}")
    print(f"Total length: {len(coeffs)} coefficients\n")

    print(f"First {n_preview} coefficients:")
    for i in range(min(n_preview, len(coeffs))):
        print(f"  [{i:5d}] = {coeffs[i]:+.10f}")

    print(f"\nLast {n_preview} coefficients:")
    start_idx = len(coeffs) - n_preview
    for i in range(max(0, start_idx), len(coeffs)):
        print(f"  [{i:5d}] = {coeffs[i]:+.10f}")

    print(f"{'='*70}")


def save_coeffs_json(coeffs, output_file):
    """Save coefficients as JSON array"""
    coeffs_list = coeffs.tolist()

    with open(output_file, 'w') as f:
        json.dump(coeffs_list, f, indent=2)

    print(f"\n✓ Saved {len(coeffs_list)} coefficients to {output_file}")
    print(f"  Ready to import into OCA file!")


def compare_with_oca(coeffs, oca_file, channel_num):
    """Compare extracted filter with existing OCA filter"""
    print(f"\n{'='*70}")
    print(f"COMPARISON WITH OCA FILE")
    print(f"{'='*70}")

    with open(oca_file, 'r') as f:
        data = json.load(f)

    oca_filter = np.array(data['channels'][channel_num]['filter'])

    print(f"\nOCA Channel {channel_num} filter:")
    print(f"  Length: {len(oca_filter)}")
    print(f"  First coeff: {oca_filter[0]:.10f}")
    print(f"  Max: {oca_filter.max():.10f}")
    print(f"  Min: {oca_filter.min():.10f}")
    print(f"  Mean: {oca_filter.mean():.10f}")

    print(f"\nExtracted WAV filter:")
    print(f"  Length: {len(coeffs)}")
    print(f"  First coeff: {coeffs[0]:.10f}")
    print(f"  Max: {coeffs.max():.10f}")
    print(f"  Min: {coeffs.min():.10f}")
    print(f"  Mean: {coeffs.mean():.10f}")

    if len(coeffs) == len(oca_filter):
        print(f"\n✓ Filter lengths match!")
    else:
        print(f"\n⚠️  Length mismatch: WAV has {len(coeffs)}, OCA needs {len(oca_filter)}")
        print(f"   Use --target-length {len(oca_filter)} to adjust")

    print(f"{'='*70}")


def main():
    parser = argparse.ArgumentParser(
        description='Extract FIR filter coefficients from WAV files for OCA import',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview WAV filter
  uv run python wav_to_oca.py "mb_cdsp/Filters for Front Left.wav" --preview

  # Extract and save (with length adjustment if needed)
  uv run python wav_to_oca.py "mb_cdsp/Filters for Front Left.wav" \\
    --target-length 16321 --output front_left_fir.json

  # Compare with existing OCA channel
  uv run python wav_to_oca.py "mb_cdsp/Filters for Front Left.wav" \\
    --compare-oca A1EvoExpress_v2_Oct14_1933.oca --channel 0
        """
    )

    parser.add_argument('wav_file', help='Path to WAV filter file')
    parser.add_argument('--target-length', type=int, choices=[16321, 16055],
                        help='Target length for OCA (16321 for Small, 16055 for Large)')
    parser.add_argument('--output', '-o', help='Output JSON file')
    parser.add_argument('--preview', action='store_true',
                        help='Preview filter without saving')
    parser.add_argument('--compare-oca', help='Compare with OCA file')
    parser.add_argument('--channel', type=int, default=0,
                        help='Channel number for comparison (default: 0)')
    parser.add_argument('--force', action='store_true',
                        help='Force truncation even if safety checks fail (use with caution!)')

    args = parser.parse_args()

    # Load WAV filter
    print(f"Loading WAV filter: {args.wav_file}\n")
    coeffs, sample_rate = load_wav_filter(args.wav_file)

    # Analyze
    analyze_filter(coeffs)

    # Adjust length if requested
    if args.target_length:
        coeffs = truncate_or_pad(coeffs, args.target_length, force=args.force)
        if coeffs is None:
            print("\n❌ Operation aborted. Run 'analyze_filter.py' for detailed safety analysis.")
            return
        analyze_filter(coeffs)

    # Preview
    preview_filter(coeffs)

    # Compare with OCA if requested
    if args.compare_oca:
        compare_with_oca(coeffs, args.compare_oca, args.channel)

    # Save if output specified
    if args.output:
        if args.target_length is None:
            print("\n⚠️  Warning: No --target-length specified")
            print("   Saving filter as-is. Ensure length matches OCA requirements!")
        save_coeffs_json(coeffs, args.output)
    elif not args.preview:
        print(f"\n💡 Use --output to save coefficients")
        print(f"   Example: --output front_left_fir.json --target-length 16321")


if __name__ == '__main__':
    main()
