from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base, SessionLocal
from app.routes import auth, chat, upload
from app.models import User
from app.auth import get_password_hash

# Create FastAPI app
app = FastAPI(title=settings.APP_NAME)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize database tables and demo users on startup"""
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created/verified")
        
        db = SessionLocal()
        try:
            existing_users = db.query(User).count()
            
            if existing_users == 0:
                print("Creating demo users...")
                
                manager = User(
                    full_name="John Manager",
                    email="manager@takeashot.com",
                    password_hash=get_password_hash("password123"),
                    role="manager",
                    is_active=True
                )
                db.add(manager)
                
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
                print("Manager: manager@takeashot.com / password123")
                print("Employee: alex.johnson@takeashot.com / password123")
            else:
                print(f"✅ Database already has {existing_users} users")
                
        finally:
            db.close()
            
    except Exception as e:
        print(f"⚠️ Database initialization error: {e}")

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(upload.router, prefix="/api/upload", tags=["upload"])

@app.get("/")
async def root():
    return {
        "message": "Take a Shot API is running!",
        "status": "healthy",
        "version": "1.0.0"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}