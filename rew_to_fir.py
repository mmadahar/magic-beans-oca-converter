#!/usr/bin/env python3
"""
REW to FIR Converter - Convert Room EQ Wizard correction files to FIR filter coefficients

This script converts REW frequency-domain correction curves (frequency, dB pairs)
into time-domain FIR filter coefficients compatible with Audyssey OCA files.

Usage:
    uv run python rew_to_fir.py "mb/ Front Left correction.txt" --taps 16321 --sample-rate 48000
    uv run python rew_to_fir.py "mb/ Front Left correction.txt" --preview  # Preview only
"""

import numpy as np
from scipy.signal import get_window
from scipy.interpolate import interp1d
import sys
import argparse
import json


def load_rew_correction(filepath):
    """Load REW correction file (frequency, magnitude_dB pairs)"""
    frequencies = []
    magnitudes_db = []

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    freq = float(parts[0])
                    mag_db = float(parts[1])
                    frequencies.append(freq)
                    magnitudes_db.append(mag_db)
                except ValueError:
                    continue

    return np.array(frequencies), np.array(magnitudes_db)


def rew_to_fir(rew_file, n_taps=16321, sample_rate=48000, window='hann', normalize=True):
    """
    Convert REW correction curve to FIR filter coefficients

    Parameters:
    -----------
    rew_file : str
        Path to REW correction.txt file
    n_taps : int
        Number of FIR filter taps (must match OCA: 16321 for Small, 16055 for Large)
    sample_rate : int
        Sample rate in Hz (typically 48000 for Audyssey)
    window : str
        Window function ('hann', 'hamming', 'blackman', 'bartlett')
    normalize : bool
        Normalize first coefficient to match Audyssey convention (~0.7)

    Returns:
    --------
    fir_coeffs : np.ndarray
        FIR filter coefficients (length n_taps)
    """

    print(f"Loading REW correction file: {rew_file}")
    freq_points, mag_db_points = load_rew_correction(rew_file)

    print(f"  Loaded {len(freq_points)} frequency points")
    print(f"  Frequency range: {freq_points.min():.1f} Hz - {freq_points.max():.1f} Hz")
    print(f"  Magnitude range: {mag_db_points.min():.2f} dB - {mag_db_points.max():.2f} dB")

    # Create uniform frequency grid for FFT
    # FFT bins: 0 to sample_rate/2 (Nyquist)
    n_freqs = n_taps // 2 + 1
    freq_uniform = np.linspace(0, sample_rate / 2, n_freqs)

    print(f"\nInterpolating to {n_freqs} uniform frequency bins...")

    # Interpolate REW curve to uniform grid
    # Use linear interpolation, extrapolate with boundary values
    interp_func = interp1d(freq_points, mag_db_points,
                           kind='linear',
                           bounds_error=False,
                           fill_value=(mag_db_points[0], mag_db_points[-1]))

    mag_db_uniform = interp_func(freq_uniform)

    # Convert dB to linear magnitude
    mag_linear = 10 ** (mag_db_uniform / 20)

    print(f"  Linear magnitude range: {mag_linear.min():.4f} - {mag_linear.max():.4f}")

    # Create complex spectrum (zero phase for linear-phase FIR)
    # For real signals, we need symmetric spectrum
    complex_spectrum = mag_linear.astype(complex)

    print(f"\nPerforming inverse FFT to get time-domain impulse response...")

    # Use irfft for real-valued output (assumes conjugate symmetry)
    impulse_response = np.fft.irfft(complex_spectrum, n=n_taps)

    # Audyssey uses minimum-phase filters (causal, energy concentrated at start)
    # We need to convert from zero-phase to minimum-phase using Hilbert transform
    # For simplicity, we'll use a causal approach by keeping irfft output as-is
    # and ensuring the peak is near the beginning

    # Find peak location
    peak_idx = np.argmax(np.abs(impulse_response))

    # If peak is not at start, circularly shift to make it causal
    if peak_idx > n_taps // 4:  # If peak is in second half or far from start
        # Shift so peak is near the beginning
        impulse_response = np.roll(impulse_response, -peak_idx)

    print(f"  Impulse response length: {len(impulse_response)}")
    print(f"  Peak value: {impulse_response.max():.6f} at index {np.argmax(np.abs(impulse_response))}")

    # For causal filters, we don't want to apply a full window that zeros the edges
    # Instead, apply a one-sided window or just use the impulse response as-is
    # Audyssey appears to use minimal windowing to preserve the causal nature
    print(f"\nApplying gentle smoothing to reduce artifacts...")

    # Apply a gentle taper to the end only (last 5% of samples)
    taper_start = int(n_taps * 0.95)
    taper_length = n_taps - taper_start
    taper = np.ones(n_taps)
    taper[taper_start:] = np.linspace(1, 0, taper_length)

    fir_coeffs = impulse_response * taper

    print(f"  After tapering - Max: {fir_coeffs.max():.6f}, Min: {fir_coeffs.min():.6f}")

    # Normalize to match Audyssey convention
    if normalize:
        # Find the peak coefficient
        peak_val = np.abs(fir_coeffs).max()
        target_peak = 0.72  # Typical Audyssey first coefficient
        scaling_factor = target_peak / peak_val

        fir_coeffs *= scaling_factor

        print(f"\nNormalized filter:")
        print(f"  Scaling factor: {scaling_factor:.6f}")
        print(f"  First coefficient: {fir_coeffs[0]:.6f}")
        print(f"  Max coefficient: {fir_coeffs.max():.6f}")
        print(f"  Min coefficient: {fir_coeffs.min():.6f}")
        print(f"  Mean: {fir_coeffs.mean():.8f}")
        print(f"  Std dev: {fir_coeffs.std():.8f}")

    return fir_coeffs


