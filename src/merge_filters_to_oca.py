#!/usr/bin/env python3
"""
OCA Filter Merger - Inject Magic Beans Filters into OCA File

This script takes the original OCA file and injects the converted Magic Beans
FIR filters into the appropriate channels, creating a new modified OCA file.

Usage:
    uv run python src/merge_filters_to_oca.py
    uv run python src/merge_filters_to_oca.py --input input/file.oca --output output/oca/modified.oca
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


# Channel mapping: which filter file goes to which OCA channel
FILTER_MAPPING = [
    {
        "filter_file": "ch0_front_left.json",
        "channel_num": 0,
        "channel_name": "Front Left",
        "description": "S-type (16,321 taps)"
    },
    {
        "filter_file": "ch1_front_right.json",
        "channel_num": 1,
        "channel_name": "Front Right",
        "description": "S-type (16,321 taps)"
    },
    {
        "filter_file": "ch2_surround_back_left.json",
        "channel_num": 2,
        "channel_name": "Surround Back Left",
        "description": "S-type (16,321 taps)"
    },
    {
        "filter_file": "ch3_surround_back_right.json",
        "channel_num": 3,
        "channel_name": "Surround Back Right",
        "description": "S-type (16,321 taps)"
    },
    {
        "filter_file": "ch6_front_height_left.json",
        "channel_num": 6,
        "channel_name": "Front Height Left",
        "description": "E-type (16,055 taps)"
    },
    {
        "filter_file": "ch7_front_height_right.json",
        "channel_num": 7,
        "channel_name": "Front Height Right",
        "description": "E-type (16,055 taps)"
    },
]


def load_oca_file(oca_path: Path) -> dict:
    """Load OCA JSON file"""
    print(f"Loading OCA file: {oca_path}")

    if not oca_path.exists():
        raise FileNotFoundError(f"OCA file not found: {oca_path}")

    with open(oca_path, 'r') as f:
        oca_data = json.load(f)

    # Verify structure
    if 'channels' not in oca_data:
        raise ValueError("Invalid OCA file: missing 'channels' key")

    num_channels = len(oca_data['channels'])
    print(f"  ✓ Loaded {num_channels} channels")
    print(f"  Model: {oca_data.get('model', 'Unknown')}")
    print(f"  A1 Evo Express Version: {oca_data.get('A1EvoExpress', 'Unknown')}")

    return oca_data


def load_filter_file(filter_path: Path) -> List[float]:
    """Load converted filter JSON file"""
    if not filter_path.exists():
        raise FileNotFoundError(f"Filter file not found: {filter_path}")

    with open(filter_path, 'r') as f:
        filter_data = json.load(f)

    if not isinstance(filter_data, list):
        raise ValueError(f"Invalid filter file format: {filter_path}")

    return filter_data


def validate_filter(filter_data: List[float], channel_num: int, oca_data: dict) -> bool:
    """
    Validate that the filter is appropriate for the channel.

    Returns True if valid, False otherwise.
    """
    channel = oca_data['channels'][channel_num]
    expected_length = len(channel['filter'])
    actual_length = len(filter_data)

    if actual_length != expected_length:
        print(f"  ⚠️  Length mismatch: expected {expected_length}, got {actual_length}")
        return False

    # Check for NaN or infinite values
    import math
    for i, val in enumerate(filter_data):
        if not math.isfinite(val):
            print(f"  ⚠️  Invalid value at index {i}: {val}")
            return False

    # Check if first coefficient is reasonable (typically 0.1 to 2.0)
    first_coeff = abs(filter_data[0])
    if first_coeff < 0.01 or first_coeff > 5.0:
        print(f"  ⚠️  Unusual first coefficient: {filter_data[0]}")
        print(f"     (expected range: 0.1 to 2.0)")
        # Don't fail, just warn

    return True


def inject_filters(oca_data: dict, filters_dir: Path,
                  copy_to_lv: bool = True,
                  selected_channels: Optional[List[int]] = None) -> Dict:
    """
    Inject Magic Beans filters into OCA channels.

    Args:
        oca_data: The OCA data dictionary
        filters_dir: Directory containing converted filter JSON files
        copy_to_lv: If True, also copy filter to filterLV (Dynamic EQ)
        selected_channels: If provided, only inject these channel numbers

    Returns:
        Dictionary with injection statistics
    """
    stats = {
        "attempted": 0,
        "successful": 0,
        "skipped": 0,
        "failed": 0,
        "channels_modified": []
    }

    print("\n" + "=" * 80)
    print("Injecting Magic Beans Filters into OCA Channels")
    print("=" * 80)
    print()

    for mapping in FILTER_MAPPING:
        channel_num = mapping["channel_num"]
        filter_file = mapping["filter_file"]
        channel_name = mapping["channel_name"]
        description = mapping["description"]

        stats["attempted"] += 1

        # Check if we should process this channel
        if selected_channels is not None and channel_num not in selected_channels:
            print(f"Channel {channel_num} ({channel_name}): Skipped (not selected)")
            stats["skipped"] += 1
            continue

        print(f"Channel {channel_num} ({channel_name}) - {description}")

        # Check if channel exists in OCA
        if channel_num >= len(oca_data['channels']):
            print(f"  ⚠️  Channel {channel_num} does not exist in OCA file")
            stats["failed"] += 1
            continue

        # Load filter file
        filter_path = filters_dir / filter_file

        if not filter_path.exists():
            print(f"  ⚠️  Filter file not found: {filter_file}")
            stats["skipped"] += 1
            continue

        try:
            print(f"  Loading: {filter_file}")
            new_filter = load_filter_file(filter_path)

            # Validate filter
            print(f"  Validating filter ({len(new_filter)} taps)...")
            if not validate_filter(new_filter, channel_num, oca_data):
                print(f"  ❌ Validation failed")
                stats["failed"] += 1
                continue

            # Get original filter for comparison
            original_filter = oca_data['channels'][channel_num]['filter']
            print(f"  Original first coefficient: {original_filter[0]:.6f}")
            print(f"  New first coefficient:      {new_filter[0]:.6f}")

            # Inject filter
            oca_data['channels'][channel_num]['filter'] = new_filter
            print(f"  ✓ Injected into 'filter'")

            # Optionally inject into filterLV (low-volume variant for Dynamic EQ)
            if copy_to_lv and 'filterLV' in oca_data['channels'][channel_num]:
                oca_data['channels'][channel_num]['filterLV'] = new_filter
                print(f"  ✓ Injected into 'filterLV'")

            stats["successful"] += 1
            stats["channels_modified"].append(channel_num)
            print(f"  ✅ Success!")

        except Exception as e:
            print(f"  ❌ Error: {e}")
            stats["failed"] += 1

        print()

    return stats


def save_oca_file(oca_data: dict, output_path: Path, backup_original: bool = True):
    """Save modified OCA file"""
    print("=" * 80)
    print("Saving Modified OCA File")
    print("=" * 80)
    print()

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # If output path already exists and backup requested, backup it
    if output_path.exists() and backup_original:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = output_path.parent / f"{output_path.stem}_backup_{timestamp}{output_path.suffix}"
        print(f"Backing up existing file to: {backup_path}")
        import shutil
        shutil.copy2(output_path, backup_path)

    # Save with indentation for readability
    print(f"Writing OCA file: {output_path}")
    with open(output_path, 'w') as f:
        json.dump(oca_data, f, indent=2)

    # Get file size
    file_size = output_path.stat().st_size
    file_size_mb = file_size / (1024 * 1024)

    print(f"  ✓ Saved successfully")
    print(f"  File size: {file_size_mb:.2f} MB")
    print()


def print_summary(stats: Dict, output_path: Path):
    """Print final summary"""
    print("=" * 80)
    print("INJECTION SUMMARY")
    print("=" * 80)
    print()
    print(f"Channels attempted:  {stats['attempted']}")
    print(f"✅ Successfully modified: {stats['successful']}")

    if stats['failed'] > 0:
        print(f"❌ Failed: {stats['failed']}")

    if stats['skipped'] > 0:
        print(f"⚠️  Skipped: {stats['skipped']}")

    print()

    if stats['channels_modified']:
        print(f"Modified channels: {', '.join(map(str, stats['channels_modified']))}")

    print()
    print(f"Output file: {output_path}")
    print()
    print("=" * 80)
    print("⚠️  IMPORTANT SAFETY REMINDERS")
    print("=" * 80)
    print()
    print("Before using this modified OCA file:")
    print("  1. ✅ Original OCA file is backed up")
    print("  2. ✅ Review reports/DETAILED_ANALYSIS_REPORT.md")
    print("  3. ⚠️  Upload to A1 Evo Express and test at LOW volume")
    print("  4. ⚠️  Test ONE speaker at a time initially")
    print("  5. ⚠️  Listen for any distortion or clipping")
    print("  6. ⚠️  Gradually increase volume if all sounds normal")
    print()


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(
        description="Inject Magic Beans filters into OCA file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (default paths)
  uv run python src/merge_filters_to_oca.py

  # Specify custom input/output
  uv run python src/merge_filters_to_oca.py --input input/original.oca --output output/oca/modified.oca

  # Only inject specific channels
  uv run python src/merge_filters_to_oca.py --channels 0 1 6 7

  # Don't copy to filterLV (keep original Dynamic EQ filters)
  uv run python src/merge_filters_to_oca.py --no-copy-lv
        """
    )

    parser.add_argument(
        '--input', '-i',
        type=Path,
        default=Path('input/A1EvoExpress_v2_Oct14_1933.oca'),
        help='Input OCA file path (default: input/A1EvoExpress_v2_Oct14_1933.oca)'
    )

    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=None,
        help='Output OCA file path (default: output/oca/modified_YYYYMMDD_HHMMSS.oca)'
    )

    parser.add_argument(
        '--filters-dir', '-f',
        type=Path,
        default=Path('output/filters'),
        help='Directory containing converted filter JSON files (default: output/filters)'
    )

    parser.add_argument(
        '--channels', '-c',
        type=int,
        nargs='+',
        default=None,
        help='Only inject specified channel numbers (e.g., --channels 0 1 6 7)'
    )

    parser.add_argument(
        '--no-copy-lv',
        action='store_true',
        help='Do NOT copy filter to filterLV (keep original Dynamic EQ filters)'
    )

    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Do not backup existing output file'
    )

    args = parser.parse_args()

    # Generate default output path with timestamp if not specified
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = Path(f'output/oca/modified_{timestamp}.oca')

    print("=" * 80)
    print("Magic Beans Filter Injection - OCA Modifier")
    print("=" * 80)
    print()
    print(f"Input OCA:        {args.input}")
    print(f"Output OCA:       {args.output}")
    print(f"Filters directory: {args.filters_dir}")
    print(f"Copy to filterLV: {not args.no_copy_lv}")

    if args.channels:
        print(f"Selected channels: {args.channels}")
    else:
        print(f"Processing:       All available channels")

    print()

    try:
        # Load original OCA
        oca_data = load_oca_file(args.input)

        # Inject filters
        stats = inject_filters(
            oca_data,
            args.filters_dir,
            copy_to_lv=not args.no_copy_lv,
            selected_channels=args.channels
        )

        # Check if any filters were successfully injected
        if stats['successful'] == 0:
            print("❌ No filters were successfully injected. Aborting.")
            return 1

        # Save modified OCA
        save_oca_file(oca_data, args.output, backup_original=not args.no_backup)

        # Print summary
        print_summary(stats, args.output)

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
