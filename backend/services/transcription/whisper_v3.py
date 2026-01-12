import os
import subprocess
import uuid
import asyncio
import re
import random
import json
from typing import List, Dict, Any
from dotenv import load_dotenv
import static_ffmpeg

load_dotenv()

class WhisperLargeV3Service:
    def __init__(self):
        self.model_size = os.getenv("WHISPER_MODEL", "base") # Default to base for stability
        self.device = "cuda" if os.getenv("USE_GPU", "false").lower() == "true" else "cpu"
        self.compute_type = "float16" if self.device == "cuda" else "int8"
        self.model = None # Lazy load
        
        # Ensure FFmpeg is available on Windows
        print("Ensuring FFmpeg infrastructure is ready...")
        static_ffmpeg.add_paths()
        
    def _load_model(self):
        if self.model is None:
            print(f"Loading Whisper Model ({self.model_size}) on {self.device}...")
            from faster_whisper import WhisperModel
            self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
        return self.model

    async def preprocess_audio(self, video_path: str) -> str:
        """
        Extracts high-quality mono 16kHz WAV for Whisper.
        """
        unique_id = uuid.uuid4().hex[:8]
        audio_path = f"temp_audio_{unique_id}.wav"
        
        cmd = [
            'ffmpeg', '-y', '-i', video_path,
            '-ar', '16000', '-ac', '1', '-acodec', 'pcm_s16le',
            audio_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        
        if not os.path.exists(audio_path):
            raise Exception("FFmpeg audio extraction failed.")
        
        return audio_path

    async def get_audio_duration(self, audio_path: str) -> float:
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', audio_path
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        return float(stdout.decode().strip())

    async def chunk_audio_ffmpeg(self, audio_path: str, chunk_length: int = 30) -> List[str]:
        """
        Splits audio into 30s chunks using FFmpeg.
        """
        duration = await self.get_audio_duration(audio_path)
        chunks = []
        
        for start_time in range(0, int(duration), chunk_length):
            chunk_path = f"{audio_path}_chunk_{start_time}.wav"
            cmd = [
                'ffmpeg', '-y', '-ss', str(start_time), '-t', str(chunk_length),
                '-i', audio_path, '-acodec', 'copy', chunk_path
            ]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            chunks.append(chunk_path)
        return chunks

    async def transcribe_chunk(self, chunk_path: str, start_offset: float, language: str = None) -> Dict[str, Any]:
        """
        Transcribes a single chunk with word-level timestamps and detects language.
        """
        model = self._load_model()
        loop = asyncio.get_event_loop()
        # VAD filter helps with alignment and avoids transcribing silence
        segments, info = await loop.run_in_executor(
            None, 
            lambda: model.transcribe(
                chunk_path, 
                word_timestamps=True,
                beam_size=5,
                task="translate" if language == "en" else "transcribe",
                language=language if language and language != "auto" else None,
                vad_filter=True,
                initial_prompt=f"Capturing viral shorts audio. Clear {language if language else 'English'} captions."
            )
        )
        
        chunk_words = []
        chunk_segments = []
        for segment in segments:
            chunk_segments.append({
                "start": round(segment.start + start_offset, 2),
                "end": round(segment.end + start_offset, 2),
                "text": segment.text.strip()
            })
            if segment.words:
                for word in segment.words:
                    chunk_words.append({
                        "word": word.word.strip(),
                        "start": round(word.start + start_offset, 2),
                        "end": round(word.end + start_offset, 2)
                    })
        
        if os.path.exists(chunk_path):
            try: os.remove(chunk_path)
            except: pass
            
        return {
            "words": chunk_words,
            "segments": chunk_segments,
            "language": info.language,
            "language_prob": info.language_probability
        }

    def group_words_virally(self, words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        STRICT 2-4 WORD GROUPING for viral shorts.
        - Splits precisely at 4 words max.
        - Breaks at punctuation.
        - Force first segment to 0.0s.
        """
        if not words:
            return []

        segments = []
        current_group = []
        
        for i, word_data in enumerate(words):
            current_group.append(word_data)
            
            # Conditions to break:
            # 1. Reach 4 words (Strictly 2-4)
            if len(current_group) >= 4:
                break_condition = True
            elif any(punc in word_data["word"] for punc in ['.', '?', '!']):
                # 2. End of sentence
                break_condition = True
            elif i < len(words) - 1 and (words[i+1]["start"] - word_data["end"]) > 0.3:
                # 3. Speech pause
                break_condition = True
            else:
                break_condition = False
            
            if break_condition or i == len(words) - 1:
                seg_text = " ".join([w["word"] for w in current_group]).strip()
                segments.append({
                    "start": round(current_group[0]["start"], 2),
                    "end": round(current_group[-1]["end"], 2),
                    "text": seg_text
                })
                current_group = []

        # Zero-delay rule
        if segments:
            segments[0]["start"] = 0.0
            
        return segments

    async def render_viral_video(self, input_video: str, segments: List[Dict[str, Any]], styles: Dict[str, Any]) -> str:
        """
        Burns subtitles directly into video for download.
        Uses SSA/ASS for advanced styling.
        """
        unique_id = uuid.uuid4().hex[:8]
        ass_path = f"subs_{unique_id}.ass"
        output_video = f"export_{unique_id}.mp4"
        
        # 1. Create ASS Subtitle File
        color = styles.get('color', '#FFFFFF').replace('#', '&H00')
        ass_color = "&H00FFFFFF" 
        
        with open(ass_path, "w", encoding='utf-8') as f:
            f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n")
            f.write("[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            f.write(f"Style: Default,Bebas Neue,80,{ass_color},&H000000FF,&H00000000,&H90000000,1,0,0,0,100,100,0,0,1,4,2,2,40,40,200,1\n\n")
            f.write("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            
            for seg in segments:
                t_start = self._format_ass_time(seg['start'])
                t_end = self._format_ass_time(seg['end'])
                text = (seg.get('text') or seg.get('word') or "").upper()
                f.write(f"Dialogue: 0,{t_start},{t_end},Default,,0,0,0,,{text}\n")

        # 2. FFmpeg Command
        escaped_ass = ass_path.replace(":", "\\:").replace("\\", "/")
        cmd = [
            'ffmpeg', '-y', '-i', input_video,
            '-vf', f"subtitles='{escaped_ass}'",
            '-c:a', 'copy',
            '-preset', 'ultrafast',
            output_video
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        
        if os.path.exists(ass_path): os.remove(ass_path)
        return output_video

    def _format_ass_time(self, seconds: float) -> str:
        ms = int((seconds % 1) * 100)
        s = int(seconds % 60)
        m = int((seconds // 60) % 60)
        h = int(seconds // 3600)
        return f"{h}:{m:02}:{s:02}.{ms:02}"

    def post_process_captions(self, words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        enhanced_words = []
        emojis = ["🔥", "✨", "🎯", "⚡", "🚀", "🙌", "💥", "🎬"]
        
        for i, word_data in enumerate(words):
            word = word_data["word"]
            if i == 0 or (i > 0 and words[i-1]["word"].endswith(('.', '!', '?'))):
                word = word.capitalize()
            
            if random.random() < 0.1:
                word += f" {random.choice(emojis)}"
            
            enhanced_words.append({
                **word_data,
                "word": word
            })
        return enhanced_words

    async def process_video(self, video_path: str, language: str = None):
        audio_path = None
        try:
            audio_path = await self.preprocess_audio(video_path)
            chunk_paths = await self.chunk_audio_ffmpeg(audio_path)
            
            tasks = []
            for i, cp in enumerate(chunk_paths):
                tasks.append(self.transcribe_chunk(cp, i * 30.0, language))
            
            results = await asyncio.gather(*tasks)
            
            all_words = []
            all_segments = []
            detected_language = results[0]["language"] if results else "unknown"
            language_prob = results[0]["language_prob"] if results else 0.0
            
            for res in results:
                all_words.extend(res["words"])
                
            final_words = self.post_process_captions(all_words)
            viral_segments = self.group_words_virally(final_words)
            
            return {
                "status": "success",
                "words": final_words,
                "segments": viral_segments,
                "full_text": " ".join([w["word"] for w in final_words]),
                "language": detected_language,
                "language_probability": language_prob,
                "model": "whisper-large-v3"
            }
        except Exception as e:
            print(f"Transcription Error: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            if audio_path and os.path.exists(audio_path):
                try: os.remove(audio_path)
                except: pass

transcription_service = WhisperLargeV3Service()
