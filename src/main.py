#!/usr/bin/env python3
"""
Main Workflow Orchestrator - OCA Filter Conversion Pipeline

This script orchestrates the complete workflow:
1. Scan mb/convolution/ for Magic Beans WAV files
2. Convert each WAV to OCA-compatible JSON filter
3. Run comprehensive FFT analysis to verify conversions
4. Generate detailed analysis report

Usage:
    uv run python src/main.py
"""

import sys
from pathlib import Path
import json

# Import our modules
from wav_to_oca import load_wav_filter, truncate_or_pad, check_truncation_safety, save_coeffs_json
from comprehensive_fft_analysis import main as run_fft_analysis, CHANNEL_MAPPING

# Paths
WAV_DIR = Path("mb/convolution")
OUTPUT_FILTERS_DIR = Path("output/filters")
REPORTS_DIR = Path("reports")


def convert_wav_to_oca_filter(wav_path: Path, target_length: int, output_path: Path) -> bool:
    """
    Convert a single WAV file to OCA JSON filter.

    Returns True if conversion was successful, False otherwise.
    """
    try:
        print(f"  Loading WAV: {wav_path.name}")
        coeffs = load_wav_filter(str(wav_path))

        print(f"  Original length: {len(coeffs)} taps")
        print(f"  Target length: {target_length} taps")

        # Check if truncation is safe
        is_safe, metrics = check_truncation_safety(coeffs, target_length)

        if not is_safe:
            print(f"  ⚠️  Warning: Truncation may not be safe!")
            print(f"  Energy lost: {metrics['discarded_energy_percent']:.4f}%")
            print(f"  Consider using --force flag if you want to proceed anyway")
            return False

        print(f"  ✓ Truncation safe - energy lost: {metrics['discarded_energy_percent']:.6f}%")

        # Truncate to target length
        truncated_coeffs = truncate_or_pad(coeffs, target_length, force=False)

        # Save to JSON
        save_coeffs_json(truncated_coeffs, str(output_path))
        print(f"  ✓ Saved to: {output_path}")

        return True

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    """Main workflow orchestrator"""
    print("=" * 80)
    print("OCA Filter Conversion Pipeline - Complete Workflow")
    print("=" * 80)
    print()
    print("This workflow will:")
    print("  1. Convert Magic Beans WAV files → OCA JSON filters")
    print("  2. Run comprehensive FFT analysis")
    print("  3. Generate detailed analysis report")
    print()

    # Verify input directory exists
    if not WAV_DIR.exists():
        print(f"❌ Error: WAV directory not found: {WAV_DIR}")
        print("Please ensure Magic Beans WAV files are in mb/convolution/")
        sys.exit(1)

    # Create output directories
    print("Setting up output directories...")
    OUTPUT_FILTERS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    print("✓ Directories ready\n")

    # Step 1: Convert WAV files to OCA JSON filters
    print("=" * 80)
    print("Step 1: Converting WAV Files to OCA Filters")
    print("=" * 80)
    print()

    conversion_results = []

    for config in CHANNEL_MAPPING:
        wav_file = config["wav_file"]
        channel_name = config["channel_name"]
        target_length = config["target_length"]
        short_name = config["short_name"]

        # Determine output filename
        if config["channel_num"] is not None:
            output_filename = f"ch{config['channel_num']}_{short_name}.json"
        else:
            output_filename = f"{short_name}.json"

        print(f"Converting: {channel_name}")
        print(f"  Channel: {config['channel_num'] if config['channel_num'] is not None else 'LFE (no channel num)'}")

        wav_path = WAV_DIR / wav_file

        if not wav_path.exists():
            print(f"  ⚠️  WAV file not found: {wav_file}")
            print(f"  Skipping...\n")
            conversion_results.append({
                "channel": channel_name,
                "status": "skipped",
                "reason": "WAV file not found"
            })
            continue

        output_path = OUTPUT_FILTERS_DIR / output_filename

        success = convert_wav_to_oca_filter(wav_path, target_length, output_path)

        conversion_results.append({
            "channel": channel_name,
            "status": "success" if success else "failed",
            "output": str(output_path) if success else None
        })

        print()

    # Summary of conversions
    successful = sum(1 for r in conversion_results if r["status"] == "success")
    failed = sum(1 for r in conversion_results if r["status"] == "failed")
    skipped = sum(1 for r in conversion_results if r["status"] == "skipped")

    print("=" * 80)
    print("Conversion Summary")
    print("=" * 80)
    print(f"✓ Successful: {successful}")
    if failed > 0:
        print(f"❌ Failed: {failed}")
    if skipped > 0:
        print(f"⚠️  Skipped: {skipped}")
    print()

    if successful == 0:
        print("❌ No filters were successfully converted. Aborting FFT analysis.")
        sys.exit(1)

    # Step 2: Run comprehensive FFT analysis
    print("=" * 80)
    print("Step 2: Running Comprehensive FFT Analysis")
    print("=" * 80)
    print()

    try:
        run_fft_analysis()
    except Exception as e:
        print(f"\n❌ Error during FFT analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Final summary
    print("\n" + "=" * 80)
    print("Pipeline Complete!")
    print("=" * 80)
    print(f"\n✓ Converted {successful} WAV files to OCA JSON filters")
    print(f"✓ Generated comprehensive FFT analysis")
    print(f"✓ Created detailed analysis report")
    print()
    print("Output locations:")
    print(f"  - Filters:       {OUTPUT_FILTERS_DIR}")
    print(f"  - Analysis data: output/data/")
    print(f"  - Plots:         output/plots/")
    print(f"  - Report:        reports/DETAILED_ANALYSIS_REPORT.md")
    print()
    print("Next steps:")
    print("  1. Review reports/DETAILED_ANALYSIS_REPORT.md")
    print("  2. Backup your original OCA file")
    print("  3. Import filters from output/filters/ into your OCA")
    print("  4. Test at low volume")
    print()


if __name__ == '__main__':
    main()
