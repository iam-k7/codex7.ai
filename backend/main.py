import os
import uuid
import json
import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

# --- Load environment ---
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / "backend" / ".env"
load_dotenv(ENV_PATH if ENV_PATH.exists() else None)

# --- Create FastAPI app ONCE ---
app = FastAPI(title="codex7.ai")

# --- Serve Frontend ---
FRONTEND_DIR = BASE_DIR / "frontend"

app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR),
    name="static"
)

@app.get("/")
def root():
    return FileResponse(FRONTEND_DIR / "index.html")

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Internal services ---
from backend.ai_service import generate_ai_captions, export_video_render
from backend.sheets_service import SheetsDB, JSONDB
from backend.services.analytics import analytics

# --- Databases ---
db = SheetsDB()
local_db = JSONDB()

# --- Models ---
class UserLogin(BaseModel):
    name: str
    email: str
    country: str

class UserFeedback(BaseModel):
    user_id: str
    email: Optional[str] = ""
    rating: int
    message: Optional[str] = ""
    feature: Optional[str] = "Editor"
    language_pref: Optional[str] = "en"

# ---------------- API ROUTES ----------------

@app.post("/api/login")
async def login(user: UserLogin):
    user_result = local_db.store_user(user.dict())
    if not user_result:
        raise HTTPException(status_code=500, detail="Local DB error")

    user_id = user_result["user_id"]

    db.store_user({
        "user_id": user_id,
        "name": user.name,
        "email": user.email,
        "country": user.country
    })

    return {"status": "success", "user_id": user_id}

@app.post("/api/feedback")
async def submit_feedback(fb: UserFeedback):
    await analytics.log_event("USER_FEEDBACK", fb.dict())
    db.store_feedback(fb.dict())
    local_db.store_feedback(fb.dict())
    return {"status": "success"}

@app.post("/api/generate-captions")
async def generate(
    video: UploadFile = File(...),
    email: str = Form(...),
    language: str = Form("en")
):
    temp_file = f"temp_{uuid.uuid4()}_{video.filename}"
    content = await video.read()

    with open(temp_file, "wb") as f:
        f.write(content)

    try:
        result = await generate_ai_captions(temp_file, language)
        os.remove(temp_file)
        return result
    except Exception as e:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history")
async def history(email: str):
    user = db.get_user_by_email(email)
    if not user:
        return []
    return local_db.get_user_history(user["user_id"])

@app.post("/api/export-video")
async def export_video(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    segments: str = Form(...),
    styles: str = Form(...)
):
    temp_in = f"export_{uuid.uuid4()}.mp4"
    content = await video.read()

    with open(temp_in, "wb") as f:
        f.write(content)

    segments_list = json.loads(segments)
    styles_dict = json.loads(styles)

    output = await export_video_render(temp_in, segments_list, styles_dict)

    background_tasks.add_task(os.remove, temp_in)

    return FileResponse(
        output,
        media_type="video/mp4",
        filename="codex7_export.mp4"
    )

# --- Local run only ---
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
