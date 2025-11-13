from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Message
from app.config import settings
from datetime import datetime
import cloudinary
import cloudinary.uploader
import os

router = APIRouter()

# Configure Cloudinary if credentials are available
if settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY:
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET
    )
    USE_CLOUDINARY = True
    print(f"✅ Cloudinary configured: {settings.CLOUDINARY_CLOUD_NAME}")
else:
    USE_CLOUDINARY = False
    # Fallback to local storage
    UPLOAD_DIR = settings.UPLOAD_DIR
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR, exist_ok=True)
    print("⚠️ Cloudinary not configured, using local storage")

@router.post("/file")
async def upload_file(
    file: UploadFile = File(...),
    user_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """Upload a file (uses Cloudinary in production, local storage in development)"""
    try:
        print(f"📤 Uploading file: {file.filename} (Use Cloudinary: {USE_CLOUDINARY})")
        
        if USE_CLOUDINARY:
            # Upload to Cloudinary
            print("☁️ Uploading to Cloudinary...")
            result = cloudinary.uploader.upload(
                file.file,
                folder="takeashot",
                resource_type="auto"
            )
            file_url = result['secure_url']
            file_path = file_url
            print(f"✅ Uploaded to Cloudinary: {file_url}")
            
        else:
            # Fallback: Local storage (for development)
            print("💾 Saving to local storage...")
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            file_url = f"/uploads/{file.filename}"
            print(f"✅ Saved locally: {file_path}")
        
        # Create notification message with file
        message = Message(
            sender_id=user_id,
            receiver_id=None,  # AI receives it
            content=f"📎 File uploaded: {file.filename}",
            file_path=file_url
        )
        
        db.add(message)
        db.commit()
        
        print(f"✅ Upload complete!")
        
        return {
            "success": True,
            "filename": file.filename,
            "file_url": file_url,
            "message": "File uploaded successfully!"
        }
        
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")