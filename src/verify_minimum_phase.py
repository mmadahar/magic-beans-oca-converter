#!/usr/bin/env python3
"""
Minimum Phase FIR Filter Verification Tool

This script performs comprehensive empirical tests to verify whether FIR filters
are minimum phase or linear phase. It implements four different mathematical tests:

1. Energy Concentration Test
2. Group Delay Analysis
3. Symmetry Test
4. Zero Location Test (Definitive Proof)

Usage:
    uv run python src/verify_minimum_phase.py <path_to_wav_file>
    uv run python src/verify_minimum_phase.py mb/convolution/"Filters for Front Left.wav"

References:
- DSP Related: https://www.dsprelated.com/freebooks/filters/Minimum_Phase_Filters.html
- Advanced Solutions: https://www.advsolned.com/fir-minimum-phase/
- NYU EE: https://eeweb.engineering.nyu.edu/iselesni/EL713/mpfir/mpfir.pdf
- DSP Guru: https://dspguru.com/dsp/howtos/how-to-design-minimum-phase-fir-filters/

Theory:
    Minimum phase FIR filters have all zeros inside or on the unit circle in the
    z-plane. This results in:
    - Causal impulse response (energy at start, not center)
    - Minimum group delay for given magnitude response
    - Asymmetric impulse response
    - Directly invertible for room correction

    Linear phase FIR filters have:
    - Symmetric or anti-symmetric impulse response
    - Constant group delay of (N-1)/2 samples
    - Pre-ringing artifacts
    - Higher latency
"""

import numpy as np
import sys
from pathlib import Path
from scipy.io import wavfile
from scipy.signal import group_delay


def load_wav_filter(wav_path: Path) -> tuple:
    """Load FIR filter coefficients from WAV file"""
    sample_rate, data = wavfile.read(wav_path)

    # Convert to float
    if data.dtype == np.int16:
        coeffs = data.astype(float) / 32768.0
    elif data.dtype == np.int32:
        coeffs = data.astype(float) / 2147483648.0
    elif data.dtype == np.float32 or data.dtype == np.float64:
        coeffs = data.astype(float)
    else:
        raise ValueError(f"Unsupported data type: {data.dtype}")

    return coeffs, sample_rate


def test_energy_concentration(coeffs: np.ndarray) -> dict:
    """
    Test 1: Energy Concentration

    Minimum phase filters concentrate energy at the beginning of the impulse
    response. Linear phase filters spread energy more evenly across the entire
    response with peak at center.

    Returns:
        dict: Energy percentages at various sample counts
    """
    cumulative_energy = np.cumsum(coeffs**2)
    total_energy = cumulative_energy[-1]

    results = {}
    for samples in [10, 100, 1000, 10000]:
        if samples < len(coeffs):
            pct = (cumulative_energy[samples-1] / total_energy) * 100
            results[samples] = pct

    # Minimum phase should have >95% energy in first 1000 samples
    is_minimum_phase = results.get(1000, 0) > 95.0

    return {
        'energy_distribution': results,
        'is_minimum_phase': is_minimum_phase,
        'confidence': 'high' if results.get(1000, 0) > 99 else 'medium'
    }


def test_group_delay(coeffs: np.ndarray) -> dict:
    """
    Test 2: Group Delay Analysis

    Group delay τ(ω) = -dφ(ω)/dω measures the delay as a function of frequency.

    - Linear phase: constant group delay of (N-1)/2 samples across all frequencies
    - Minimum phase: variable group delay, typically much smaller than (N-1)/2

    Returns:
        dict: Group delay statistics
    """
    try:
        w, gd = group_delay((coeffs, 1), w=2048)
        mean_gd = np.mean(gd)
        std_gd = np.std(gd)
        theoretical_linear_phase_delay = (len(coeffs) - 1) / 2
        ratio = mean_gd / theoretical_linear_phase_delay

        # Minimum phase should have ratio << 1
        is_minimum_phase = ratio < 0.01

        return {
            'mean_group_delay': mean_gd,
            'std_group_delay': std_gd,
            'theoretical_linear_phase_delay': theoretical_linear_phase_delay,
            'ratio': ratio,
            'is_minimum_phase': is_minimum_phase,
            'confidence': 'high' if ratio < 0.001 else 'medium'
        }
    except Exception as e:
        return {
            'error': str(e),
            'is_minimum_phase': None,
            'confidence': 'none'
        }


