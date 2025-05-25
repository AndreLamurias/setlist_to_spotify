import os
import json
import time
import base64
import re
import requests

REDIRECT_URI = "http://localhost:8888/callback"
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
TOKEN_FILE = ".spotify_token.json"


def extract_playlist_id(url):
    """Extracts playlist ID from a full Spotify playlist URL"""
    match = re.search(r"playlist/([a-zA-Z0-9]+)", url)
    return match.group(1) if match else None

def get_spotify_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            tokens = json.load(f)
            # Check expiration
            if time.time() < tokens["expires_at"]:
                return tokens["access_token"]
            else:
                # Try to refresh
                refreshed = refresh_token(tokens["refresh_token"])
                if refreshed:
                    return refreshed
                else:
                    print("[red]Failed to refresh token. Re-authenticating...[/red]")

    # If no token or refresh fails, do full auth
    return authorize_user()


def refresh_token(refresh_token):
    auth_str = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()

    res = requests.post("https://accounts.spotify.com/api/token", data={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }, headers={
        "Authorization": f"Basic {b64_auth}"
    })

    if res.status_code == 200:
        data = res.json()
        access_token = data["access_token"]
        expires_in = data.get("expires_in", 3600)
        new_token = {
            "access_token": access_token,
            "refresh_token": refresh_token,  # Keep the original
            "expires_at": time.time() + expires_in - 30
        }
        with open(TOKEN_FILE, "w") as f:
            json.dump(new_token, f)
        return access_token
    else:
        return None


def authorize_user():
    params = {
    "client_id": SPOTIFY_CLIENT_ID,
    "response_type": "code",
    "redirect_uri": REDIRECT_URI,
    "scope": "playlist-modify-public playlist-modify-private"
}

    auth_url = f"https://accounts.spotify.com/authorize?{urlencode(params)}"

    print("\n[bold blue]Open this URL in your browser to authenticate with Spotify:[/bold blue]")
    print(auth_url)
    code = Prompt.ask("\nPaste the code from the URL after login")

    res = requests.post("https://accounts.spotify.com/api/token", data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": SPOTIFY_CLIENT_ID,
        "client_secret": SPOTIFY_CLIENT_SECRET
    })

    if res.status_code == 200:
        data = res.json()
        access_token = data["access_token"]
        refresh_token_val = data["refresh_token"]
        expires_in = data.get("expires_in", 3600)

        token_data = {
            "access_token": access_token,
            "refresh_token": refresh_token_val,
            "expires_at": time.time() + expires_in - 30
        }

        with open(TOKEN_FILE, "w") as f:
            json.dump(token_data, f)

        return access_token
    else:
        print("[red]Failed to authenticate with Spotify.[/red]")
        print(f"[yellow]Status: {res.status_code}[/yellow]")
        print(f"[yellow]Response: {res.text}[/yellow]")
        exit()

def get_current_user_id(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get("https://api.spotify.com/v1/me", headers=headers)
    if response.status_code == 200:
        return response.json()["id"]
    else:
        print("[red]❌ Could not get Spotify user ID[/red]")
        return None

def get_user_playlists(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    playlists = []
    url = "https://api.spotify.com/v1/me/playlists"
    
    while url:
        res = requests.get(url, headers=headers)
        data = res.json()
        playlists.extend(data.get("items", []))
        url = data.get("next")  # paginated results

    return playlists

