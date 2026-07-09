#!/usr/bin/env python3
"""Import iPinYou RTB dataset into AdPulse SQLite database.

Supports two layouts:

* ``raw`` - per-advertiser ``bid.log.txt``, ``imp.log.txt``, ``click.log.txt``
  and ``conv.log.txt`` (tab separated, 22 columns, no header).
* ``formalized`` - output of ``make-ipinyou-data``: ``advertiser/train.log.txt``
  and ``advertiser/test.log.txt`` (tab separated, 27 columns, with header).
"""

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
from app.models.ipinyou import (  # noqa: E402
    IpinyouBid,
    IpinyouClick,
    IpinyouConv,
    IpinyouDailyStat,
    IpinyouImp,
)

# ---------------------------------------------------------------------------
# Raw layout indices (bid.log.txt / imp.log.txt / click.log.txt / conv.log.txt)
# ---------------------------------------------------------------------------
RAW_IDX_BID_ID = 0
RAW_IDX_TIMESTAMP = 1
RAW_IDX_IPINYOU_ID = 2
RAW_IDX_USER_AGENT = 3
RAW_IDX_IP = 4
RAW_IDX_REGION = 5
RAW_IDX_CITY = 6
RAW_IDX_AD_EXCHANGE = 7
RAW_IDX_DOMAIN = 8
RAW_IDX_URL = 9
RAW_IDX_ANON_URL_ID = 10
RAW_IDX_AD_SLOT_ID = 11
RAW_IDX_AD_SLOT_WIDTH = 12
RAW_IDX_AD_SLOT_HEIGHT = 13
RAW_IDX_AD_SLOT_VISIBILITY = 14
RAW_IDX_AD_SLOT_FORMAT = 15
RAW_IDX_CREATIVE_ID = 16
RAW_IDX_BIDDING_PRICE = 17
RAW_IDX_PAYING_PRICE = 18
RAW_IDX_LANDING_PAGE = 19
RAW_IDX_ADVERTISER_ID = 20
RAW_IDX_USER_TAGS = 21
RAW_COLUMNS = 22

# ---------------------------------------------------------------------------
# Formalized layout indices (train.log.txt / test.log.txt from make-ipinyou-data)
# Columns: click, weekday, hour, <original schema>
# ---------------------------------------------------------------------------
FORM_IDX_CLICK = 0
FORM_IDX_BID_ID = 3
FORM_IDX_TIMESTAMP = 4
FORM_IDX_IPINYOU_ID = 6
FORM_IDX_USER_AGENT = 7
FORM_IDX_IP = 8
FORM_IDX_REGION = 9
FORM_IDX_CITY = 10
FORM_IDX_AD_EXCHANGE = 11
FORM_IDX_DOMAIN = 12
FORM_IDX_URL = 13
FORM_IDX_URL_ID = 14
FORM_IDX_AD_SLOT_ID = 15
FORM_IDX_AD_SLOT_WIDTH = 16
FORM_IDX_AD_SLOT_HEIGHT = 17
FORM_IDX_AD_SLOT_VISIBILITY = 18
FORM_IDX_AD_SLOT_FORMAT = 19
FORM_IDX_SLOT_PRICE = 20
FORM_IDX_CREATIVE_ID = 21
FORM_IDX_BID_PRICE = 22
FORM_IDX_PAY_PRICE = 23
FORM_IDX_KEY_PAGE = 24
FORM_IDX_ADVERTISER_ID = 25
FORM_IDX_USER_TAGS = 26
FORM_COLUMNS = 27


