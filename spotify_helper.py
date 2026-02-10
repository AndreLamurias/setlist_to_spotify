import os
import json
import time
import base64
import re
import requests
from urllib.parse import urlencode
import base64
import json
import time
from rich.prompt import Prompt
import sys
from dotenv import load_dotenv  # Add this

load_dotenv()  # Add this immediately

REDIRECT_URI = "http://127.0.0.1:8888/callback"
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
TOKEN_FILE = ".spotify_token.json"


#def extract_playlist_id(url):
#    """Extracts playlist ID from a full Spotify playlist URL"""
#    match = re.search(r"playlist/([a-zA-Z0-9]+)", url)
#    return match.group(1) if match else None

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
    "scope": "playlist-modify-public playlist-modify-private playlist-read-private"
}
    # ADD THIS DEBUG PRINT
    print(f"\n DEBUG: Sending Redirect URI: {REDIRECT_URI}")
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

def get_playlist_tracks(access_token, playlist_id):
    headers = {"Authorization": f"Bearer {access_token}"}
    tracks = []

    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    while url:
        res = requests.get(url, headers=headers)
        
        if res.status_code != 200:
            breakpoint()
            print(f"[red]❌ Failed to fetch playlist tracks: {res.status_code} - {res.text}[/red]")
            sys.exit()
            return []

        try:
            data = res.json()
        except ValueError:
            print(f"[red]❌ Invalid JSON in playlist tracks response[/red]")
            return []

        items = data.get("items", [])
        for item in items:
            track = item.get("track")
            if track:
                tracks.append(track)

        url = data.get("next")  # handle pagination

    return tracks

def extract_playlist_id(url_or_id):
    if "spotify.com/playlist/" in url_or_id:
        match = re.search(r"playlist/([a-zA-Z0-9]+)", url_or_id)
        return match.group(1) if match else None
    return url_or_id  # assume it's a raw ID


from difflib import SequenceMatcher

def create_spotify_playlist(access_token, user_id, name, description="", public=False):
    url = f"https://api.spotify.com/v1/users/{user_id}/playlists"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    data = {
        "name": name,
        "description": description,
        "public": public
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        playlist = response.json()
        print(f"✅ Created playlist: [bold]{playlist['name']}[/bold]")
        return playlist["id"]
    else:
        print(f"[red]❌ Failed to create playlist: {response.text}[/red]")
        return None


def add_songs_to_playlist(access_token, songs, artist_name, playlist_id):
    headers = {"Authorization": f"Bearer {access_token}"}
    uris = []

    # Get the existing tracks in the playlist
    existing_tracks = get_playlist_tracks(access_token, playlist_id)
    existing_uris = {track["uri"] for track in existing_tracks}

    def similar(a, b): return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    for song in songs:
        search = requests.get("https://api.spotify.com/v1/search", headers=headers, params={
            "q": f"{artist_name} {song} ",
            "type": "track",
            "limit": 10
        }).json()

        tracks = search.get("tracks", {}).get("items", [])
        found = False
        for track in tracks:
            track_artists = [artist["name"] for artist in track["artists"]]
            track_uri = track["uri"]
            if any(similar(track_artist, artist_name) > 0.8 for track_artist in track_artists):
                if track_uri not in existing_uris:  # Check if the track is already in the playlist
                    uris.append(track_uri)
                    existing_uris.add(track_uri)  # Add the URI to the set of existing URIs
                    print(f"✅ Found and added: {song} by {', '.join(track_artists)} {track_uri}")
                else:
                    print(f"❌ Skipping duplicate: {song} by {', '.join(track_artists)} {track_uri}")
                found = True
                break
        
        if not found:
            print([t["name"] for t in tracks])
            print(f"{song} {artist_name}")
            #breakpoint()
            print(f"❌ Not found or wrong artist: {song}")

    if not uris:
        print("No new songs found to add.")
        return 0

    # Add non-duplicate songs to the playlist
    res = requests.post(
        f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks",
        headers=headers,
        json={"uris": uris}
    )

    if res.status_code == 201:
        print("[green]🎉 Songs added to playlist![/green]")
        return len(uris)
    else:
        print(f"[red]Failed to add songs: {res.text}[/red]")
        return 0


## for web app
def get_auth_url():
    params = {
        "client_id": SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": "playlist-modify-public playlist-modify-private playlist-read-private"
    }
    print(f"\n DEBUG: Sending Redirect URI: {REDIRECT_URI}")
    return f"https://accounts.spotify.com/authorize?{urlencode(params)}"