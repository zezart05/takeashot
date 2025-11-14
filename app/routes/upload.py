from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Message
from app.config import settings
import cloudinary
import cloudinary.uploader
import os

router = APIRouter()

if settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY:
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET
    )
    USE_CLOUDINARY = True
else:
    USE_CLOUDINARY = False
    UPLOAD_DIR = settings.UPLOAD_DIR
    os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/file")
async def upload_file(
    file: UploadFile = File(...),
    user_id: int = Form(...),
    db: Session = Depends(get_db)
):
    try:
        original_filename = file.filename
        
        if USE_CLOUDINARY:
            result = cloudinary.uploader.upload(
                file.file,
                folder="takeashot",
                resource_type="auto",
                use_filename=True,
                unique_filename=True
            )
            file_url = result['secure_url']
        else:
            file_path = os.path.join(UPLOAD_DIR, original_filename)
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            file_url = f"/uploads/{original_filename}"
        
        message = Message(
            sender_id=user_id,
            receiver_id=None,
            content=f"📎 {original_filename}",
            file_path=file_url
        )
        db.add(message)
        db.commit()
        
        return {
            "success": True,
            "filename": original_filename,
            "file_url": file_url
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))