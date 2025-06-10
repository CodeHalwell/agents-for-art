from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from .models import Base, Url, Exhibition, EntryFee, Prize


class DatabaseManager:
    """
    One engine + one Session.  No DeclarativeBase inheritance.
    """
    def __init__(self, db_path: str = "art_events.db") -> None:
        engine = create_engine(f"sqlite:///{db_path}", future=True)
        Base.metadata.create_all(engine)
        self.session: Session = Session(engine)

    # ───── CRUD helpers ────────────────────────────────────────────────
    def add_url(self, **kw) -> Url:
        row = Url(**kw)
        self.session.add(row)
        self.session.commit()
        return row

    def add_exhibition(self, **kw) -> Exhibition:
        row = Exhibition(**kw)
        self.session.add(row)
        self.session.commit()
        return row

    def add_entry_fee(self, **kw) -> EntryFee:
        row = EntryFee(**kw)
        self.session.add(row)
        self.session.commit()
        return row

    def add_prize(self, **kw) -> Prize:
        row = Prize(**kw)
        self.session.add(row)
        self.session.commit()
        return row
