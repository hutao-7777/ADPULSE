#!/usr/bin/env python3
"""Import iPinYou RTB dataset into AdPulse SQLite database."""

import argparse
import sys
import uuid
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

# Allow imports from the backend package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession
from tqdm import tqdm

from app.core.database import AsyncSessionLocal, Base, engine  # noqa: E402
from app.models.ipinyou import (
    IpinyouBid,
    IpinyouClick,
    IpinyouConv,
    IpinyouDailyStat,
    IpinyouImp,
)

# iPinYou field indices (tab-separated, no header).
IDX_BID_ID = 0
IDX_TIMESTAMP = 1
IDX_IPINYOU_ID = 2
IDX_USER_AGENT = 3
IDX_IP = 4
IDX_REGION = 5
IDX_CITY = 6
IDX_AD_EXCHANGE = 7
IDX_DOMAIN = 8
IDX_URL = 9
IDX_ANON_URL_ID = 10
IDX_AD_SLOT_ID = 11
IDX_AD_SLOT_WIDTH = 12
IDX_AD_SLOT_HEIGHT = 13
IDX_AD_SLOT_VISIBILITY = 14
IDX_AD_SLOT_FORMAT = 15
IDX_CREATIVE_ID = 16
IDX_BIDDING_PRICE = 17
IDX_PAYING_PRICE = 18
IDX_LANDING_PAGE = 19
IDX_ADVERTISER_ID = 20
IDX_USER_TAGS = 21

EXPECTED_COLUMNS = 22


def parse_timestamp(value: str) -> datetime:
    """Parse iPinYou timestamp (yyyymmddHHMMSS...)."""
    # The timestamp is at least 14 digits long (down to seconds); milliseconds
    # may follow. We keep only the first 14 characters for strptime.
    clean = value.strip()[:14]
    return datetime.strptime(clean, "%Y%m%d%H%M%S")


def parse_price(value: str) -> float:
    """Convert iPinYou price (1/1000 CNY) to CNY."""
    if not value:
        return 0.0
    try:
        return int(value) / 1000.0
    except ValueError:
        return 0.0


def parse_optional_int(value: str) -> Optional[int]:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def parse_optional_str(value: str) -> Optional[str]:
    return value.strip() or None


