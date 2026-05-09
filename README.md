# LibTrack API Platform

A minimal Smart Library & Book Inventory Management System API for educational institutes.

## Features

- **Books Management**: CRUD operations with ISBN-based tracking
- **Members Management**: Student/member registration and management
- **Borrow/Return Operations**: Complete borrowing lifecycle with due dates
- **CSV Upload**: Bulk book import from Excel/CSV files
- **Audit Logs**: Complete activity tracking
- **Analytics**: Reading statistics and popular books
- **REST APIs**: Ready for mobile/web integration

## Installation

```bash
pip install -r requirements.txt
```

## Running the Server

```bash
python main.py
```

Server will start on `http://localhost:8000`

## API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.

## Core APIs

### Books Management
- `POST /books` - Add new book
- `GET /books` - List all books
- `GET /books/{id}` - Get book details
- `PUT /books/{id}` - Update book
- `DELETE /books/{id}` - Delete book

### Members Management
- `POST /members` - Register new member
- `GET /members` - List all members
- `GET /members/{id}` - Get member details

### Borrow/Return Operations
- `POST /borrow` - Borrow a book
- `POST /return/{borrow_id}` - Return a book
- `GET /borrow-records` - List all borrow records

### Data Management
- `POST /upload-books` - Upload books via CSV
- `GET /analytics` - Get library statistics
- `GET /audit-logs` - View audit trail

## CSV Upload Format

Required columns: `title`, `author`, `isbn`, `category`
Optional columns: `total_copies`

Example:
```csv
title,author,isbn,category,total_copies
Python Programming,John Doe,978-1234567890,Programming,5
Data Science,Jane Smith,978-0987654321,Technology,3
```

## Database

Uses SQLite database (`library.db`) with the following tables:
- `books` - Book inventory
- `members` - Member information
- `borrow_records` - Borrowing history
- `audit_logs` - Activity tracking

## Key Features

- **Duplicate Prevention**: ISBN and email uniqueness checks
- **Inventory Tracking**: Automatic copy count management
- **Due Date Management**: Configurable borrowing periods
- **Overdue Tracking**: Automatic overdue detection
- **Audit Trail**: Complete operation logging
- **Analytics Dashboard**: Real-time statistics

## Error Handling

- 400: Bad Request (validation errors, duplicates)
- 404: Not Found (book/member not found)
- 500: Internal Server Error

## Future Enhancements

- User authentication
- Email notifications
- Fine management
- Advanced search and filtering
- Mobile app integration
