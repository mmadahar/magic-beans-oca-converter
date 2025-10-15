#!/usr/bin/env python3
"""
FIR Filter Analysis Tool - Determine if truncation is safe

This tool analyzes FIR filter coefficients to determine:
1. Where the active region (non-negligible coefficients) ends
2. What percentage of energy would be lost by truncation
3. Whether truncation is safe or would destroy the filter
4. Recommendations for proper conversion

Usage:
    uv run python analyze_filter.py "mb_cdsp/Filters for Front Left.wav"
    uv run python analyze_filter.py "mb_cdsp/Filters for Front Left.wav" --target-length 16321
    uv run python analyze_filter.py "mb_cdsp/*.wav" --batch
"""

import numpy as np
import json
import argparse
from scipy.io import wavfile
from pathlib import Path
import glob


def load_wav_filter(wav_file):
    """Load FIR filter from WAV file"""
    sample_rate, data = wavfile.read(wav_file)

    if data.dtype == np.int16:
        coeffs = data.astype(float) / 32768.0
    elif data.dtype == np.int32:
        coeffs = data.astype(float) / 2147483648.0
    elif data.dtype == np.float32 or data.dtype == np.float64:
        coeffs = data.astype(float)
    else:
        raise ValueError(f"Unsupported data type: {data.dtype}")

    # Handle multi-channel
    if len(coeffs.shape) > 1:
        coeffs = coeffs[:, 0]

    return coeffs, sample_rate


def find_active_region(coeffs, threshold_db=-120):
    """
    Find where the active filter region ends

    Active region = where coefficients are above threshold

    Parameters:
    -----------
    coeffs : np.ndarray
        Filter coefficients
    threshold_db : float
        Threshold in dB relative to peak (default -120dB)

    Returns:
    --------
    active_start : int
        First significant coefficient
    active_end : int
        Last significant coefficient
    """
    # Convert threshold to linear
    peak = np.abs(coeffs).max()
    threshold_linear = peak * (10 ** (threshold_db / 20))

    # Find first and last significant samples
    significant = np.abs(coeffs) > threshold_linear

    if not np.any(significant):
        return 0, 0

    active_start = np.argmax(significant)
    active_end = len(coeffs) - np.argmax(significant[::-1]) - 1

    return active_start, active_end


def calculate_energy_distribution(coeffs):
    """
    Calculate cumulative energy distribution

    Returns array showing what % of total energy is contained
    in the first N samples
    """
    energy = coeffs ** 2
    cumulative_energy = np.cumsum(energy)
    total_energy = cumulative_energy[-1]

    return cumulative_energy / total_energy * 100


def find_energy_cutoff(coeffs, target_percent=99.0):
    """
    Find sample index where target% of energy is contained

    Returns the index where cumulative energy reaches target%
    """
    energy_dist = calculate_energy_distribution(coeffs)
    cutoff_idx = np.argmax(energy_dist >= target_percent)

    return cutoff_idx


