from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import List, Optional
import csv
import io
import uuid

app = FastAPI(title="LibTrack API Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = "sqlite:///./library.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Book(Base):
    __tablename__ = "books"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    isbn = Column(String, unique=True, nullable=False)
    category = Column(String, nullable=False)
    total_copies = Column(Integer, default=1)
    available_copies = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    borrow_records = relationship("BorrowRecord", back_populates="book")

class Member(Base):
    __tablename__ = "members"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, nullable=False)
    membership_date = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    borrow_records = relationship("BorrowRecord", back_populates="member")

class BorrowRecord(Base):
    __tablename__ = "borrow_records"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    book_id = Column(String, ForeignKey("books.id"), nullable=False)
    member_id = Column(String, ForeignKey("members.id"), nullable=False)
    borrow_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=False)
    return_date = Column(DateTime, nullable=True)
    status = Column(String, default="borrowed")  # borrowed, returned, overdue
    
    book = relationship("Book", back_populates="borrow_records")
    member = relationship("Member", back_populates="borrow_records")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    user_id = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(Text, nullable=True)

Base.metadata.create_all(bind=engine)

# Pydantic Models
class BookCreate(BaseModel):
    title: str
    author: str
    isbn: str
    category: str
    total_copies: int = 1

class BookResponse(BaseModel):
    id: str
    title: str
    author: str
    isbn: str
    category: str
    total_copies: int
    available_copies: int
    created_at: datetime

class MemberCreate(BaseModel):
    name: str
    email: str
    phone: str

class MemberResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    membership_date: datetime
    is_active: bool

class BorrowCreate(BaseModel):
    book_id: str
    member_id: str
    days: int = 14

class BorrowResponse(BaseModel):
    id: str
    book_id: str
    member_id: str
    borrow_date: datetime
    due_date: datetime
    return_date: Optional[datetime]
    status: str

# API Endpoints
@app.get("/")
def root():
    return {"message": "LibTrack API Platform - Smart Library Management System"}

@app.post("/books", response_model=BookResponse)
def create_book(book: BookCreate, db: Session = Depends(get_db)):
    existing_book = db.query(Book).filter(Book.isbn == book.isbn).first()
    if existing_book:
        raise HTTPException(status_code=400, detail="Book with this ISBN already exists")
    
    db_book = Book(**book.dict())
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    
    # Log audit
    audit = AuditLog(
        action="CREATE",
        entity_type="BOOK",
        entity_id=db_book.id,
        details=f"Created book: {book.title}"
    )
    db.add(audit)
    db.commit()
    
    return db_book

@app.get("/books", response_model=List[BookResponse])
def get_books(db: Session = Depends(get_db)):
    return db.query(Book).all()

