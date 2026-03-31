import feedparser
import random
import json
import os
from datetime import datetime, timedelta
import google.generativeai as genai

RSS_FEEDS = [
    "https://venturebeat.com/category/ai/feed/",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "https://www.tomshardware.com/rss/news.xml",
    "https://www.pcgamer.com/rss/news/",
    "https://arstechnica.com/gadgets/feed/",
    "https://blog.google/technology/ai/rss/",
    "https://huggingface.co/blog/feed.xml",
]

KEYWORDS = [
    "gemini", "grok", "chatgpt", "claude", "llama", "mistral",
    "stable diffusion", "midjourney", "dall-e", "sora", "kling",
    "runway", "pika", "elevenlabs", "suno", "udio",
    "nvidia", "amd", "rtx", "radeon", "dlss", "fsr",
    "blackwell", "rdna", "gpu", "geforce",
    "ai video", "ai image", "ai audio", "ai music",
    "text to video", "text to image", "image generation",
    "open source model", "new model", "ai tool", "artificial intelligence",
    "machine learning", "generative ai",
]


def fetch_recent_news(hours_back=48):
    cutoff = datetime.now() - timedelta(hours=hours_back)
    articles = []

    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:15]:
                pub = entry.get("published_parsed") or entry.get("updated_parsed")
                if pub:
                    pub_dt = datetime(*pub[:6])
                    if pub_dt < cutoff:
                        continue

                title = entry.get("title", "")
                summary = entry.get("summary", "")[:500]
                link = entry.get("link", "")

                text_lower = (title + " " + summary).lower()
                if any(kw in text_lower for kw in KEYWORDS):
                    articles.append({
                        "title": title,
                        "summary": summary,
                        "link": link,
                        "source": feed.feed.get("title", url),
                    })
        except Exception as e:
            print(f"Error en feed {url}: {e}")

    seen_titles = set()
    unique = []
    for a in articles:
        key = a["title"][:60].lower()
        if key not in seen_titles:
            seen_titles.add(key)
            unique.append(a)

    print(f"✅ {len(unique)} noticias relevantes encontradas")
    return unique[:20]


def pick_best_news(articles):
    if not articles:
        raise ValueError("No hay noticias disponibles")

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-1.5-flash")

    titles = "\n".join(
        f"{i+1}. {a['title']} (fuente: {a['source']})"
        for i, a in enumerate(articles)
    )

    response = model.generate_content(
        f"Eres un editor de YouTube Shorts de tecnologia. "
        f"De estas noticias de IA/Tech, elige el NUMERO (solo el numero) "
        f"de la mas viral e interesante para un Short de YouTube de 60 segundos:\n\n"
        f"{titles}\n\n"
        f"Responde SOLO con el numero."
    )

    try:
        idx = int(response.text.strip()) - 1
        idx = max(0, min(idx, len(articles) - 1))
    except Exception:
        idx = 0

    chosen = articles[idx]
    print(f"Noticia elegida: {chosen['title']}")
    return chosen


def generate_script(article):
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-1.5-flash")

    response = model.generate_content(
        f"""Eres un guionista experto en YouTube Shorts de tecnologia viral.
Crea un guion para un Short de 50-60 segundos sobre esta noticia:

TITULO: {article['title']}
RESUMEN: {article['summary']}
FUENTE: {article['source']}

Formato JSON exacto (sin markdown, solo JSON puro):
{{
  "titulo_video": "titulo llamativo con emoji para YouTube (max 60 chars)",
  "descripcion": "descripcion SEO con hashtags (max 200 chars)",
  "hashtags": ["#IA", "#Tech", "#shorts"],
  "escenas": [
    {{"duracion": 3, "texto_pantalla": "texto grande en pantalla", "narracion": "lo que se dice"}},
    {{"duracion": 3, "texto_pantalla": "...", "narracion": "..."}}
  ],
  "gancho": "primera frase ultra llamativa para los primeros 3 segundos",
  "llamada_accion": "frase final para que den like y se suscriban"
}}

Maximo 10 escenas, total 55 segundos. Que sea emocionante, informativo y viral."""
    )

    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip().rstrip("```").strip()

    script = json.loads(raw)
    print(f"Guion generado: {script['titulo_video']}")
    return script


if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    articles = fetch_recent_news()
    article = pick_best_news(articles)
    script = generate_script(article)

    with open("output/script.json", "w", encoding="utf-8") as f:
        json.dump({"article": article, "script": script}, f, ensure_ascii=False, indent=2)

    print("✅ script.json guardado")