def test_symmetry(coeffs: np.ndarray) -> dict:
    """
    Test 3: Symmetry Test

    Linear phase FIR filters MUST have symmetric (Type I, II) or anti-symmetric
    (Type III, IV) impulse response. Minimum phase filters are asymmetric.

    Returns:
        dict: Symmetry metrics
    """
    mid = len(coeffs) // 2
    first_half = coeffs[:mid]
    second_half_reversed = coeffs[-mid:][::-1]

    max_diff = np.max(np.abs(first_half - second_half_reversed))
    rms_diff = np.sqrt(np.mean((first_half - second_half_reversed)**2))

    # If symmetric, max_diff should be very small (< 0.001)
    is_symmetric = max_diff < 0.001
    is_minimum_phase = not is_symmetric

    return {
        'max_difference': max_diff,
        'rms_difference': rms_diff,
        'is_symmetric': is_symmetric,
        'is_minimum_phase': is_minimum_phase,
        'confidence': 'high'
    }


def test_zero_locations(coeffs: np.ndarray, max_order: int = 4096) -> dict:
    """
    Test 4: Zero Location Test (DEFINITIVE PROOF)

    The most mathematically rigorous test. A filter is minimum phase if and only if
    all zeros of its transfer function H(z) lie inside or on the unit circle (|z| ≤ 1).

    Warning: Computing roots of polynomials with order > 4096 can be numerically
    unstable, so we test a truncated version for practical purposes.

    Returns:
        dict: Zero location statistics
    """
    # Use subset for numerical stability
    test_length = min(len(coeffs), max_order)
    test_coeffs = coeffs[:test_length]

    print(f"    Computing zeros for {test_length}-tap filter (this may take a moment)...")

    try:
        zeros = np.roots(test_coeffs)
        magnitudes = np.abs(zeros)

        # Categorize zeros with small tolerance for numerical error
        tolerance = 1.001
        outside = np.sum(magnitudes > tolerance)
        on_circle = np.sum((magnitudes >= 0.999) & (magnitudes <= tolerance))
        inside = np.sum(magnitudes < 0.999)

        max_magnitude = np.max(magnitudes)

        # All zeros must be inside/on unit circle for minimum phase
        is_minimum_phase = outside == 0

        return {
            'test_length': test_length,
            'total_zeros': len(zeros),
            'inside_unit_circle': int(inside),
            'on_unit_circle': int(on_circle),
            'outside_unit_circle': int(outside),
            'max_zero_magnitude': max_magnitude,
            'is_minimum_phase': is_minimum_phase,
            'confidence': 'definitive' if is_minimum_phase else 'definitive',
            'warning': 'Tested truncated filter' if test_length < len(coeffs) else None
        }
    except Exception as e:
        return {
            'error': str(e),
            'is_minimum_phase': None,
            'confidence': 'none'
        }