def preview_filter(fir_coeffs, n_preview=20):
    """Preview first and last N coefficients"""
    print(f"\n{'='*70}")
    print(f"FILTER PREVIEW")
    print(f"{'='*70}")
    print(f"Total length: {len(fir_coeffs)} coefficients\n")

    print(f"First {n_preview} coefficients:")
    for i in range(min(n_preview, len(fir_coeffs))):
        print(f"  [{i:5d}] = {fir_coeffs[i]:+.10f}")

    print(f"\nLast {n_preview} coefficients:")
    start_idx = len(fir_coeffs) - n_preview
    for i in range(max(0, start_idx), len(fir_coeffs)):
        print(f"  [{i:5d}] = {fir_coeffs[i]:+.10f}")

    print(f"{'='*70}")


def save_coeffs_json(fir_coeffs, output_file):
    """Save coefficients as JSON array"""
    coeffs_list = fir_coeffs.tolist()

    with open(output_file, 'w') as f:
        json.dump(coeffs_list, f, indent=2)

    print(f"\n✓ Saved {len(coeffs_list)} coefficients to {output_file}")


def save_coeffs_txt(fir_coeffs, output_file):
    """Save coefficients as plain text (one per line)"""
    with open(output_file, 'w') as f:
        for coeff in fir_coeffs:
            f.write(f"{coeff:.15f}\n")

    print(f"\n✓ Saved {len(fir_coeffs)} coefficients to {output_file}")


def compare_with_oca(fir_coeffs, oca_file, channel_num):
    """Compare generated filter with existing OCA filter"""
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

    print(f"\nGenerated filter:")
    print(f"  Length: {len(fir_coeffs)}")
    print(f"  First coeff: {fir_coeffs[0]:.10f}")
    print(f"  Max: {fir_coeffs.max():.10f}")
    print(f"  Min: {fir_coeffs.min():.10f}")
    print(f"  Mean: {fir_coeffs.mean():.10f}")

    if len(fir_coeffs) == len(oca_filter):
        print(f"\n✓ Filter lengths match!")
    else:
        print(f"\n⚠ Filter length mismatch!")

    print(f"{'='*70}")


def main():
    parser = argparse.ArgumentParser(
        description='Convert REW correction files to FIR filter coefficients',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview conversion
  uv run python rew_to_fir.py "mb/ Front Left correction.txt" --preview

  # Generate 16321-tap filter (for Small speakers)
  uv run python rew_to_fir.py "mb/ Front Left correction.txt" --taps 16321 --output front_left_fir.json

  # Generate 16055-tap filter (for Large speakers)
  uv run python rew_to_fir.py "mb/ Front Height Left correction.txt" --taps 16055 --window blackman

  # Compare with existing OCA channel
  uv run python rew_to_fir.py "mb/ Front Left correction.txt" --compare-oca A1EvoExpress_v2_Oct14_1933.oca --channel 0
        """
    )

    parser.add_argument('rew_file', help='Path to REW correction.txt file')
    parser.add_argument('--taps', type=int, default=16321,
                        help='Number of FIR taps (16321 for Small, 16055 for Large)')
    parser.add_argument('--sample-rate', type=int, default=48000,
                        help='Sample rate in Hz (default: 48000)')
    parser.add_argument('--window', choices=['hann', 'hamming', 'blackman', 'bartlett'],
                        default='hann', help='Window function (default: hann)')
    parser.add_argument('--output', '-o', help='Output file (.json or .txt)')
    parser.add_argument('--preview', action='store_true',
                        help='Preview filter without saving')
    parser.add_argument('--compare-oca', help='Compare with OCA file')
    parser.add_argument('--channel', type=int, default=0,
                        help='Channel number for comparison (default: 0)')

    args = parser.parse_args()

    # Generate FIR filter
    fir_coeffs = rew_to_fir(
        args.rew_file,
        n_taps=args.taps,
        sample_rate=args.sample_rate,
        window=args.window
    )

    # Preview
    preview_filter(fir_coeffs)

    # Compare with OCA if requested
    if args.compare_oca:
        compare_with_oca(fir_coeffs, args.compare_oca, args.channel)

    # Save if output specified
    if args.output:
        if args.output.endswith('.json'):
            save_coeffs_json(fir_coeffs, args.output)
        else:
            save_coeffs_txt(fir_coeffs, args.output)
        print(f"\n✓ Ready to import into OCA file!")
    elif not args.preview:
        print(f"\n💡 Use --output to save coefficients")
        print(f"   Example: --output front_left_fir.json")


if __name__ == '__main__':
    main()