@app.get("/books/{book_id}", response_model=BookResponse)
def get_book(book_id: str, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@app.put("/books/{book_id}", response_model=BookResponse)
def update_book(book_id: str, book: BookCreate, db: Session = Depends(get_db)):
    db_book = db.query(Book).filter(Book.id == book_id).first()
    if not db_book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    for key, value in book.dict().items():
        setattr(db_book, key, value)
    
    db.commit()
    db.refresh(db_book)
    
    # Log audit
    audit = AuditLog(
        action="UPDATE",
        entity_type="BOOK",
        entity_id=book_id,
        details=f"Updated book: {book.title}"
    )
    db.add(audit)
    db.commit()
    
    return db_book

@app.delete("/books/{book_id}")
def delete_book(book_id: str, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    db.delete(book)
    db.commit()
    
    # Log audit
    audit = AuditLog(
        action="DELETE",
        entity_type="BOOK",
        entity_id=book_id,
        details=f"Deleted book: {book.title}"
    )
    db.add(audit)
    db.commit()
    
    return {"message": "Book deleted successfully"}

@app.post("/members", response_model=MemberResponse)
def create_member(member: MemberCreate, db: Session = Depends(get_db)):
    existing_member = db.query(Member).filter(Member.email == member.email).first()
    if existing_member:
        raise HTTPException(status_code=400, detail="Member with this email already exists")
    
    db_member = Member(**member.dict())
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    
    # Log audit
    audit = AuditLog(
        action="CREATE",
        entity_type="MEMBER",
        entity_id=db_member.id,
        details=f"Created member: {member.name}"
    )
    db.add(audit)
    db.commit()
    
    return db_member

@app.get("/members", response_model=List[MemberResponse])
def get_members(db: Session = Depends(get_db)):
    return db.query(Member).all()

@app.get("/members/{member_id}", response_model=MemberResponse)
def get_member(member_id: str, db: Session = Depends(get_db)):
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member

@app.post("/borrow", response_model=BorrowResponse)
def borrow_book(borrow: BorrowCreate, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == borrow.book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    if book.available_copies <= 0:
        raise HTTPException(status_code=400, detail="No copies available")
    
    member = db.query(Member).filter(Member.id == borrow.member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    if not member.is_active:
        raise HTTPException(status_code=400, detail="Member is not active")
    
    # Check if member already has this book
    existing_borrow = db.query(BorrowRecord).filter(
        BorrowRecord.book_id == borrow.book_id,
        BorrowRecord.member_id == borrow.member_id,
        BorrowRecord.status == "borrowed"
    ).first()
    
    if existing_borrow:
        raise HTTPException(status_code=400, detail="Member already has this book")
    
    borrow_record = BorrowRecord(
        book_id=borrow.book_id,
        member_id=borrow.member_id,
        due_date=datetime.utcnow() + timedelta(days=borrow.days)
    )
    
    book.available_copies -= 1
    
    db.add(borrow_record)
    db.commit()
    db.refresh(borrow_record)
    
    # Log audit
    audit = AuditLog(
        action="BORROW",
        entity_type="BOOK",
        entity_id=borrow.book_id,
        details=f"Book borrowed by member: {member.name}"
    )
    db.add(audit)
    db.commit()
    
    return borrow_record

@app.post("/return/{borrow_id}")
def return_book(borrow_id: str, db: Session = Depends(get_db)):
    borrow_record = db.query(BorrowRecord).filter(BorrowRecord.id == borrow_id).first()
    if not borrow_record:
        raise HTTPException(status_code=404, detail="Borrow record not found")
    
    if borrow_record.status != "borrowed":
        raise HTTPException(status_code=400, detail="Book already returned")
    
    borrow_record.return_date = datetime.utcnow()
    borrow_record.status = "returned"
    
    book = db.query(Book).filter(Book.id == borrow_record.book_id).first()
    book.available_copies += 1
    
    db.commit()
    
    # Log audit
    audit = AuditLog(
        action="RETURN",
        entity_type="BOOK",
        entity_id=borrow_record.book_id,
        details=f"Book returned by member"
    )
    db.add(audit)
    db.commit()
    
    return {"message": "Book returned successfully"}

@app.get("/borrow-records", response_model=List[BorrowResponse])
def get_borrow_records(db: Session = Depends(get_db)):
    return db.query(BorrowRecord).all()

@app.post("/upload-books")
async def upload_books(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    contents = await file.read()
    csv_file = io.StringIO(contents.decode('utf-8'))
    reader = csv.DictReader(csv_file)
    
    required_columns = ['title', 'author', 'isbn', 'category']
    if not all(col in reader.fieldnames for col in required_columns):
        raise HTTPException(status_code=400, detail=f"CSV must contain columns: {required_columns}")
    
    created_count = 0
    skipped_count = 0
    
    for row in reader:
        existing_book = db.query(Book).filter(Book.isbn == row['isbn']).first()
        if existing_book:
            skipped_count += 1
            continue
        
        book = Book(
            title=row['title'],
            author=row['author'],
            isbn=row['isbn'],
            category=row['category'],
            total_copies=int(row.get('total_copies', 1)),
            available_copies=int(row.get('total_copies', 1))
        )
        db.add(book)
        created_count += 1
    
    db.commit()
    
    return {
        "message": f"Upload completed. Created: {created_count}, Skipped (duplicates): {skipped_count}"
    }

@app.get("/analytics")
def get_analytics(db: Session = Depends(get_db)):
    total_books = db.query(Book).count()
    total_members = db.query(Member).count()
    total_borrowed = db.query(BorrowRecord).filter(BorrowRecord.status == "borrowed").count()
    overdue_books = db.query(BorrowRecord).filter(
        BorrowRecord.status == "borrowed",
        BorrowRecord.due_date < datetime.utcnow()
    ).count()
    
    # Most popular books
    popular_books = db.query(BorrowRecord.book_id, Book.title).join(Book).group_by(
        BorrowRecord.book_id, Book.title
    ).order_by(db.func.count(BorrowRecord.id).desc()).limit(5).all()
    
    return {
        "total_books": total_books,
        "total_members": total_members,
        "currently_borrowed": total_borrowed,
        "overdue_books": overdue_books,
        "popular_books": [{"book_id": book_id, "title": title} for book_id, title in popular_books]
    }

@app.get("/audit-logs")
def get_audit_logs(db: Session = Depends(get_db)):
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100).all()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
