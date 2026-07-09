#!/usr/bin/env python3
"""Generate per-advertiser train.log.txt from raw iPinYou bz2 files on Windows.

This script avoids the need for ``make``, bash or bzip2 CLI tools. It reads the
raw ``training*/imp.*.txt.bz2`` and ``training*/clk.*.txt.bz2`` files directly
using Python's ``bz2`` module, filters rows by advertiser, and writes a
``train.log.txt`` compatible with ``scripts/import_ipinyou.py --format formalized``.

Usage:
    python scripts/prepare_ipinyou_windows.py \
        --dataset-dir ../make-ipinyou-data/original-data/ipinyou.contest.dataset \
        --output-dir ../make-ipinyou-data \
        --advertiser 1458 \
        --limit 50000
"""

import argparse
import bz2
from datetime import datetime
from pathlib import Path
from typing import Optional, Set

from tqdm import tqdm

# Raw iPinYou column indices (schema.txt, 24 columns).
# 0:bidid 1:timestamp 2:logtype 3:ipinyouid 4:useragent 5:IP 6:region 7:city
# 8:adexchange 9:domain 10:url 11:urlid 12:slotid 13:slotwidth 14:slotheight
# 15:slotvisibility 16:slotformat 17:slotprice 18:creative 19:bidprice
# 20:payprice 21:keypage 22:advertiser 23:usertag
IDX_BID_ID = 0
IDX_TIMESTAMP = 1
IDX_LOGTYPE = 2
IDX_IPINYOU_ID = 3
IDX_USER_AGENT = 4
IDX_IP = 5
IDX_REGION = 6
IDX_CITY = 7
IDX_AD_EXCHANGE = 8
IDX_DOMAIN = 9
IDX_URL = 10
IDX_URL_ID = 11
IDX_SLOT_ID = 12
IDX_SLOT_WIDTH = 13
IDX_SLOT_HEIGHT = 14
IDX_SLOT_VISIBILITY = 15
IDX_SLOT_FORMAT = 16
IDX_SLOT_PRICE = 17
IDX_CREATIVE = 18
IDX_BID_PRICE = 19
IDX_PAY_PRICE = 20
IDX_KEY_PAGE = 21
IDX_ADVERTISER = 22
IDX_USERTAG = 23

RAW_COLUMNS = 24


def parse_timestamp(value: str) -> datetime:
    """Parse iPinYou timestamp (yyyymmddHHMMSS...)."""
    return datetime.strptime(value.strip()[:14], "%Y%m%d%H%M%S")


def find_bz2_files(root: Path, pattern: str) -> list[Path]:
    """Return sorted list of bz2 files matching pattern under root."""
    return sorted(root.rglob(pattern))


def collect_click_bids(dataset_dir: Path, advertiser: str) -> Set[str]:
    """Read all click bz2 files and return bid IDs for the target advertiser."""
    click_files = find_bz2_files(dataset_dir, "training*/clk.*.txt.bz2")
    click_bids: Set[str] = set()

    if not click_files:
        print("No click log files found.")
        return click_bids

    for file_path in tqdm(click_files, desc="Scanning click files"):
        with bz2.open(file_path, "rt", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.rstrip("\n\r")
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) != RAW_COLUMNS:
                    continue
                if parts[IDX_ADVERTISER].strip() != advertiser:
                    continue
                click_bids.add(parts[IDX_BID_ID].strip())

    return click_bids


def build_train_line(parts: list[str], click_bids: Set[str]) -> str:
    """Prepend click/weekday/hour to a raw impression row."""
    bid_id = parts[IDX_BID_ID].strip()
    click = "1" if bid_id in click_bids else "0"
    ts = parse_timestamp(parts[IDX_TIMESTAMP])
    weekday = str(int(ts.strftime("%w")))
    hour = ts.strftime("%H")
    return f"{click}\t{weekday}\t{hour}\t" + "\t".join(parts) + "\n"


def prepare_advertiser(
    dataset_dir: Path,
    output_dir: Path,
    advertiser: str,
    limit: Optional[int],
) -> int:
    """Generate train.log.txt for one advertiser."""
    if not dataset_dir.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")

    print(f"Collecting click bids for advertiser {advertiser}...")
    click_bids = collect_click_bids(dataset_dir, advertiser)
    print(f"Found {len(click_bids)} click bid IDs.")

    imp_files = find_bz2_files(dataset_dir, "training*/imp.*.txt.bz2")
    if not imp_files:
        raise FileNotFoundError("No impression log files found.")

    advertiser_dir = output_dir / advertiser
    advertiser_dir.mkdir(parents=True, exist_ok=True)
    output_path = advertiser_dir / "train.log.txt"

    header = (
        "click\tweekday\thour\tbidid\ttimestamp\tlogtype\tipinyouid\t"
        "useragent\tIP\tregion\tcity\tadexchange\tdomain\turl\turlid\t"
        "slotid\tslotwidth\tslotheight\tslotvisibility\tslotformat\t"
        "slotprice\tcreative\tbidprice\tpayprice\tkeypage\tadvertiser\t"
        "usertag\n"
    )

    written = 0
    with output_path.open("w", encoding="utf-8") as out:
        out.write(header)
        for file_path in tqdm(imp_files, desc="Writing impressions"):
            if limit is not None and written >= limit:
                break
            with bz2.open(file_path, "rt", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if limit is not None and written >= limit:
                        break
                    line = line.rstrip("\n\r")
                    if not line:
                        continue
                    parts = line.split("\t")
                    if len(parts) != RAW_COLUMNS:
                        continue
                    if parts[IDX_ADVERTISER].strip() != advertiser:
                        continue
                    out.write(build_train_line(parts, click_bids))
                    written += 1

    print(f"Wrote {written} rows to {output_path}")
    return written


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare iPinYou train.log.txt for a specific advertiser on Windows."
        )
    )
    parser.add_argument(
        "--dataset-dir",
        required=True,
        type=Path,
        help="Path to original-data/ipinyou.contest.dataset",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Output root directory (e.g. ../make-ipinyou-data)",
    )
    parser.add_argument(
        "--advertiser",
        required=True,
        help="Advertiser ID, e.g. 1458",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50_000,
        help="Maximum rows to write per advertiser (default: 50000).",
    )
    args = parser.parse_args()

    prepare_advertiser(args.dataset_dir, args.output_dir, args.advertiser, args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
