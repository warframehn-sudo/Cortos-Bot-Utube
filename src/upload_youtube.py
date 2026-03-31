"""
upload_youtube.py — Sube el Short a YouTube usando la API gratuita de YouTube Data v3
La YouTube Data API es GRATUITA (10,000 unidades/día, subir video = ~1600 unidades)
"""

import json
import os
import pickle
import time
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# ─── Configuración ────────────────────────────────────────────────────────────
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CREDENTIALS_FILE = "credentials/youtube_credentials.json"  # Token guardado
CLIENT_SECRETS_FILE = "credentials/client_secrets.json"     # OAuth2 de Google


def get_youtube_service():
    """Obtiene el servicio autenticado de YouTube."""
    creds = None
    
    # Cargar credenciales guardadas (token de refresh)
    token_data = os.environ.get("YOUTUBE_TOKEN")
    if token_data:
        creds = Credentials.from_authorized_user_info(
            json.loads(token_data), SCOPES
        )
    
    # Si el token expiró, renovarlo con refresh token
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        print("🔄 Token de YouTube renovado")
    
    if not creds or not creds.valid:
        raise ValueError(
            "❌ Credenciales de YouTube inválidas. "
            "Ejecuta 'python src/auth_youtube.py' para autenticarte."
        )
    
    return build("youtube", "v3", credentials=creds)


def upload_short(video_path: Path, script: dict) -> str:
    """Sube el video como YouTube Short."""
    youtube = get_youtube_service()
    
    title = script["titulo_video"][:100]  # Límite de YouTube
    description = (
        f"{script['descripcion']}\n\n"
        f"{'  '.join(script.get('hashtags', []))}\n\n"
        f"#Shorts #IA #TechNews #InteligenicaArtificial #Tecnologia"
    )[:5000]
    
    # Tags para el video
    tags = [
        tag.lstrip("#") for tag in script.get("hashtags", [])
    ] + ["Shorts", "IA", "Inteligencia Artificial", "Tech", "Tecnologia",
         "AI", "Novedades", "Tutorial"]
    
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags[:30],  # Máximo 30 tags
            "categoryId": "28",  # Ciencia y Tecnología
            "defaultLanguage": "es",
            "defaultAudioLanguage": "es",
        },
        "status": {
            "privacyStatus": "public",  # Cambiar a "private" para pruebas
            "selfDeclaredMadeForKids": False,
            "madeForKids": False,
        }
    }
    
    print(f"📤 Subiendo: {title}")
    
    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024 * 5  # Chunks de 5MB
    )
    
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )
    
    # Subida con reintentos y progreso
    response = None
    retry = 0
    
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                print(f"  📊 Progreso: {progress}%")
        except HttpError as e:
            if e.resp.status in [500, 502, 503, 504] and retry < 3:
                retry += 1
                wait = 2 ** retry
                print(f"  ⚠️  Error {e.resp.status}, reintentando en {wait}s...")
                time.sleep(wait)
            else:
                raise
    
    video_id = response["id"]
    video_url = f"https://youtube.com/shorts/{video_id}"
    
    print(f"✅ Video subido exitosamente!")
    print(f"🔗 URL: {video_url}")
    
    return video_id


def add_thumbnail_if_exists(youtube_service, video_id: str, thumbnail_path: Path):
    """Sube miniatura personalizada (opcional, requiere canal verificado)."""
    if not thumbnail_path.exists():
        return
    
    try:
        youtube_service.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg")
        ).execute()
        print("🖼️  Miniatura personalizada subida")
    except HttpError as e:
        print(f"⚠️  No se pudo subir miniatura: {e} (¿canal verificado?)")


if __name__ == "__main__":
    with open("output/script.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    script = data["script"]
    video_path = Path("output/short_final.mp4")
    
    if not video_path.exists():
        raise FileNotFoundError(f"Video no encontrado: {video_path}")
    
    video_id = upload_short(video_path, script)
    
    # Guardar resultado
    with open("output/result.json", "w") as f:
        json.dump({
            "video_id": video_id,
            "url": f"https://youtube.com/shorts/{video_id}",
            "title": script["titulo_video"],
            "uploaded_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        }, f, indent=2)
    
    print("\n🎉 ¡Short de YouTube publicado exitosamente!")