def analyze_truncation_safety(coeffs, target_length):
    """
    Comprehensive analysis of truncation safety

    Returns:
    --------
    dict with analysis results and recommendations
    """
    original_length = len(coeffs)

    # Find active region
    active_start, active_end = find_active_region(coeffs, threshold_db=-120)
    active_length = active_end - active_start + 1

    # Calculate energy cutoffs
    energy_50_idx = find_energy_cutoff(coeffs, 50.0)
    energy_90_idx = find_energy_cutoff(coeffs, 90.0)
    energy_95_idx = find_energy_cutoff(coeffs, 95.0)
    energy_99_idx = find_energy_cutoff(coeffs, 99.0)
    energy_999_idx = find_energy_cutoff(coeffs, 99.9)

    # Energy at target length
    energy_dist = calculate_energy_distribution(coeffs)
    energy_at_target = energy_dist[target_length - 1] if target_length <= len(coeffs) else 100.0
    energy_loss_percent = 100.0 - energy_at_target

    # Calculate RMS in different regions
    rms_full = np.sqrt(np.mean(coeffs ** 2))
    rms_kept = np.sqrt(np.mean(coeffs[:target_length] ** 2))
    rms_discarded = np.sqrt(np.mean(coeffs[target_length:] ** 2)) if target_length < len(coeffs) else 0

    # Determine safety
    is_safe = False
    risk_level = "CATASTROPHIC"

    if active_end < target_length:
        is_safe = True
        risk_level = "SAFE"
    elif energy_99_idx < target_length:
        is_safe = True
        risk_level = "MOSTLY_SAFE"
    elif energy_95_idx < target_length:
        risk_level = "MODERATE_RISK"
    elif energy_90_idx < target_length:
        risk_level = "HIGH_RISK"
    else:
        risk_level = "CATASTROPHIC"

    # Generate recommendation
    if risk_level == "SAFE":
        recommendation = "✓ Safe to truncate - active region ends before truncation point"
    elif risk_level == "MOSTLY_SAFE":
        recommendation = "⚠ Mostly safe - 99% of energy preserved, but expect minor quality loss"
    elif risk_level == "MODERATE_RISK":
        recommendation = "⚠ Risky - significant filter content will be lost. Consider frequency domain redesign."
    elif risk_level == "HIGH_RISK":
        recommendation = "⛔ Dangerous - major filter content will be lost. Use frequency domain redesign."
    else:
        recommendation = "🛑 CATASTROPHIC - truncation will destroy the filter. Do NOT truncate!"

    return {
        'original_length': original_length,
        'target_length': target_length,
        'active_start': active_start,
        'active_end': active_end,
        'active_length': active_length,
        'energy_50_idx': energy_50_idx,
        'energy_90_idx': energy_90_idx,
        'energy_95_idx': energy_95_idx,
        'energy_99_idx': energy_99_idx,
        'energy_999_idx': energy_999_idx,
        'energy_at_target_percent': energy_at_target,
        'energy_loss_percent': energy_loss_percent,
        'rms_full': rms_full,
        'rms_kept': rms_kept,
        'rms_discarded': rms_discarded,
        'is_safe': is_safe,
        'risk_level': risk_level,
        'recommendation': recommendation
    }


def print_analysis(filename, analysis, sample_rate):
    """Pretty print analysis results"""
    print(f"\n{'='*70}")
    print(f"FILTER TRUNCATION ANALYSIS")
    print(f"{'='*70}")
    print(f"File: {filename}")
    print(f"Sample rate: {sample_rate} Hz")

    print(f"\n📊 FILTER DIMENSIONS:")
    print(f"  Original length: {analysis['original_length']:,} taps")
    print(f"  Target length:   {analysis['target_length']:,} taps")
    print(f"  Duration @ {sample_rate}Hz: {analysis['original_length']/sample_rate:.3f}s → {analysis['target_length']/sample_rate:.3f}s")

    print(f"\n🎯 ACTIVE REGION (above -120dB):")
    print(f"  Start: sample {analysis['active_start']:,}")
    print(f"  End:   sample {analysis['active_end']:,}")
    print(f"  Length: {analysis['active_length']:,} active taps")

    if analysis['active_end'] >= analysis['target_length']:
        print(f"  ⚠️  Active region EXTENDS BEYOND truncation point!")
        print(f"  ⚠️  Would cut off {analysis['active_end'] - analysis['target_length']:,} active samples")
    else:
        print(f"  ✓ Active region ends before truncation point")
        print(f"  ✓ Safe margin: {analysis['target_length'] - analysis['active_end']:,} samples")

    print(f"\n⚡ ENERGY DISTRIBUTION:")
    print(f"  50% of energy in first:  {analysis['energy_50_idx']:,} samples")
    print(f"  90% of energy in first:  {analysis['energy_90_idx']:,} samples")
    print(f"  95% of energy in first:  {analysis['energy_95_idx']:,} samples")
    print(f"  99% of energy in first:  {analysis['energy_99_idx']:,} samples")
    print(f"  99.9% of energy in first: {analysis['energy_999_idx']:,} samples")

    print(f"\n📉 TRUNCATION IMPACT:")
    print(f"  Energy preserved: {analysis['energy_at_target_percent']:.4f}%")
    print(f"  Energy lost:      {analysis['energy_loss_percent']:.4f}%")
    print(f"  RMS (full filter):     {analysis['rms_full']:.6f}")
    print(f"  RMS (kept region):     {analysis['rms_kept']:.6f}")
    print(f"  RMS (discarded region): {analysis['rms_discarded']:.6f}")

    print(f"\n🚦 SAFETY ASSESSMENT:")
    print(f"  Risk level: {analysis['risk_level']}")
    print(f"  {analysis['recommendation']}")

    print(f"{'='*70}\n")


