"""
generate_video.py — Crea el video del Short completamente gratis
- Imágenes: Pollinations.ai (100% gratis, sin API key)
- Texto en pantalla: MoviePy + Pillow
- Audio: gTTS (Google Text-to-Speech, gratis)
- Video: MoviePy (gratis)
"""

import json
import os
import time
import requests
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy.editor import (
    VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip,
    concatenate_videoclips, TextClip
)
from moviepy.audio.fx.all import audio_fadein, audio_fadeout
from gtts import gTTS
import tempfile

# ─── Configuración ────────────────────────────────────────────────────────────
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)
FRAMES_DIR = OUTPUT_DIR / "frames"
FRAMES_DIR.mkdir(exist_ok=True)
AUDIO_DIR = OUTPUT_DIR / "audio"
AUDIO_DIR.mkdir(exist_ok=True)

# Resolución vertical para Shorts (9:16)
W, H = 1080, 1920


def generate_image_pollinations(prompt: str, scene_idx: int) -> Path:
    """
    Genera imagen con Pollinations.ai — 100% GRATIS, sin registro ni API key.
    Usa el modelo flux (por defecto).
    """
    # Enriquecer el prompt para estilo tech/futurista
    full_prompt = (
        f"{prompt}, futuristic tech style, dark background, neon accents, "
        f"high quality, 9:16 vertical format, dramatic lighting, cinematic"
    )
    
    # URL de la API de Pollinations (pública y gratuita)
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(full_prompt)}"
    params = {
        "width": W,
        "height": H,
        "model": "flux",
        "nologo": "true",
        "enhance": "true",
    }
    
    img_path = FRAMES_DIR / f"scene_{scene_idx:02d}.jpg"
    
    try:
        print(f"  🎨 Generando imagen {scene_idx+1}: {prompt[:50]}...")
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        
        with open(img_path, "wb") as f:
            f.write(response.content)
        
        # Verificar que es una imagen válida
        img = Image.open(img_path)
        img.verify()
        print(f"  ✅ Imagen {scene_idx+1} guardada ({img_path.stat().st_size // 1024}KB)")
        return img_path
        
    except Exception as e:
        print(f"  ⚠️  Error generando imagen, usando fallback: {e}")
        return create_fallback_image(prompt, scene_idx)


