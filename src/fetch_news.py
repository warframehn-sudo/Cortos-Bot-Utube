"""
fetch_news.py — Busca noticias de IA desde feeds RSS gratuitos
Sin APIs de pago, sin claves comerciales
"""

import feedparser
import random
import json
import os
from datetime import datetime, timedelta
import anthropic

# ─── Fuentes RSS gratuitas de noticias de IA / Tech ───────────────────────────
RSS_FEEDS = [
    # IA General
    "https://venturebeat.com/category/ai/feed/",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "https://feeds.feedburner.com/oreilly/radar",
    # Nvidia / AMD / Gaming IA
    "https://www.tomshardware.com/rss/news.xml",
    "https://www.pcgamer.com/rss/news/",
    "https://arstechnica.com/gadgets/feed/",
    # Modelos de IA (Gemini, Grok, video, audio, imagen)
    "https://blog.google/technology/ai/rss/",
    "https://openai.com/blog/rss/",
    "https://www.anthropic.com/rss.xml",
    "https://huggingface.co/blog/feed.xml",
]

# Palabras clave para filtrar noticias relevantes
KEYWORDS = [
    # Modelos generativos
    "gemini", "grok", "chatgpt", "claude", "llama", "mistral",
    "stable diffusion", "midjourney", "dall-e", "sora", "kling",
    "runway", "pika", "elevenlabs", "suno", "udio",
    # Nvidia / AMD gaming
    "nvidia", "amd", "rtx", "radeon", "dlss", "fsr", "ray tracing",
    "blackwell", "rdna", "gpu", "geforce",
    # Categorías generales
    "ai video", "ai image", "ai audio", "ai music", "text to video",
    "text to image", "image generation", "video generation",
    "open source model", "new model", "ai tool", "artificial intelligence",
    "machine learning", "generative ai",
]


def fetch_recent_news(hours_back: int = 48) -> list[dict]:
    """Descarga y filtra noticias de las últimas N horas."""
    cutoff = datetime.now() - timedelta(hours=hours_back)
    articles = []

    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:15]:  # máx 15 por feed
                # Fecha de publicación
                pub = entry.get("published_parsed") or entry.get("updated_parsed")
                if pub:
                    pub_dt = datetime(*pub[:6])
                    if pub_dt < cutoff:
                        continue

                title = entry.get("title", "")
                summary = entry.get("summary", "")[:500]
                link = entry.get("link", "")

                # Filtrar por relevancia
                text_lower = (title + " " + summary).lower()
                if any(kw in text_lower for kw in KEYWORDS):
                    articles.append({
                        "title": title,
                        "summary": summary,
                        "link": link,
                        "source": feed.feed.get("title", url),
                    })
        except Exception as e:
            print(f"⚠️  Error en feed {url}: {e}")

    # Eliminar duplicados por título similar
    seen_titles = set()
    unique = []
    for a in articles:
        key = a["title"][:60].lower()
        if key not in seen_titles:
            seen_titles.add(key)
            unique.append(a)

    print(f"✅ {len(unique)} noticias relevantes encontradas")
    return unique[:20]  # máx 20 candidatas


def pick_best_news(articles: list[dict]) -> dict:
    """Elige la noticia más viral/interesante usando Claude (free tier)."""
    if not articles:
        raise ValueError("No hay noticias disponibles")

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    titles = "\n".join(
        f"{i+1}. {a['title']} (fuente: {a['source']})"
        for i, a in enumerate(articles)
    )

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",  # Más barato/rápido
        max_tokens=100,
        messages=[{
            "role": "user",
            "content": (
                f"Eres un editor de YouTube Shorts de tecnología. "
                f"De estas noticias de IA/Tech, elige el NÚMERO (solo el número) "
                f"de la más viral e interesante para un Short de YouTube de 60 segundos:\n\n"
                f"{titles}\n\n"
                f"Responde SOLO con el número."
            )
        }]
    )

    try:
        idx = int(message.content[0].text.strip()) - 1
        idx = max(0, min(idx, len(articles) - 1))
    except Exception:
        idx = 0

    chosen = articles[idx]
    print(f"🎯 Noticia elegida: {chosen['title']}")
    return chosen


def generate_script(article: dict) -> dict:
    """Genera el guión completo del Short con Claude."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        messages=[{
            "role": "user",
            "content": f"""Eres un guionista experto en YouTube Shorts de tecnología viral.
Crea un guión para un Short de 50-60 segundos sobre esta noticia:

TÍTULO: {article['title']}
RESUMEN: {article['summary']}
FUENTE: {article['source']}

Formato JSON exacto (sin markdown, solo JSON):
{{
  "titulo_video": "título llamativo con emoji para YouTube (máx 60 chars)",
  "descripcion": "descripción SEO con hashtags (máx 200 chars)",
  "hashtags": ["#IA", "#Tech", "#shorts"],
  "escenas": [
    {{"duracion": 3, "texto_pantalla": "texto grande en pantalla", "narracion": "lo que se dice"}},
    {{"duracion": 3, "texto_pantalla": "...", "narracion": "..."}}
  ],
  "gancho": "primera frase ultra llamativa para los primeros 3 segundos",
  "llamada_accion": "frase final para que den like y se suscriban"
}}

Máximo 10 escenas, total ~55 segundos. Que sea emocionante, informativo y viral."""
        }]
    )

    raw = message.content[0].text.strip()
    # Limpiar posibles bloques de código markdown
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip().rstrip("```").strip()

    script = json.loads(raw)
    print(f"📝 Guión generado: {script['titulo_video']}")
    return script


if __name__ == "__main__":
    articles = fetch_recent_news()
    article = pick_best_news(articles)
    script = generate_script(article)

    # Guardar para el siguiente paso
    with open("output/script.json", "w", encoding="utf-8") as f:
        json.dump({"article": article, "script": script}, f, ensure_ascii=False, indent=2)

    print("✅ script.json guardado")