def read_tsv_rows(
    path: Path, limit: Optional[int] = None, desc: str = "Reading"
) -> Iterable[List[str]]:
    """Yield rows from a tab-separated file with a progress bar."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8", errors="replace") as fh:
        # Estimate total lines for the progress bar.
        total = sum(1 for _ in fh) if limit is None else limit
        fh.seek(0)

        pbar = tqdm(fh, total=total, desc=desc, unit="rows")
        count = 0
        for line in pbar:
            if limit is not None and count >= limit:
                break
            line = line.rstrip("\n\r")
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) != EXPECTED_COLUMNS:
                continue
            count += 1
            yield parts
        pbar.close()


def build_common_fields(parts: List[str]) -> Dict[str, Any]:
    """Extract shared fields from a row into a dict."""
    return {
        "ipinyou_id": parse_optional_str(parts[IDX_IPINYOU_ID]),
        "user_agent": parse_optional_str(parts[IDX_USER_AGENT]),
        "ip": parse_optional_str(parts[IDX_IP]),
        "region": parse_optional_int(parts[IDX_REGION]),
        "city": parse_optional_int(parts[IDX_CITY]),
        "ad_exchange": parse_optional_int(parts[IDX_AD_EXCHANGE]),
        "domain": parse_optional_str(parts[IDX_DOMAIN]),
        "url": parse_optional_str(parts[IDX_URL]),
        "anonymous_url_id": parse_optional_str(parts[IDX_ANON_URL_ID]),
        "ad_slot_id": parse_optional_str(parts[IDX_AD_SLOT_ID]),
        "ad_slot_width": parse_optional_int(parts[IDX_AD_SLOT_WIDTH]),
        "ad_slot_height": parse_optional_int(parts[IDX_AD_SLOT_HEIGHT]),
        "ad_slot_visibility": parse_optional_str(parts[IDX_AD_SLOT_VISIBILITY]),
        "ad_slot_format": parse_optional_str(parts[IDX_AD_SLOT_FORMAT]),
        "creative_id": parse_optional_str(parts[IDX_CREATIVE_ID]),
        "landing_page_url": parse_optional_str(parts[IDX_LANDING_PAGE]),
        "advertiser_id": parse_optional_str(parts[IDX_ADVERTISER_ID]),
        "user_tags": parse_optional_str(parts[IDX_USER_TAGS]),
    }


def build_bid_row(parts: List[str]) -> Dict[str, Any]:
    """Build a row dict for the bid table."""
    fields = build_common_fields(parts)
    fields.update(
        {
            "id": uuid.uuid4(),
            "bid_id": parts[IDX_BID_ID].strip(),
            "timestamp": parse_timestamp(parts[IDX_TIMESTAMP]),
            "bidding_price": parse_price(parts[IDX_BIDDING_PRICE]),
            "paying_price": parse_price(parts[IDX_PAYING_PRICE]),
            "is_win": False,
            "is_clicked": False,
            "is_converted": False,
        }
    )
    return fields


def build_imp_row(parts: List[str]) -> Dict[str, Any]:
    """Build a row dict for the impression table."""
    fields = build_common_fields(parts)
    fields.update(
        {
            "id": uuid.uuid4(),
            "bid_id": parts[IDX_BID_ID].strip(),
            "timestamp": parse_timestamp(parts[IDX_TIMESTAMP]),
            "bid_price": parse_price(parts[IDX_BIDDING_PRICE]),
            "paying_price": parse_price(parts[IDX_PAYING_PRICE]),
        }
    )
    return fields


def build_click_row(parts: List[str]) -> Dict[str, Any]:
    """Build a row dict for the click table."""
    fields = build_common_fields(parts)
    fields.update(
        {
            "id": uuid.uuid4(),
            "bid_id": parts[IDX_BID_ID].strip(),
            "timestamp": parse_timestamp(parts[IDX_TIMESTAMP]),
            "bidding_price": parse_price(parts[IDX_BIDDING_PRICE]),
            "paying_price": parse_price(parts[IDX_PAYING_PRICE]),
        }
    )
    return fields


def build_conv_row(parts: List[str]) -> Dict[str, Any]:
    """Build a row dict for the conversion table."""
    fields = build_common_fields(parts)
    fields.update(
        {
            "id": uuid.uuid4(),
            "bid_id": parts[IDX_BID_ID].strip(),
            "timestamp": parse_timestamp(parts[IDX_TIMESTAMP]),
            "bidding_price": parse_price(parts[IDX_BIDDING_PRICE]),
            "paying_price": parse_price(parts[IDX_PAYING_PRICE]),
        }
    )
    return fields


def compute_daily_stats(
    bid_rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Aggregate daily statistics from bid rows."""
    stats: Dict[Tuple[date, Optional[str]], Dict[str, Any]] = defaultdict(
        lambda: {
            "impressions": 0,
            "clicks": 0,
            "conversions": 0,
            "total_cost": 0.0,
        }
    )

    for row in bid_rows:
        dt: datetime = row["timestamp"]
        day = dt.date()
        advertiser = row.get("advertiser_id")
        key = (day, advertiser)

        if row.get("is_win"):
            stats[key]["impressions"] += 1
            stats[key]["total_cost"] += row.get("paying_price", 0.0)
        if row.get("is_clicked"):
            stats[key]["clicks"] += 1
        if row.get("is_converted"):
            stats[key]["conversions"] += 1

    result = []
    for (day, advertiser), agg in stats.items():
        impressions = agg["impressions"]
        clicks = agg["clicks"]
        avg_ctr = clicks / impressions if impressions else 0.0
        result.append(
            {
                "id": uuid.uuid4(),
                "date": day,
                "advertiser_id": advertiser,
                "impressions": impressions,
                "clicks": clicks,
                "conversions": agg["conversions"],
                "total_cost": round(agg["total_cost"], 6),
                "avg_ctr": round(avg_ctr, 6),
            }
        )
    return result


