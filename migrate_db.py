import os
from flask import Flask
from sqlalchemy import text
from app import create_app
from extensions import db
from models import FeeCollection

app = create_app()

with app.app_context():
    # 1. Add the new column to the database (if it doesn't exist)
    # Note: SQLite uses different syntax than PostgreSQL sometimes, but ADD COLUMN is generally supported.
    try:
        db.session.execute(text('ALTER TABLE fee_collection ADD COLUMN fee_month VARCHAR(7)'))
        db.session.commit()
        print("Column 'fee_month' added successfully.")
    except Exception as e:
        db.session.rollback()
        print(f"Column might already exist or error occurred: {e}")

    # 2. Backfill existing records
    fees = FeeCollection.query.all()
    updated_count = 0
    for fee in fees:
        if not fee.fee_month and fee.date_collected:
            # Format: YYYY-MM
            fee.fee_month = fee.date_collected.strftime('%Y-%m')
            updated_count += 1
            
    if updated_count > 0:
        db.session.commit()
        print(f"Successfully backfilled 'fee_month' for {updated_count} records.")
    else:
        print("No records needed backfilling.")

print("Migration complete!")
