import os
from services.transcription.whisper_v3 import transcription_service

async def generate_ai_captions(video_path: str, language: str = "en"):
    """
    Production Entry Point: Calls the isolated Whisper Large v3 infrastructure.
    Includes chunking, async transcription, and viral post-processing.
    """
    try:
        # Transfer execution to the dedicated transcription service
        result = await transcription_service.process_video(video_path, language)
        
        # If the high-accuracy service fails, we try once more as per requirements
        if result.get("status") == "error":
            print(f"Retrying transcription for {video_path}...")
            result = await transcription_service.process_video(video_path, language)
            
        return result
        
    except Exception as e:
        print(f"AI Service Bridge Error: {e}")
        return {"status": "error", "message": f"Critical AI Failure: {str(e)}"}

async def export_video_render(video_path: str, segments: list, styles: dict):
    """
    Renders video with burned-in subtitles.
    """
    return await transcription_service.render_viral_video(video_path, segments, styles)