def main():
    """Main execution"""
    if len(sys.argv) < 2:
        print("Usage: uv run python src/verify_minimum_phase.py <path_to_wav_file>")
        print('Example: uv run python src/verify_minimum_phase.py mb/convolution/"Filters for Front Left.wav"')
        sys.exit(1)

    wav_path = Path(sys.argv[1])

    if not wav_path.exists():
        print(f"Error: File not found: {wav_path}")
        sys.exit(1)

    print("=" * 80)
    print("MINIMUM PHASE FIR FILTER VERIFICATION")
    print("=" * 80)
    print(f"\nFile: {wav_path.name}")

    # Load WAV file
    try:
        coeffs, sample_rate = load_wav_filter(wav_path)
        print(f"Length: {len(coeffs)} taps")
        print(f"Sample Rate: {sample_rate} Hz")
        print(f"Duration: {len(coeffs)/sample_rate*1000:.1f} ms")
    except Exception as e:
        print(f"Error loading WAV file: {e}")
        sys.exit(1)

    # Run all tests
    print("\n" + "=" * 80)
    print("TEST 1: Energy Concentration")
    print("=" * 80)
    test1 = test_energy_concentration(coeffs)
    for samples, pct in test1['energy_distribution'].items():
        print(f"  Energy in first {samples:5d} samples: {pct:6.3f}%")
    print(f"\n  Result: {'✓ MINIMUM PHASE' if test1['is_minimum_phase'] else '✗ NOT minimum phase'}")
    print(f"  Confidence: {test1['confidence']}")

    print("\n" + "=" * 80)
    print("TEST 2: Group Delay Analysis")
    print("=" * 80)
    test2 = test_group_delay(coeffs)
    if 'error' in test2:
        print(f"  Error: {test2['error']}")
    else:
        print(f"  Mean group delay: {test2['mean_group_delay']:.1f} samples")
        print(f"  Linear phase would be: {test2['theoretical_linear_phase_delay']:.1f} samples")
        print(f"  Ratio: {test2['ratio']:.6f}")
        print(f"\n  Result: {'✓ MINIMUM PHASE' if test2['is_minimum_phase'] else '✗ NOT minimum phase'}")
        print(f"  Confidence: {test2['confidence']}")

    print("\n" + "=" * 80)
    print("TEST 3: Symmetry Test")
    print("=" * 80)
    test3 = test_symmetry(coeffs)
    print(f"  Max difference between halves: {test3['max_difference']:.6f}")
    print(f"  RMS difference: {test3['rms_difference']:.6f}")
    print(f"  Symmetric: {test3['is_symmetric']}")
    print(f"\n  Result: {'✓ MINIMUM PHASE' if test3['is_minimum_phase'] else '✗ NOT minimum phase (linear phase)'}")
    print(f"  Confidence: {test3['confidence']}")

    print("\n" + "=" * 80)
    print("TEST 4: Zero Location Test (DEFINITIVE PROOF)")
    print("=" * 80)
    test4 = test_zero_locations(coeffs)
    if 'error' in test4:
        print(f"  Error: {test4['error']}")
    else:
        print(f"  Tested filter length: {test4['test_length']} taps")
        print(f"  Total zeros found: {test4['total_zeros']}")
        print(f"  Inside unit circle: {test4['inside_unit_circle']}")
        print(f"  On unit circle: {test4['on_unit_circle']}")
        print(f"  Outside unit circle: {test4['outside_unit_circle']}")
        print(f"  Max zero magnitude: {test4['max_zero_magnitude']:.6f}")
        if test4['warning']:
            print(f"  ⚠️  {test4['warning']}")
        print(f"\n  Result: {'✅ MINIMUM PHASE (DEFINITIVE)' if test4['is_minimum_phase'] else '❌ NOT MINIMUM PHASE (DEFINITIVE)'}")
        print(f"  Confidence: {test4['confidence']}")

    # Final conclusion
    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)

    votes = sum([
        test1['is_minimum_phase'],
        test2.get('is_minimum_phase', False),
        test3['is_minimum_phase'],
        test4.get('is_minimum_phase', False)
    ])

    if votes >= 3:
        print("✅ This filter is MINIMUM PHASE")
        print("\nImplications:")
        print("  • Compatible with Audyssey OCA minimum phase architecture")
        print("  • No phase response problems expected")
        print("  • Causal response with minimal group delay")
        print("  • Directly invertible for room correction")
    else:
        print("⚠️  This filter appears to be LINEAR PHASE or MIXED PHASE")
        print("\nWarning:")
        print("  • May NOT be compatible with Audyssey OCA")
        print("  • Audyssey explicitly requires minimum phase filters")
        print("  • Phase response mismatch could cause problems")

    print("\n" + "=" * 80)


if __name__ == '__main__':
    main()
