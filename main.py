from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from shazamio import Shazam
import yt_dlp
import os
import uuid
import asyncio
import subprocess

app = FastAPI()

async def shazam_recognize(audio_path):
    shazam = Shazam()
    result = await shazam.recognize(audio_path)
    if not result or 'track' not in result:
        return None
    track = result['track']
    return {
        "title": track.get("title"),
        "artist": track.get("subtitle"),
        "image": track.get("images", {}).get("coverarthq"),
    }

def download_and_convert(video_url):
    temp_id = str(uuid.uuid4())
    video_file = f"{temp_id}.mp4"
    audio_file = f"{temp_id}.mp3"

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': video_file,
        'quiet': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # Convert to mp3
        subprocess.run(["ffmpeg", "-y", "-i", video_file, "-vn", "-acodec", "libmp3lame", audio_file], check=True)
        return audio_file, video_file
    except Exception as e:
        return None, None

@app.get("/identify")
async def identify(request: Request):
    video_url = request.query_params.get("url")
    if not video_url:
        return JSONResponse({"error": "No URL provided"}, status_code=400)

    audio_file, video_file = download_and_convert(video_url)
    if not audio_file:
        return JSONResponse({"error": "Failed to download or convert video"}, status_code=500)

    result = await shazam_recognize(audio_file)

    # Clean up
    if os.path.exists(audio_file):
        os.remove(audio_file)
    if os.path.exists(video_file):
        os.remove(video_file)

    if not result:
        return JSONResponse({"error": "No song recognized"}, status_code=404)

    return JSONResponse(result)