async def bulk_insert(session: AsyncSession, model, rows: List[Dict[str, Any]]) -> int:
    """Insert rows in bulk, ignoring conflicts."""
    if not rows:
        return 0
    await session.execute(sqlite_insert(model).values(rows).on_conflict_do_nothing())
    return len(rows)


async def import_ipinyou(
    data_dir: Path,
    advertiser: str,
    limit: int,
) -> Dict[str, int]:
    """Run the full import pipeline for one advertiser."""
    advertiser_dir = data_dir / advertiser
    if not advertiser_dir.is_dir():
        raise FileNotFoundError(f"Advertiser directory not found: {advertiser_dir}")

    bid_path = advertiser_dir / "bid.log.txt"
    imp_path = advertiser_dir / "imp.log.txt"
    click_path = advertiser_dir / "click.log.txt"
    conv_path = advertiser_dir / "conv.log.txt"

    # 1. Read bids up to the limit.
    bid_rows: List[Dict[str, Any]] = []
    bid_id_set: Set[str] = set()
    for parts in read_tsv_rows(bid_path, limit=limit, desc="Bids"):
        row = build_bid_row(parts)
        bid_rows.append(row)
        bid_id_set.add(row["bid_id"])

    # 2. Read impressions, clicks and conversions, filtering to the loaded bids.
    imp_rows: List[Dict[str, Any]] = []
    click_rows: List[Dict[str, Any]] = []
    conv_rows: List[Dict[str, Any]] = []

    win_ids: Set[str] = set()
    click_ids: Set[str] = set()
    conv_ids: Set[str] = set()

    if imp_path.exists():
        for parts in read_tsv_rows(imp_path, desc="Impressions"):
            bid_id = parts[IDX_BID_ID].strip()
            if bid_id in bid_id_set:
                imp_rows.append(build_imp_row(parts))
                win_ids.add(bid_id)

    if click_path.exists():
        for parts in read_tsv_rows(click_path, desc="Clicks"):
            bid_id = parts[IDX_BID_ID].strip()
            if bid_id in bid_id_set:
                click_rows.append(build_click_row(parts))
                click_ids.add(bid_id)

    if conv_path.exists():
        for parts in read_tsv_rows(conv_path, desc="Conversions"):
            bid_id = parts[IDX_BID_ID].strip()
            if bid_id in bid_id_set:
                conv_rows.append(build_conv_row(parts))
                conv_ids.add(bid_id)

    # 3. Mark bid flags based on related events.
    for row in bid_rows:
        bid_id = row["bid_id"]
        row["is_win"] = bid_id in win_ids
        row["is_clicked"] = bid_id in click_ids
        row["is_converted"] = bid_id in conv_ids

    # 4. Compute daily statistics.
    daily_stat_rows = compute_daily_stats(bid_rows)

    # 5. Persist everything.
    async with AsyncSessionLocal() as session:
        async with session.begin():
            counts = {
                "bids": await bulk_insert(session, IpinyouBid, bid_rows),
                "impressions": await bulk_insert(session, IpinyouImp, imp_rows),
                "clicks": await bulk_insert(session, IpinyouClick, click_rows),
                "conversions": await bulk_insert(session, IpinyouConv, conv_rows),
                "daily_stats": await bulk_insert(
                    session, IpinyouDailyStat, daily_stat_rows
                ),
            }
        await session.commit()

    return counts


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import iPinYou RTB dataset into AdPulse."
    )
    parser.add_argument(
        "--data-dir",
        required=True,
        type=Path,
        help="Path to the make-ipinyou-data root directory.",
    )
    parser.add_argument(
        "--advertiser",
        required=True,
        help="Advertiser ID to import, e.g. 1458.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50_000,
        help="Maximum number of bid rows to import (default: 50000).",
    )
    args = parser.parse_args()

    # Create tables if they do not exist.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print(
        f"Importing advertiser {args.advertiser} from {args.data_dir} "
        f"(limit={args.limit})"
    )
    counts = await import_ipinyou(args.data_dir, args.advertiser, args.limit)
    print("Import complete:")
    for name, count in counts.items():
        print(f"  {name}: {count}")

    await engine.dispose()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