def create_fallback_image(text: str, scene_idx: int) -> Path:
    """Crea imagen de respaldo con degradado y texto si Pollinations falla."""
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    
    # Degradado azul/morado tech
    for y in range(H):
        ratio = y / H
        r = int(10 + ratio * 30)
        g = int(0 + ratio * 10)
        b = int(40 + ratio * 80)
        draw.rectangle([(0, y), (W, y + 1)], fill=(r, g, b))
    
    # Texto centrado
    draw.text((W//2, H//2), text[:40], fill=(255, 255, 255), anchor="mm")
    
    img_path = FRAMES_DIR / f"scene_{scene_idx:02d}.jpg"
    img.save(img_path, "JPEG", quality=90)
    return img_path


def add_text_overlay(img_path: Path, text: str, scene_idx: int) -> Path:
    """Añade texto con overlay semitransparente sobre la imagen."""
    img = Image.open(img_path).convert("RGBA")
    
    # Overlay oscuro en la parte inferior para legibilidad
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Rectángulo semitransparente
    box_h = 320
    box_y = H - box_h - 80
    draw.rectangle([(0, box_y), (W, H - 60)], fill=(0, 0, 0, 180))
    
    # Texto principal
    try:
        # Intentar cargar fuente del sistema
        font_size = 72 if len(text) < 30 else 56
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()
    
    draw_overlay = ImageDraw.Draw(overlay)
    
    # Ajustar texto en varias líneas
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        test = " ".join(current_line + [word])
        bbox = draw_overlay.textbbox((0, 0), test, font=font)
        if bbox[2] > W - 80 and current_line:
            lines.append(" ".join(current_line))
            current_line = [word]
        else:
            current_line.append(word)
    if current_line:
        lines.append(" ".join(current_line))
    
    # Calcular posición Y centrada en el box
    total_text_h = len(lines) * (font_size + 12)
    text_y = box_y + (box_h - total_text_h) // 2
    
    for line in lines:
        bbox = draw_overlay.textbbox((0, 0), line, font=font)
        text_x = (W - (bbox[2] - bbox[0])) // 2
        # Sombra
        draw_overlay.text((text_x + 3, text_y + 3), line, font=font, fill=(0, 0, 0, 200))
        # Texto blanco
        draw_overlay.text((text_x, text_y), line, font=font, fill=(255, 255, 255, 255))
        text_y += font_size + 12
    
    # Composición final
    result = Image.alpha_composite(img, overlay).convert("RGB")
    out_path = FRAMES_DIR / f"scene_{scene_idx:02d}_text.jpg"
    result.save(out_path, "JPEG", quality=95)
    return out_path


def generate_narration(text: str, scene_idx: int, lang: str = "es") -> Path:
    """Genera narración con gTTS (Google Text-to-Speech) — 100% GRATIS."""
    audio_path = AUDIO_DIR / f"scene_{scene_idx:02d}.mp3"
    
    try:
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(str(audio_path))
        print(f"  🎙️  Audio {scene_idx+1} generado")
    except Exception as e:
        print(f"  ⚠️  Error en TTS: {e}")
        # Crear silencio como fallback
        from pydub import AudioSegment
        silence = AudioSegment.silent(duration=2000)
        silence.export(str(audio_path), format="mp3")
    
    return audio_path


def build_video(script: dict) -> Path:
    """Ensambla el video final con todas las escenas."""
    escenas = script["escenas"]
    clips = []
    
    print(f"\n🎬 Construyendo video con {len(escenas)} escenas...")
    
    for i, escena in enumerate(escenas):
        print(f"\n📸 Escena {i+1}/{len(escenas)}: {escena['texto_pantalla'][:40]}...")
        
        # 1. Generar imagen con Pollinations
        time.sleep(1)  # Respetar rate limit de Pollinations
        img_path = generate_image_pollinations(escena["texto_pantalla"], i)
        
        # 2. Añadir texto encima
        img_with_text = add_text_overlay(img_path, escena["texto_pantalla"], i)
        
        # 3. Generar narración
        audio_path = generate_narration(escena["narracion"], i)
        
        # 4. Crear clip de imagen
        img_clip = ImageClip(str(img_with_text))
        
        # 5. Cargar audio para saber duración real
        audio_clip = AudioFileClip(str(audio_path))
        duration = max(escena.get("duracion", 3), audio_clip.duration + 0.3)
        
        # 6. Configurar duración del clip de imagen
        img_clip = img_clip.set_duration(duration)
        
        # 7. Ajustar audio a la duración
        audio_clip = audio_clip.set_duration(min(audio_clip.duration, duration))
        
        # 8. Combinar imagen + audio
        video_clip = img_clip.set_audio(audio_clip)
        clips.append(video_clip)
    
    # Concatenar todas las escenas
    print("\n🔗 Concatenando escenas...")
    final_video = concatenate_videoclips(clips, method="compose")
    
    # Agregar fade in/out de audio
    final_audio = final_video.audio
    if final_audio:
        final_audio = audio_fadein(final_audio, 0.5)
        final_audio = audio_fadeout(final_audio, 1.0)
        final_video = final_video.set_audio(final_audio)
    
    # Exportar
    output_path = OUTPUT_DIR / "short_final.mp4"
    print(f"\n💾 Exportando video final...")
    final_video.write_videofile(
        str(output_path),
        fps=30,
        codec="libx264",
        audio_codec="aac",
        bitrate="8000k",
        audio_bitrate="192k",
        threads=2,
        preset="fast",
        ffmpeg_params=["-movflags", "+faststart"],  # Optimizado para web
        verbose=False,
        logger=None,
    )
    
    print(f"✅ Video exportado: {output_path} ({output_path.stat().st_size // (1024*1024)} MB)")
    return output_path


if __name__ == "__main__":
    with open("output/script.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    script = data["script"]
    video_path = build_video(script)
    print(f"\n🎉 Video listo: {video_path}")
