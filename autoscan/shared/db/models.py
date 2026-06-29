from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    JSON,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    github_org: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String)
    website: Mapped[Optional[str]] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(String)
    employee_count: Mapped[Optional[int]] = mapped_column(Integer)
    funding_status: Mapped[Optional[str]] = mapped_column(String)
    qualification_score: Mapped[Optional[float]] = mapped_column(Float)
    enrichment_score: Mapped[Optional[float]] = mapped_column(Float)
    tech_stack: Mapped[Optional[list]] = mapped_column(JSON)
    status: Mapped[Optional[str]] = mapped_column(String, default="NEW")
    
    impact_score: Mapped[Optional[float]] = mapped_column(Float)
    estimated_risk_min_usd: Mapped[Optional[float]] = mapped_column(Float)
    estimated_risk_max_usd: Mapped[Optional[float]] = mapped_column(Float)
    report_price_cents: Mapped[Optional[int]] = mapped_column(Integer)
    report_tier: Mapped[Optional[str]] = mapped_column(String)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    repositories: Mapped[List["Repository"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    contacts: Mapped[List["Contact"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )

class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    name: Mapped[str] = mapped_column(String)
    full_name: Mapped[str] = mapped_column(String, unique=True, index=True)
    language: Mapped[Optional[str]] = mapped_column(String)
    stars: Mapped[int] = mapped_column(Integer, default=0)
    last_commit_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_fork: Mapped[bool] = mapped_column(Boolean, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    topics: Mapped[Optional[list]] = mapped_column(JSON)
    clone_url: Mapped[Optional[str]] = mapped_column(String)
    local_path: Mapped[Optional[str]] = mapped_column(String)
    file_count: Mapped[Optional[int]] = mapped_column(Integer)
    size_mb: Mapped[Optional[float]] = mapped_column(Float)
    languages_inventory: Mapped[Optional[dict]] = mapped_column(JSON)
    has_secrets_risk: Mapped[Optional[bool]] = mapped_column(Boolean)
    status: Mapped[Optional[str]] = mapped_column(String, default="NEW")
    finding_count: Mapped[int] = mapped_column(Integer, default=0)
    last_scanned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


    company: Mapped["Company"] = relationship(back_populates="repositories")
    findings: Mapped[List["Finding"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )

class Finding(Base):
    __tablename__ = "findings"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), index=True)
    type: Mapped[str] = mapped_column(String, index=True)
    severity: Mapped[str] = mapped_column(String, index=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(String)
    file_path: Mapped[Optional[str]] = mapped_column(String)
    line_no: Mapped[Optional[int]] = mapped_column(Integer)
    scanner_name: Mapped[str] = mapped_column(String)
    confidence: Mapped[Optional[str]] = mapped_column(String)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON)
    verified: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    is_false_positive: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    ai_explanation: Mapped[Optional[str]] = mapped_column(String)
    ai_recommendation: Mapped[Optional[str]] = mapped_column(String)
    verified_severity: Mapped[Optional[str]] = mapped_column(String)
    fix_hours_estimate: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    repository: Mapped["Repository"] = relationship(back_populates="findings")

class DiscoveryState(Base):
    __tablename__ = "discovery_state"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    language: Mapped[str] = mapped_column(String, unique=True, index=True)
    last_cursor: Mapped[Optional[str]] = mapped_column(String)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

class Report(Base):
    __tablename__ = "reports"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    full_report_path: Mapped[Optional[str]] = mapped_column(String)
    teaser_report_path: Mapped[Optional[str]] = mapped_column(String)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    company: Mapped["Company"] = relationship()

class Contact(Base):
    __tablename__ = "contacts"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    email: Mapped[str] = mapped_column(String, index=True)
    first_name: Mapped[Optional[str]] = mapped_column(String)
    last_name: Mapped[Optional[str]] = mapped_column(String)
    position: Mapped[Optional[str]] = mapped_column(String)
    score: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    source: Mapped[Optional[str]] = mapped_column(String)
    is_verified: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    company: Mapped["Company"] = relationship(back_populates="contacts")

class Email(Base):
    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"), index=True)
    subject: Mapped[str] = mapped_column(String)
    html_body: Mapped[str] = mapped_column(String)
    text_body: Mapped[str] = mapped_column(String)
    sequence_num: Mapped[int] = mapped_column(Integer, default=1)
    checkout_session_id: Mapped[Optional[str]] = mapped_column(String)
    
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    clicked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    company: Mapped["Company"] = relationship()
    contact: Mapped["Contact"] = relationship()
    events: Mapped[List["EmailEvent"]] = relationship(
        back_populates="email", cascade="all, delete-orphan"
    )

class EmailEvent(Base):
    __tablename__ = "email_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email_id: Mapped[int] = mapped_column(ForeignKey("emails.id"), index=True)
    event_type: Mapped[str] = mapped_column(String, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String)
    user_agent: Mapped[Optional[str]] = mapped_column(String)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    email: Mapped["Email"] = relationship(back_populates="events")

class Payment(Base):
    __tablename__ = "payments"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"), index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    contact_id: Mapped[Optional[int]] = mapped_column(ForeignKey("contacts.id"))
    stripe_session_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(String, index=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String, default="pending")
    access_revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    report: Mapped["Report"] = relationship()
    company: Mapped["Company"] = relationship()
    contact: Mapped["Contact"] = relationship()