def parse_timestamp(value: str) -> datetime:
    """Parse iPinYou timestamp (yyyymmddHHMMSS...)."""
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
    path: Path,
    limit: Optional[int] = None,
    desc: str = "Reading",
    skip_header: bool = False,
) -> Iterable[List[str]]:
    """Yield rows from a tab-separated file with a progress bar."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8", errors="replace") as fh:
        total = sum(1 for _ in fh) if limit is None else limit
        fh.seek(0)
        if skip_header:
            next(fh, None)
            total = max(0, total - 1)

        pbar = tqdm(fh, total=total, desc=desc, unit="rows")
        count = 0
        for line in pbar:
            if limit is not None and count >= limit:
                break
            line = line.rstrip("\n\r")
            if not line:
                continue
            count += 1
            yield line.split("\t")
        pbar.close()


# ---------------------------------------------------------------------------
# Raw format helpers
# ---------------------------------------------------------------------------
def build_raw_common_fields(parts: List[str]) -> Dict[str, Any]:
    return {
        "ipinyou_id": parse_optional_str(parts[RAW_IDX_IPINYOU_ID]),
        "user_agent": parse_optional_str(parts[RAW_IDX_USER_AGENT]),
        "ip": parse_optional_str(parts[RAW_IDX_IP]),
        "region": parse_optional_int(parts[RAW_IDX_REGION]),
        "city": parse_optional_int(parts[RAW_IDX_CITY]),
        "ad_exchange": parse_optional_int(parts[RAW_IDX_AD_EXCHANGE]),
        "domain": parse_optional_str(parts[RAW_IDX_DOMAIN]),
        "url": parse_optional_str(parts[RAW_IDX_URL]),
        "anonymous_url_id": parse_optional_str(parts[RAW_IDX_ANON_URL_ID]),
        "ad_slot_id": parse_optional_str(parts[RAW_IDX_AD_SLOT_ID]),
        "ad_slot_width": parse_optional_int(parts[RAW_IDX_AD_SLOT_WIDTH]),
        "ad_slot_height": parse_optional_int(parts[RAW_IDX_AD_SLOT_HEIGHT]),
        "ad_slot_visibility": parse_optional_str(parts[RAW_IDX_AD_SLOT_VISIBILITY]),
        "ad_slot_format": parse_optional_str(parts[RAW_IDX_AD_SLOT_FORMAT]),
        "creative_id": parse_optional_str(parts[RAW_IDX_CREATIVE_ID]),
        "landing_page_url": parse_optional_str(parts[RAW_IDX_LANDING_PAGE]),
        "advertiser_id": parse_optional_str(parts[RAW_IDX_ADVERTISER_ID]),
        "user_tags": parse_optional_str(parts[RAW_IDX_USER_TAGS]),
    }


def build_raw_bid_row(parts: List[str]) -> Dict[str, Any]:
    fields = build_raw_common_fields(parts)
    fields.update(
        {
            "id": uuid.uuid4(),
            "bid_id": parts[RAW_IDX_BID_ID].strip(),
            "timestamp": parse_timestamp(parts[RAW_IDX_TIMESTAMP]),
            "bidding_price": parse_price(parts[RAW_IDX_BIDDING_PRICE]),
            "paying_price": parse_price(parts[RAW_IDX_PAYING_PRICE]),
            "is_win": False,
            "is_clicked": False,
            "is_converted": False,
        }
    )
    return fields


def build_raw_imp_row(parts: List[str]) -> Dict[str, Any]:
    fields = build_raw_common_fields(parts)
    fields.update(
        {
            "id": uuid.uuid4(),
            "bid_id": parts[RAW_IDX_BID_ID].strip(),
            "timestamp": parse_timestamp(parts[RAW_IDX_TIMESTAMP]),
            "bid_price": parse_price(parts[RAW_IDX_BIDDING_PRICE]),
            "paying_price": parse_price(parts[RAW_IDX_PAYING_PRICE]),
        }
    )
    return fields


def build_raw_click_row(parts: List[str]) -> Dict[str, Any]:
    fields = build_raw_common_fields(parts)
    fields.update(
        {
            "id": uuid.uuid4(),
            "bid_id": parts[RAW_IDX_BID_ID].strip(),
            "timestamp": parse_timestamp(parts[RAW_IDX_TIMESTAMP]),
            "bidding_price": parse_price(parts[RAW_IDX_BIDDING_PRICE]),
            "paying_price": parse_price(parts[RAW_IDX_PAYING_PRICE]),
        }
    )
    return fields


def build_raw_conv_row(parts: List[str]) -> Dict[str, Any]:
    fields = build_raw_common_fields(parts)
    fields.update(
        {
            "id": uuid.uuid4(),
            "bid_id": parts[RAW_IDX_BID_ID].strip(),
            "timestamp": parse_timestamp(parts[RAW_IDX_TIMESTAMP]),
            "bidding_price": parse_price(parts[RAW_IDX_BIDDING_PRICE]),
            "paying_price": parse_price(parts[RAW_IDX_PAYING_PRICE]),
        }
    )
    return fields


# ---------------------------------------------------------------------------
# Formalized format helpers (make-ipinyou-data output)
# ---------------------------------------------------------------------------
def build_form_common_fields(parts: List[str]) -> Dict[str, Any]:
    return {
        "ipinyou_id": parse_optional_str(parts[FORM_IDX_IPINYOU_ID]),
        "user_agent": parse_optional_str(parts[FORM_IDX_USER_AGENT]),
        "ip": parse_optional_str(parts[FORM_IDX_IP]),
        "region": parse_optional_int(parts[FORM_IDX_REGION]),
        "city": parse_optional_int(parts[FORM_IDX_CITY]),
        "ad_exchange": parse_optional_int(parts[FORM_IDX_AD_EXCHANGE]),
        "domain": parse_optional_str(parts[FORM_IDX_DOMAIN]),
        "url": parse_optional_str(parts[FORM_IDX_URL]),
        "anonymous_url_id": parse_optional_str(parts[FORM_IDX_URL_ID]),
        "ad_slot_id": parse_optional_str(parts[FORM_IDX_AD_SLOT_ID]),
        "ad_slot_width": parse_optional_int(parts[FORM_IDX_AD_SLOT_WIDTH]),
        "ad_slot_height": parse_optional_int(parts[FORM_IDX_AD_SLOT_HEIGHT]),
        "ad_slot_visibility": parse_optional_str(parts[FORM_IDX_AD_SLOT_VISIBILITY]),
        "ad_slot_format": parse_optional_str(parts[FORM_IDX_AD_SLOT_FORMAT]),
        "creative_id": parse_optional_str(parts[FORM_IDX_CREATIVE_ID]),
        "landing_page_url": parse_optional_str(parts[FORM_IDX_KEY_PAGE]),
        "advertiser_id": parse_optional_str(parts[FORM_IDX_ADVERTISER_ID]),
        "user_tags": parse_optional_str(parts[FORM_IDX_USER_TAGS]),
    }


def build_form_bid_row(parts: List[str]) -> Dict[str, Any]:
    """Each formalized row corresponds to a winning bid."""
    fields = build_form_common_fields(parts)
    fields.update(
        {
            "id": uuid.uuid4(),
            "bid_id": parts[FORM_IDX_BID_ID].strip(),
            "timestamp": parse_timestamp(parts[FORM_IDX_TIMESTAMP]),
            "bidding_price": parse_price(parts[FORM_IDX_BID_PRICE]),
            "paying_price": parse_price(parts[FORM_IDX_PAY_PRICE]),
            "is_win": True,
            "is_clicked": parts[FORM_IDX_CLICK].strip() == "1",
            "is_converted": False,
        }
    )
    return fields


def build_form_imp_row(parts: List[str]) -> Dict[str, Any]:
    fields = build_form_common_fields(parts)
    fields.update(
        {
            "id": uuid.uuid4(),
            "bid_id": parts[FORM_IDX_BID_ID].strip(),
            "timestamp": parse_timestamp(parts[FORM_IDX_TIMESTAMP]),
            "bid_price": parse_price(parts[FORM_IDX_BID_PRICE]),
            "paying_price": parse_price(parts[FORM_IDX_PAY_PRICE]),
        }
    )
    return fields


def build_form_click_row(parts: List[str]) -> Dict[str, Any]:
    fields = build_form_common_fields(parts)
    fields.update(
        {
            "id": uuid.uuid4(),
            "bid_id": parts[FORM_IDX_BID_ID].strip(),
            "timestamp": parse_timestamp(parts[FORM_IDX_TIMESTAMP]),
            "bidding_price": parse_price(parts[FORM_IDX_BID_PRICE]),
            "paying_price": parse_price(parts[FORM_IDX_PAY_PRICE]),
        }
    )
    return fields


# ---------------------------------------------------------------------------
# Aggregation and persistence
# ---------------------------------------------------------------------------
def compute_daily_stats(bid_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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


async def bulk_insert(
    session: AsyncSession, model: Any, rows: List[Dict[str, Any]]
) -> int:
    """Insert rows in bulk, ignoring conflicts."""
    if not rows:
        return 0
    await session.execute(sqlite_insert(model).values(rows).on_conflict_do_nothing())
    return len(rows)


async def import_raw_format(
    data_dir: Path,
    advertiser: str,
    limit: int,
) -> Dict[str, int]:
    """Import from per-advertiser raw log files."""
    advertiser_dir = data_dir / advertiser
    if not advertiser_dir.is_dir():
        raise FileNotFoundError(f"Advertiser directory not found: {advertiser_dir}")

    bid_path = advertiser_dir / "bid.log.txt"
    imp_path = advertiser_dir / "imp.log.txt"
    click_path = advertiser_dir / "click.log.txt"
    conv_path = advertiser_dir / "conv.log.txt"

    bid_rows: List[Dict[str, Any]] = []
    bid_id_set: Set[str] = set()
    for parts in read_tsv_rows(bid_path, limit=limit, desc="Bids"):
        if len(parts) != RAW_COLUMNS:
            continue
        row = build_raw_bid_row(parts)
        bid_rows.append(row)
        bid_id_set.add(row["bid_id"])

    imp_rows: List[Dict[str, Any]] = []
    click_rows: List[Dict[str, Any]] = []
    conv_rows: List[Dict[str, Any]] = []
    win_ids: Set[str] = set()
    click_ids: Set[str] = set()
    conv_ids: Set[str] = set()

    if imp_path.exists():
        for parts in read_tsv_rows(imp_path, desc="Impressions"):
            if len(parts) != RAW_COLUMNS:
                continue
            bid_id = parts[RAW_IDX_BID_ID].strip()
            if bid_id in bid_id_set:
                imp_rows.append(build_raw_imp_row(parts))
                win_ids.add(bid_id)

    if click_path.exists():
        for parts in read_tsv_rows(click_path, desc="Clicks"):
            if len(parts) != RAW_COLUMNS:
                continue
            bid_id = parts[RAW_IDX_BID_ID].strip()
            if bid_id in bid_id_set:
                click_rows.append(build_raw_click_row(parts))
                click_ids.add(bid_id)

    if conv_path.exists():
        for parts in read_tsv_rows(conv_path, desc="Conversions"):
            if len(parts) != RAW_COLUMNS:
                continue
            bid_id = parts[RAW_IDX_BID_ID].strip()
            if bid_id in bid_id_set:
                conv_rows.append(build_raw_conv_row(parts))
                conv_ids.add(bid_id)

    for row in bid_rows:
        bid_id = row["bid_id"]
        row["is_win"] = bid_id in win_ids
        row["is_clicked"] = bid_id in click_ids
        row["is_converted"] = bid_id in conv_ids

    daily_stat_rows = compute_daily_stats(bid_rows)

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


async def import_formalized_format(
    data_dir: Path,
    advertiser: str,
    limit: int,
) -> Dict[str, int]:
    """Import from make-ipinyou-data formalized train/test files."""
    advertiser_dir = data_dir / advertiser
    if not advertiser_dir.is_dir():
        raise FileNotFoundError(f"Advertiser directory not found: {advertiser_dir}")

    train_path = advertiser_dir / "train.log.txt"
    test_path = advertiser_dir / "test.log.txt"

    bid_rows: List[Dict[str, Any]] = []
    imp_rows: List[Dict[str, Any]] = []
    click_rows: List[Dict[str, Any]] = []

    def process_file(path: Path, desc: str) -> None:
        if not path.exists():
            return
        for parts in read_tsv_rows(path, limit=limit, desc=desc, skip_header=True):
            if len(parts) != FORM_COLUMNS:
                continue
            bid_rows.append(build_form_bid_row(parts))
            imp_rows.append(build_form_imp_row(parts))
            if parts[FORM_IDX_CLICK].strip() == "1":
                click_rows.append(build_form_click_row(parts))

    process_file(train_path, "Train")
    remaining = limit - len(bid_rows) if limit is not None else None
    if remaining is None or remaining > 0:
        process_file(test_path, "Test")

    if limit is not None:
        bid_rows = bid_rows[:limit]
        imp_rows = imp_rows[:limit]
        click_rows = [
            c for c in click_rows if c["bid_id"] in {r["bid_id"] for r in bid_rows}
        ]

    daily_stat_rows = compute_daily_stats(bid_rows)

    async with AsyncSessionLocal() as session:
        async with session.begin():
            counts = {
                "bids": await bulk_insert(session, IpinyouBid, bid_rows),
                "impressions": await bulk_insert(session, IpinyouImp, imp_rows),
                "clicks": await bulk_insert(session, IpinyouClick, click_rows),
                "conversions": 0,
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
        help="Path to the dataset root directory.",
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
        help="Maximum number of rows to import (default: 50000).",
    )
    parser.add_argument(
        "--format",
        choices=["raw", "formalized"],
        default="formalized",
        help=(
            "Dataset layout: 'raw' expects bid/imp/click/conv.log.txt; "
            "'formalized' expects advertiser/train.log.txt and test.log.txt "
            "as produced by make-ipinyou-data (default)."
        ),
    )
    args = parser.parse_args()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print(
        f"Importing advertiser {args.advertiser} from {args.data_dir} "
        f"(format={args.format}, limit={args.limit})"
    )

    if args.format == "raw":
        counts = await import_raw_format(args.data_dir, args.advertiser, args.limit)
    else:
        counts = await import_formalized_format(
            args.data_dir, args.advertiser, args.limit
        )

    print("Import complete:")
    for name, count in counts.items():
        print(f"  {name}: {count}")

    await engine.dispose()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
