from app.database import engine, Base, SessionLocal
from app.models import User, UserRole
from app.auth import get_password_hash
from datetime import datetime

def init_database():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully")
    
    db = SessionLocal()
    
    try:
        existing_users = db.query(User).count()
        if existing_users > 0:
            print(f"⚠️  Database already has {existing_users} users. Skipping initialization.")
            return
        
        print("\nCreating sample users...")
        
        default_password = "password123"
        
        manager = User(
            full_name="John Manager",
            email="manager@takeashot.com",
            password_hash=get_password_hash(default_password),
            role=UserRole.MANAGER,
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(manager)
        
        employees = [
            User(
                full_name="Alex Johnson",
                email="alex.johnson@takeashot.com",
                password_hash=get_password_hash(default_password),
                role=UserRole.EMPLOYEE,
                is_active=True,
                created_at=datetime.utcnow()
            ),
            User(
                full_name="Sarah Chen",
                email="sarah.chen@takeashot.com",
                password_hash=get_password_hash(default_password),
                role=UserRole.EMPLOYEE,
                is_active=True,
                created_at=datetime.utcnow()
            ),
        ]
        
        for employee in employees:
            db.add(employee)
        
        db.commit()
        
        print("✅ Sample users created successfully!\n")
        print("="*60)
        print("DEMO LOGIN CREDENTIALS")
        print("="*60)
        print("\n📋 MANAGER:")
        print("   Email: manager@takeashot.com")
        print("   Password: password123")
        print("\n👤 EMPLOYEES:")
        print("   Email: alex.johnson@takeashot.com")
        print("   Password: password123")
        print("\n   Email: sarah.chen@takeashot.com")
        print("   Password: password123")
        print("\n" + "="*60)
        print("🚀 Database initialization complete!")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_database()