"""
Script to recreate the database with the updated schema including JWT support.
This will create a fresh database with the enrolled_modules column.
"""
from app.database import engine
from app.models import Base

print("Dropping all tables...")
Base.metadata.drop_all(bind=engine)

print("Creating all tables with updated schema...")
Base.metadata.create_all(bind=engine)

print("Database recreated successfully!")
print("\nThe database now includes:")
print("- Hashed password support")
print("- enrolled_modules column")
print("- All other user fields")
