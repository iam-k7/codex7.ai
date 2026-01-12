import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

import uuid
import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

# AI and Analytics Services
from ai_service import generate_ai_captions, export_video_render
from sheets_service import SheetsDB, JSONDB
from services.analytics import analytics
from fastapi.responses import FileResponse, StreamingResponse
import json

app = FastAPI(title="codex7.ai API")

class UserFeedback(BaseModel):
    user_id: str
    rating: int
    message: Optional[str] = ""
    feature: Optional[str] = "Editor"
    language_pref: Optional[str] = "en"

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

db = SheetsDB()
local_db = JSONDB()

class UserLogin(BaseModel):
    name: str
    email: str
    country: str

# Old login implementation replaced by Google Sheets version below

@app.post("/api/generate-captions")
async def process_video(
    video: UploadFile = File(...),
    email: str = Form(...),
    language: str = Form("en")
):
    # 1. Validation: Limit file size to 50MB (roughly 1-2 mins of high HQ video)
    MAX_SIZE = 50 * 1024 * 1024
    content = await video.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Max 50MB allowed.")
    await video.seek(0) # Reset pointer after reading

    # 2. Save video temporarily
    temp_path = f"temp_{uuid.uuid4()}_{video.filename}" # unique name to prevent collisions
    with open(temp_path, "wb") as f:
        f.write(content)
    
    try:
        # 3. Extract audio & Transcribe & AI process
        result = await generate_ai_captions(temp_path, language)
        
        # 4. Log Analytics (Async)
        await analytics.log_event("CAPTION_GENERATE", {
            "user_id": email,
            "user_query": video.filename,
            "detected_language": f"{result.get('language', 'unknown')} ({result.get('language_probability', 0):.2f})",
            "error_log": result.get("status")
        })
        
        # 5. Clean up
        os.remove(temp_path)
        
        return result
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        # Log Failure
        await analytics.log_event("CAPTION_FAILURE", {
            "user_id": email,
            "user_query": video.filename,
            "error_log": str(e)
        })
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history")
async def get_history(email: str):
    user = db.get_user_by_email(email)
    if not user:
        return []
    
    history = db.get_user_history(user["user_id"])
    return history

@app.post("/api/save-history")
async def save_history(
    email: str = Form(...),
    video_name: str = Form(...),
    caption_text: str = Form(...),
    font: str = Form(...),
    size: str = Form(...),
    color: str = Form(...),
    position: str = Form(...)
):
    user = db.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    db.save_history({
        "user_id": user["user_id"],
        "video_name": video_name,
        "caption_text": caption_text,
        "font": font,
        "size": size,
        "color": color,
        "position": position,
        "timestamp": datetime.datetime.now().isoformat()
    })
    
    local_db.save_history({
        "user_id": user["user_id"],
        "email": email,
        "video_name": video_name,
        "caption_text": caption_text,
        "font": font,
        "size": size,
        "color": color,
        "position": position,
        "timestamp": datetime.datetime.now().isoformat()
    })
    return {"status": "success"}

@app.post("/api/export-video")
async def export_video(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    segments: str = Form(...),
    styles: str = Form(...)
):
    """
    Renders and exports the final video with burned-in captions.
    """
    temp_in = f"export_in_{uuid.uuid4()}.mp4"
    output_path = None
    try:
        # 1. Save input
        content = await video.read()
        with open(temp_in, "wb") as f:
            f.write(content)
            
        # 2. Parse data
        segments_list = json.loads(segments)
        styles_dict = json.loads(styles)
        
        # 3. Render
        output_path = await export_video_render(temp_in, segments_list, styles_dict)
        
        # 4. Return as file and cleanup
        if not output_path or not os.path.exists(output_path):
            raise HTTPException(status_code=500, detail="Rendering failed")

        # Define cleanup function
        def cleanup_files(path1, path2):
            try:
                if path1 and os.path.exists(path1):
                    os.remove(path1)
                if path2 and os.path.exists(path2):
                    os.remove(path2)
            except Exception as e:
                print(f"Cleanup error: {e}")

        # Add cleanup to background tasks
        background_tasks.add_task(cleanup_files, temp_in, output_path)

        return FileResponse(
            path=output_path,
            filename=f"codex7_viral_export.mp4",
            media_type='video/mp4'
        )
        
    except Exception as e:
        print(f"Export Error: {e}")
        if os.path.exists(temp_in): os.remove(temp_in)
        raise HTTPException(status_code=500, detail=str(e))


# --- New Google Sheets Endpoints ---

@app.post("/api/store-user")
async def store_user_endpoint(user: UserLogin):
    """
    Stores or updates user data in Google Sheets.
    """
    # The 'login' endpoint below already does this, but we expose this specifically as requested
    try:
        result = db.store_user(user.dict())
        return {"status": "success", "action": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/store-feedback")
async def store_feedback_endpoint(fb: UserFeedback):
    """
    Stores feedback in Google Sheets.
    """
    try:
        # We need to ensure email/name are passed. The frontend might need to update to send them if they aren't in UserFeedback model fully
        success = db.store_feedback(fb.dict())
        if not success:
             raise HTTPException(status_code=500, detail="Failed to write to Google Sheets")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Existing Endpoints Updated ---

@app.post("/api/login")
async def login(user: UserLogin):
    # Check/Store in Google Sheets
    action = db.store_user({
        "name": user.name,
        "email": user.email,
        "country": user.country
    })
    
    # Store in Local JSON DB
    local_db.store_user({
        "name": user.name,
        "email": user.email,
        "country": user.country
    })
    
    # Return a user_id (using email for simplicity in this no-auth setup)
    return {"status": "success", "user_id": user.email, "action": action}

@app.post("/api/feedback")
async def submit_feedback(fb: UserFeedback):
    # Log to Analytics
    await analytics.log_event("USER_FEEDBACK", {
        "user_id": fb.user_id,
        "rating": str(fb.rating),
        "feedback_message": fb.message
    })
    
    # Store in Sheets
    db.store_feedback({
        "user_id": fb.user_id, 
        "rating": fb.rating,
        "message": fb.message,
        "feature": fb.feature,
        "language": fb.language_pref,
        "email": fb.user_id # Using user_id as email based on frontend logic usually sending email
    })

    # Store in Local JSON DB
    local_db.store_feedback(fb.dict())

    return {"status": "success", "message": "Feedback received. Thank you!"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
