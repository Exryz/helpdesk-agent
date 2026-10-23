"""Mock ticketing system: data model + repository on SQLite (via SQLModel)."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from sqlalchemy import Engine
from sqlmodel import Field, Session, SQLModel, col, create_engine, func, or_, select


class Status(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


class Ticket(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    description: str = ""
    status: Status = Status.OPEN
    priority: Priority = Priority.MEDIUM
    category: str = "General"
    requester: str
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)

    @property
    def key(self) -> str:
        return f"TCK-{self.id}"


class Comment(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    ticket_id: int = Field(foreign_key="ticket.id", index=True)
    author: str
    body: str
    created_at: datetime = Field(default_factory=_now)


class TicketNotFound(LookupError):
    pass


def parse_key(key: str | int) -> int:
    """Accept 'TCK-1003', 'tck-1003', '1003' or 1003."""
    s = str(key).strip().upper().removeprefix("TCK-").removeprefix("TCK")
    if not s.isdigit():
        raise TicketNotFound(f"Invalid ticket key: {key!r}")
    return int(s)


SEED_TICKETS: list[dict[str, str]] = [
    {"title": "Outlook not syncing on laptop", "status": "open", "priority": "high",
     "category": "Email & Collaboration", "requester": "maria.santos",
     "description": "Outlook shows 'Disconnected' and new mail stopped arriving since this morning."},
    {"title": "Request: access to Finance shared drive", "status": "in_progress",
     "priority": "medium", "category": "Accounts & Access", "requester": "john.reyes",
     "description": "Need read/write access to the Finance SharePoint site. Manager approved."},
    {"title": "VPN disconnects every 10 minutes", "status": "open", "priority": "high",
     "category": "Network", "requester": "paul.d",
     "description": "Cisco AnyConnect drops roughly every 10 minutes while working from home."},
    {"title": "Printer on 3rd floor jammed", "status": "resolved", "priority": "low",
     "category": "Hardware", "requester": "ana.cruz",
     "description": "Printer NW-3F-01 shows paper jam in tray 2."},
    {"title": "New hire laptop setup - K. Tan", "status": "in_progress", "priority": "medium",
     "category": "Onboarding & Offboarding", "requester": "hr.team",
     "description": "Prepare laptop and accounts for new hire K. Tan starting Monday."},
    {"title": "MFA phone replaced, need re-enrollment", "status": "open", "priority": "high",
     "category": "Security", "requester": "mark.lim",
     "description": "Got a new phone; Microsoft Authenticator no longer has my account."},
    {"title": "Teams camera not detected", "status": "resolved", "priority": "low",
     "category": "Email & Collaboration", "requester": "liza.garcia",
     "description": "Teams says no camera found, but the camera works in the Camera app."},
    {"title": "Password expired, locked out", "status": "closed", "priority": "medium",
     "category": "Accounts & Access", "requester": "ben.torres",
     "description": "Password expired over the weekend and the account is now locked."},
    {"title": "Software request: Adobe Acrobat Pro", "status": "open", "priority": "low",
     "category": "Software", "requester": "carla.diaz",
     "description": "Need Acrobat Pro to edit and sign vendor contracts."},
    {"title": "Wi-Fi slow in conference room B", "status": "in_progress", "priority": "medium",
     "category": "Network", "requester": "facilities",
     "description": "Video calls in conference room B keep freezing; speed tests show < 5 Mbps."},
]


class TicketRepository:
    """All ticket operations. Used by both the REST API and the MCP server."""

    FIRST_ID = 1001

    def __init__(self, engine: Engine):
        self.engine = engine
        SQLModel.metadata.create_all(engine)

    @classmethod
    def from_path(cls, path: Path | str, seed: bool = True) -> TicketRepository:
        if str(path) == ":memory:":
            from sqlalchemy.pool import StaticPool

            engine = create_engine(
                "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
            )
        else:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
        repo = cls(engine)
        if seed:
            repo.seed_if_empty()
        return repo

    def seed_if_empty(self) -> None:
        with Session(self.engine) as s:
            if s.exec(select(func.count()).select_from(Ticket)).one() > 0:
                return
            for i, data in enumerate(SEED_TICKETS):
                s.add(Ticket(id=self.FIRST_ID + i, **data))  # type: ignore[arg-type]
            s.commit()

    # ---- queries -------------------------------------------------------------------------
    def get(self, key: str | int) -> Ticket:
        with Session(self.engine) as s:
            ticket = s.get(Ticket, parse_key(key))
            if ticket is None:
                raise TicketNotFound(f"Ticket {key} not found")
            return ticket

    def comments(self, key: str | int) -> list[Comment]:
        tid = self.get(key).id
        with Session(self.engine) as s:
            stmt = select(Comment).where(Comment.ticket_id == tid).order_by(col(Comment.id))
            return list(s.exec(stmt).all())

    def search(
        self,
        query: str | None = None,
        status: Status | str | None = None,
        requester: str | None = None,
        limit: int = 10,
    ) -> list[Ticket]:
        with Session(self.engine) as s:
            stmt = select(Ticket)
            if query:
                for word in query.split():
                    like = f"%{word}%"
                    stmt = stmt.where(
                        or_(col(Ticket.title).ilike(like), col(Ticket.description).ilike(like))
                    )
            if status:
                stmt = stmt.where(Ticket.status == Status(status))
            if requester:
                stmt = stmt.where(col(Ticket.requester).ilike(requester))
            stmt = stmt.order_by(col(Ticket.updated_at).desc(), col(Ticket.id).desc()).limit(limit)
            return list(s.exec(stmt).all())

    # ---- mutations -----------------------------------------------------------------------
    def create(
        self,
        title: str,
        description: str,
        requester: str,
        priority: Priority | str = Priority.MEDIUM,
        category: str = "General",
    ) -> Ticket:
        if not title.strip():
            raise ValueError("title is required")
        with Session(self.engine) as s:
            ticket = Ticket(
                title=title.strip(),
                description=description.strip(),
                requester=requester.strip() or "unknown",
                priority=Priority(priority),
                category=category,
            )
            max_id = s.exec(select(func.max(Ticket.id))).one()
            ticket.id = max(int(max_id or 0) + 1, self.FIRST_ID)
            s.add(ticket)
            s.commit()
            s.refresh(ticket)
            return ticket

    def add_comment(self, key: str | int, body: str, author: str = "helpdesk-agent") -> Comment:
        if not body.strip():
            raise ValueError("comment body is required")
        with Session(self.engine) as s:
            ticket = s.get(Ticket, parse_key(key))
            if ticket is None:
                raise TicketNotFound(f"Ticket {key} not found")
            assert ticket.id is not None
            comment = Comment(ticket_id=ticket.id, author=author, body=body.strip())
            ticket.updated_at = _now()
            s.add(comment)
            s.add(ticket)
            s.commit()
            s.refresh(comment)
            return comment

    def update_status(self, key: str | int, status: Status | str, note: str | None = None) -> Ticket:
        new_status = Status(status)
        with Session(self.engine) as s:
            ticket = s.get(Ticket, parse_key(key))
            if ticket is None:
                raise TicketNotFound(f"Ticket {key} not found")
            old = ticket.status
            ticket.status = new_status
            ticket.updated_at = _now()
            s.add(ticket)
            assert ticket.id is not None
            body = f"Status changed {old} -> {new_status}." + (f" {note}" if note else "")
            s.add(Comment(ticket_id=ticket.id, author="helpdesk-agent", body=body))
            s.commit()
            s.refresh(ticket)
            return ticket


def ticket_to_dict(t: Ticket) -> dict[str, object]:
    return {
        "key": t.key,
        "title": t.title,
        "description": t.description,
        "status": str(t.status),
        "priority": str(t.priority),
        "category": t.category,
        "requester": t.requester,
        "created_at": t.created_at.isoformat(),
        "updated_at": t.updated_at.isoformat(),
    }


def comment_to_dict(c: Comment) -> dict[str, object]:
    return {"author": c.author, "body": c.body, "created_at": c.created_at.isoformat()}
