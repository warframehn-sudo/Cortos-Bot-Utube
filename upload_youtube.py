"""
auth_youtube.py — Script de autenticación ÚNICO (ejecutar solo una vez en tu PC)
Genera el token que se guarda como secret en GitHub.

INSTRUCCIONES:
1. Ve a https://console.cloud.google.com
2. Crea un proyecto → APIs → YouTube Data API v3 → Habilitar
3. Credenciales → OAuth 2.0 → Aplicación de escritorio
4. Descarga el JSON → guárdalo como credentials/client_secrets.json
5. Ejecuta este script: python src/auth_youtube.py
6. Se abrirá el navegador → autoriza tu cuenta de YouTube
7. Copia el contenido de credentials/youtube_token.json
8. Pégalo como secret en GitHub: YOUTUBE_TOKEN
"""

import json
import os
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = Path("credentials/youtube_token.json")
CLIENT_SECRETS = Path("credentials/client_secrets.json")


def authenticate():
    Path("credentials").mkdir(exist_ok=True)
    
    if not CLIENT_SECRETS.exists():
        print("❌ Falta credentials/client_secrets.json")
        print("   Descárgalo desde Google Cloud Console")
        return
    
    print("🌐 Abriendo navegador para autorizar YouTube...")
    
    flow = InstalledAppFlow.from_client_secrets_file(
        str(CLIENT_SECRETS), SCOPES
    )
    
    # Usar servidor local para OAuth
    creds = flow.run_local_server(
        port=8080,
        prompt="consent",
        access_type="offline"
    )
    
    # Guardar token con refresh_token
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes),
    }
    
    TOKEN_FILE.write_text(json.dumps(token_data, indent=2))
    
    print("\n✅ Autenticación exitosa!")
    print(f"📄 Token guardado en: {TOKEN_FILE}")
    print("\n" + "="*60)
    print("PRÓXIMO PASO: Copia este JSON como secret YOUTUBE_TOKEN en GitHub:")
    print("="*60)
    print(json.dumps(token_data))
    print("="*60)
    print("\nSettings → Secrets and Variables → Actions → New secret")
    print("Name: YOUTUBE_TOKEN")
    print("Value: (pega el JSON de arriba)")


if __name__ == "__main__":
    authenticate()
