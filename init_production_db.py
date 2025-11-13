import os
import sys
from sqlalchemy import create_engine
from app.database import Base
from app.models import User
from app.auth import get_password_hash
from sqlalchemy.orm import sessionmaker

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("Error: DATABASE_URL environment variable not set")
    sys.exit(1)

# Fix PostgreSQL URL if needed (Render uses postgres:// but SQLAlchemy needs postgresql://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print(f"Connecting to database...")

# Create engine
engine = create_engine(DATABASE_URL)

# Create all tables
print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("✅ Tables created!")

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

try:
    # Check if users already exist
    existing_users = db.query(User).count()
    
    if existing_users > 0:
        print(f"✅ Database already has {existing_users} users. Skipping initialization.")
    else:
        print("Creating demo users...")
        
        # Create manager
        manager = User(
            full_name="John Manager",
            email="manager@takeashot.com",
            password_hash=get_password_hash("password123"),
            role="manager",
            is_active=True
        )
        db.add(manager)
        
        # Create employee
        employee = User(
            full_name="Alex Johnson",
            email="alex.johnson@takeashot.com",
            password_hash=get_password_hash("password123"),
            role="employee",
            is_active=True
        )
        db.add(employee)
        
        db.commit()
        print("✅ Demo users created!")
        print("\nLogin credentials:")
        print("Manager: manager@takeashot.com / password123")
        print("Employee: alex.johnson@takeashot.com / password123")
        
except Exception as e:
    print(f"❌ Error: {e}")
    db.rollback()
finally:
    db.close()

print("\n🎉 Database initialization complete!")