from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Text, DateTime, ForeignKey, JSON, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from config.settings import DB_PATH

class Base(DeclarativeBase): pass
class Investigation(Base):
    __tablename__='investigations'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    title:Mapped[str]=mapped_column(String(200))
    description:Mapped[str]=mapped_column(Text,default='')
    category:Mapped[str]=mapped_column(String(80),default='General')
    status:Mapped[str]=mapped_column(String(40),default='In progress')
    created_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc))
    documents:Mapped[list['Document']]=relationship(back_populates='investigation',cascade='all, delete-orphan')
    findings:Mapped[list['Finding']]=relationship(back_populates='investigation',cascade='all, delete-orphan')
    events:Mapped[list['AuditEvent']]=relationship(back_populates='investigation',cascade='all, delete-orphan')
class Document(Base):
    __tablename__='documents'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    investigation_id:Mapped[str]=mapped_column(ForeignKey('investigations.id',ondelete='CASCADE'),index=True)
    name:Mapped[str]=mapped_column(String(255)); path:Mapped[str]=mapped_column(Text); sha256:Mapped[str]=mapped_column(String(64))
    mime_type:Mapped[str]=mapped_column(String(80)); text:Mapped[str]=mapped_column(Text,default=''); fields:Mapped[dict]=mapped_column(JSON,default=dict)
    doc_type:Mapped[str]=mapped_column(String(80),default='Other / Unknown'); classification_confidence:Mapped[float]=mapped_column(default=0)
    page_count:Mapped[int]=mapped_column(Integer,default=1); status:Mapped[str]=mapped_column(String(40),default='Processed')
    investigation:Mapped[Investigation]=relationship(back_populates='documents')
class Finding(Base):
    __tablename__='findings'
    id:Mapped[str]=mapped_column(String,primary_key=True); investigation_id:Mapped[str]=mapped_column(ForeignKey('investigations.id',ondelete='CASCADE'),index=True)
    category:Mapped[str]=mapped_column(String(80)); severity:Mapped[str]=mapped_column(String(40)); title:Mapped[str]=mapped_column(String(255)); description:Mapped[str]=mapped_column(Text)
    evidence:Mapped[dict]=mapped_column(JSON,default=dict); status:Mapped[str]=mapped_column(String(40),default='Needs review'); reviewer_note:Mapped[str]=mapped_column(Text,default='')
    investigation:Mapped[Investigation]=relationship(back_populates='findings')
class AuditEvent(Base):
    __tablename__='audit_events'
    id:Mapped[str]=mapped_column(String,primary_key=True); investigation_id:Mapped[str]=mapped_column(ForeignKey('investigations.id',ondelete='CASCADE'),index=True)
    event_type:Mapped[str]=mapped_column(String(80)); description:Mapped[str]=mapped_column(Text); created_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc))
    investigation:Mapped[Investigation]=relationship(back_populates='events')

engine=create_engine(f'sqlite:///{DB_PATH.as_posix()}',connect_args={'check_same_thread':False})
Base.metadata.create_all(engine)
Session=sessionmaker(engine,expire_on_commit=False)

def audit(db, investigation_id, event_type, description):
    import uuid
    db.add(AuditEvent(id=str(uuid.uuid4()),investigation_id=investigation_id,event_type=event_type,description=description)); db.commit()
