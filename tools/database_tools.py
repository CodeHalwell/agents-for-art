from smolagents import tool
from decimal import Decimal
from sqlalchemy import inspect

from models.db import DatabaseManager

db = DatabaseManager()

# ───────────────────────────── URL ──────────────────────────────
@tool
def add_url(
    url: str,
    raw_title: str | None = None,
    raw_date: str | None = None,
    raw_location: str | None = None,
    raw_description: str | None = None,
) -> int:
    """Insert a row in the **urls** table and return its ID.

    Args:
        url: The absolute URL of the page that advertised the open call.
        raw_title: Optional raw title text scraped from the page.
        raw_date: Optional raw date string scraped from the page.
        raw_location: Optional raw location string scraped from the page.
        raw_description: Optional teaser / summary text scraped from the page.

    Returns:
        The primary‑key ID of the newly‑inserted :class:`models.Url` row.
        This ID should be stored in ``url_id`` when creating related
        :class:`models.Exhibition` rows.
    """
    return db.add_url(
        url=url,
        raw_title=raw_title,
        raw_date=raw_date,
        raw_location=raw_location,
        raw_description=raw_description,
    ).id


# ─────────────────────────── EXHIBITION ─────────────────────────
@tool
def add_exhibition(
    *,
    title: str,
    date_start: str,  # YYYY-MM-DD
    date_end: str,    # YYYY-MM-DD
    venue: str,
    location: str,
    county: str | None,
    url_id: int,
    description: str | None = None,
) -> int:
    """Insert a row in the **exhibitions** table.

    Args:
        title: Official exhibition title.
        date_start: First public day of the exhibition (YYYY‑MM‑DD).
        date_end: Last public day of the exhibition (YYYY‑MM‑DD).
        venue: Gallery / art‑fair name.
        location: Town or city where the venue is located.
        county: Optional county / region for more granular search.
        url_id: Foreign‑key linking back to the **urls** table (output of
            :pyfunc:`add_url`).
        description: Optional long‑form description scraped from the page.

    Returns:
        The ID of the new :class:`models.Exhibition` row.
    """
    from datetime import date

    kw = dict(
        title=title,
        date_start=date.fromisoformat(date_start),
        date_end=date.fromisoformat(date_end),
        venue=venue,
        location=location,
        county=county,
        url_id=url_id,
        description=description,
    )
    return db.add_exhibition(**kw).id


# ─────────────────────────── ENTRY FEE ──────────────────────────
@tool
def add_entry_fee(
    exhibition_id: int,
    number_entries: int,
    fee_amount: str,
    flat_rate: str | None = None,
    commission_percent: str | None = None,
) -> int:
    """Insert a row in the **entry_fees** table.

    Args:
        exhibition_id: Foreign‑key to the parent exhibition.
        number_entries: The *exact* number of works this tier applies to. Use
            ``1`` for "first piece", ``2`` for "two pieces", etc.
        fee_amount: Monetary fee *per tier* (e.g. "25.00").
        flat_rate: Optional flat fee that overrides per‑piece tiers.
        commission_percent: Optional commission percentage charged on sales.

    Returns:
        The ID of the new :class:`models.EntryFee` row.
    """
    return db.add_entry_fee(
        exhibition_id=exhibition_id,
        number_entries=number_entries,
        fee_amount=Decimal(fee_amount),
        flat_rate=Decimal(flat_rate) if flat_rate else None,
        commission_percent=Decimal(commission_percent) if commission_percent else None,
    ).id


# ───────────────────────────── PRIZE ────────────────────────────
@tool
def add_prize(
    exhibition_id: int,
    prize_rank: int | None = None,
    prize_amount: str | None = None,
    prize_type: str | None = None,
    prize_description: str | None = None,
) -> int:
    """Insert a row in the **prizes** table.

    Args:
        exhibition_id: Foreign‑key to the parent exhibition.
        prize_rank: Ordinal rank (e.g. 1 for first prize).  ``None`` if the
            prize isn’t ranked.
        prize_amount: Cash value ("5000.00") or ``None`` for non‑cash awards.
        prize_type: Short label for the prize type (e.g. "cash", "materials").
        prize_description: Longer human‑readable description.

    Returns:
        The ID of the new :class:`models.Prize` row.
    """
    amt = Decimal(prize_amount) if prize_amount else None
    return db.add_prize(
        exhibition_id=exhibition_id,
        prize_rank=prize_rank,
        prize_amount=amt,
        prize_type=prize_type,
        prize_description=prize_description,
    ).id

@tool
def describe_schema(table_name: str) -> str:
    """
    Return the column names and types for the given table.

    Args:
        table_name: Name of the table in art_events.db ("exhibitions", "entry_fees", "prizes", "urls").

    Returns:
        A human-readable list of columns and their SQL types.
    """
    bind = db.session.bind
    if bind is None:
        return "ERROR: Database connection is not available"
    
    insp = inspect(bind)
    if table_name not in insp.get_table_names():
        return f"ERROR: no table named '{table_name}'. Available: {insp.get_table_names()}"
    cols = insp.get_columns(table_name)
    lines = [f"{c['name']}: {c['type']}" for c in cols]
    return "\n".join(lines)