def print_summary_table(results):
    """Print summary table for batch analysis"""
    print(f"\n{'='*100}")
    print(f"BATCH ANALYSIS SUMMARY")
    print(f"{'='*100}")

    print(f"\n{'File':<35} {'Active End':<12} {'99% Energy':<12} {'Loss %':<10} {'Risk':<15}")
    print(f"{'-'*100}")

    for result in results:
        filename = Path(result['filename']).name[:33]
        active_end = f"{result['analysis']['active_end']:,}"
        energy_99 = f"{result['analysis']['energy_99_idx']:,}"
        loss = f"{result['analysis']['energy_loss_percent']:.2f}%"
        risk = result['analysis']['risk_level']

        print(f"{filename:<35} {active_end:<12} {energy_99:<12} {loss:<10} {risk:<15}")

    print(f"{'-'*100}")

    # Count by risk level
    from collections import Counter
    risk_counts = Counter(r['analysis']['risk_level'] for r in results)

    print(f"\nRisk Distribution:")
    for risk, count in sorted(risk_counts.items()):
        print(f"  {risk}: {count} file(s)")

    print(f"{'='*100}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Analyze FIR filter truncation safety',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze single filter for 16321-tap truncation
  uv run python analyze_filter.py "mb_cdsp/Filters for Front Left.wav"

  # Check for different target length
  uv run python analyze_filter.py "mb_cdsp/Filters for Front Left.wav" --target-length 16055

  # Batch analyze all filters
  uv run python analyze_filter.py "mb_cdsp/Filters*.wav" --batch

  # Save results to JSON
  uv run python analyze_filter.py "mb_cdsp/Filters for Front Left.wav" --json analysis_results.json
        """
    )

    parser.add_argument('wav_file', help='WAV file or glob pattern (e.g., "mb_cdsp/*.wav")')
    parser.add_argument('--target-length', type=int, default=16321,
                        help='Target filter length (default: 16321 for Audyssey Small speakers)')
    parser.add_argument('--batch', action='store_true',
                        help='Process multiple files and show summary')
    parser.add_argument('--json', help='Save analysis results to JSON file')

    args = parser.parse_args()

    # Handle glob patterns
    if '*' in args.wav_file or '?' in args.wav_file:
        wav_files = glob.glob(args.wav_file)
        if not wav_files:
            print(f"No files found matching: {args.wav_file}")
            return
    else:
        wav_files = [args.wav_file]

    results = []

    for wav_file in wav_files:
        # Load filter
        coeffs, sample_rate = load_wav_filter(wav_file)

        # Analyze
        analysis = analyze_truncation_safety(coeffs, args.target_length)

        # Store results
        results.append({
            'filename': wav_file,
            'sample_rate': sample_rate,
            'analysis': analysis
        })

        # Print individual results if not in batch mode
        if not args.batch:
            print_analysis(wav_file, analysis, sample_rate)

    # Print summary for batch mode
    if args.batch and len(results) > 1:
        print_summary_table(results)

    # Save to JSON if requested
    if args.json:
        # Convert numpy types to Python types for JSON serialization
        json_results = []
        for r in results:
            json_r = {
                'filename': r['filename'],
                'sample_rate': int(r['sample_rate']),
                'analysis': {k: float(v) if isinstance(v, (np.integer, np.floating)) else v
                           for k, v in r['analysis'].items()}
            }
            json_results.append(json_r)

        with open(args.json, 'w') as f:
            json.dump(json_results, f, indent=2)

        print(f"✓ Analysis saved to {args.json}")


if __name__ == '__main__':
    main()
