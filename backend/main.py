import os
import uuid
import datetime
import json
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# AI and Analytics Services
from backend.ai_service import generate_ai_captions, export_video_render
from backend.sheets_service import SheetsDB, JSONDB
from backend.services.analytics import analytics
from fastapi.responses import FileResponse, StreamingResponse

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI()

# Serve frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
def read_root():
    return FileResponse("frontend/index.html")

# --- Environment Setup ---
_backend_dir = Path(__file__).resolve().parent
_env_path = _backend_dir / ".env"
load_dotenv(_env_path if _env_path.exists() else None)

app = FastAPI(title="codex7.ai API")

# --- Models ---
class UserFeedback(BaseModel):
    user_id: str
    email: Optional[str] = ""
    rating: int
    message: Optional[str] = ""
    feature: Optional[str] = "Editor"
    language_pref: Optional[str] = "en"

class UserLogin(BaseModel):
    name: str
    email: str
    country: str

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Database Instances ---
db = SheetsDB()
local_db = JSONDB()

# --- Endpoints ---

@app.post("/api/login")
async def login(user: UserLogin):
    """Handles user authentication and data sync"""
    # 1. Local JSON Storage (Source of Truth)
    user_result = local_db.store_user({
        "name": user.name,
        "email": user.email,
        "country": user.country
    })
    
    if not user_result:
        raise HTTPException(status_code=500, detail="Local Database Error")
        
    user_id = user_result["user_id"]
    action = user_result["action"]

    # 2. Sync to Google Sheets
    sheet_action = db.store_user({
        "name": user.name,
        "email": user.email,
        "country": user.country,
        "user_id": user_id
    })
    
    return {
        "status": "success", 
        "user_id": user_id, 
        "action": action, 
        "sheet_action": sheet_action
    }

@app.post("/api/feedback")
async def submit_feedback(fb: UserFeedback):
    """Stores user feedback in both local and cloud databases"""
    # Log to Analytics
    await analytics.log_event("USER_FEEDBACK", {
        "user_id": fb.user_id,
        "rating": str(fb.rating),
        "feedback_message": fb.message
    })
    
    # Store in Google Sheets
    db.store_feedback({
        "user_id": fb.user_id, 
        "rating": fb.rating,
        "message": fb.message,
        "feature": fb.feature,
        "language": fb.language_pref,
        "email": fb.email or fb.user_id 
    })

    # Store in Local JSON DB
    local_db.store_feedback(fb.dict())

    return {"status": "success", "message": "Feedback received. Thank you!"}

@app.post("/api/generate-captions")
async def process_video(
    video: UploadFile = File(...),
    email: str = Form(...),
    language: str = Form("en")
):
    """Processes uploaded video for AI captions"""
    MAX_SIZE = 50 * 1024 * 1024
    content = await video.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Max 50MB allowed.")
    await video.seek(0)

    temp_path = f"temp_{uuid.uuid4()}_{video.filename}"
    with open(temp_path, "wb") as f:
        f.write(content)
    
    try:
        result = await generate_ai_captions(temp_path, language)
        
        await analytics.log_event("CAPTION_GENERATE", {
            "user_id": email,
            "user_query": video.filename,
            "detected_language": f"{result.get('language', 'unknown')} ({result.get('language_probability', 0):.2f})",
            "error_log": result.get("status")
        })
        
        os.remove(temp_path)
        return result
    except Exception as e:
        if os.path.exists(temp_path): os.remove(temp_path)
        await analytics.log_event("CAPTION_FAILURE", {"user_id": email, "error_log": str(e)})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history")
async def get_history(email: str):
    """Returns user project history"""
    user = db.get_user_by_email(email)
    if not user: return []
    return local_db.get_user_history(user["user_id"])

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
    """Saves captioned project data"""
    user = db.get_user_by_email(email)
    if not user: raise HTTPException(status_code=404, detail="User not found")
        
    history_data = {
        "user_id": user["user_id"],
        "email": email,
        "video_name": video_name,
        "caption_text": caption_text,
        "font": font,
        "size": size,
        "color": color,
        "position": position,
        "timestamp": datetime.datetime.now().isoformat()
    }
    local_db.save_history(history_data)
    return {"status": "success"}

@app.post("/api/export-video")
async def export_video(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    segments: str = Form(...),
    styles: str = Form(...)
):
    """Renders final video with burned-in captions"""
    temp_in = f"export_in_{uuid.uuid4()}.mp4"
    try:
        content = await video.read()
        with open(temp_in, "wb") as f:
            f.write(content)
            
        segments_list = json.loads(segments)
        styles_dict = json.loads(styles)
        
        output_path = await export_video_render(temp_in, segments_list, styles_dict)
        
        if not output_path or not os.path.exists(output_path):
            raise HTTPException(status_code=500, detail="Rendering failed")

        def cleanup_files(path1, path2):
            try:
                for p in [path1, path2]:
                    if p and os.path.exists(p): os.remove(p)
            except: pass

        background_tasks.add_task(cleanup_files, temp_in, output_path)

        return FileResponse(
            path=output_path,
            filename=f"codex7_viral_export.mp4",
            media_type='video/mp4'
        )
    except Exception as e:
        if os.path.exists(temp_in): os.remove(temp_in)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
