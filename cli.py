import requests
from rich import print
from rich.prompt import Prompt, Confirm
from dotenv import load_dotenv
import os
from rich.prompt import Prompt
from rich import print
import sys

from spotify_helper import get_spotify_token, get_current_user_id, extract_playlist_id, extract_playlist_id, add_songs_to_playlist, create_spotify_playlist
load_dotenv()


SETLIST_FM_API_KEY = os.getenv("SETLIST_FM_API_KEY")


# Spotify Auth Step 1
import os
import json
import time
import argparse
import re



# Fetch setlist.fm data
from rich.table import Table
from rich.console import Console
from rich.prompt import IntPrompt

console = Console()

import re

def get_setlist_from_url(url):
    print(f"[bold green]Fetching setlist from URL...[/bold green]")
    
    match = re.search(r'/setlist/.+/.*-([0-9a-f]+)\.html', url)
    if not match:
        print("[red]Invalid setlist.fm URL format.[/red]")
        exit()

    setlist_id = match.group(1)
    headers = {
        "x-api-key": SETLIST_FM_API_KEY,
        "Accept": "application/json"
    }

    res = requests.get(f"https://api.setlist.fm/rest/1.0/setlist/{setlist_id}", headers=headers)

    if res.status_code != 200:
        print(f"[red]Failed to fetch setlist: {res.status_code}[/red]")
        exit()

    data = res.json()
    try:
        # Safely extract all songs from all sets
        songs = []
        for s in data.get("sets", {}).get("set", []):
            for song in s.get("song", []):
                name = song.get("name")
                if name:
                    songs.append(name)
    except (KeyError, IndexError):
        print("[red]This setlist has no valid songs.[/red]")
        exit()

    artist_name = data["artist"]["name"]
    return songs, artist_name

def get_setlist(artist, city):
    print(f"[bold green]Searching setlists for {artist} in {city}...[/bold green]")
    headers = {
        "x-api-key": SETLIST_FM_API_KEY,
        "Accept": "application/json"
    }

    res = requests.get("https://api.setlist.fm/rest/1.0/search/setlists", headers=headers, params={
        "artistName": artist,
        "cityName": city,
        "p": 1
    })

    data = res.json()
    setlists = data.get("setlist", [])
    if not setlists:
        print("[red]No setlists found.[/red]")
        exit()

    # Display options
    table = Table(title="🎤 Setlists")
    table.add_column("#", justify="right", style="cyan")
    table.add_column("Date", style="white")
    table.add_column("Venue", style="magenta")
    table.add_column("City", style="yellow")

    for i, s in enumerate(setlists, 1):
        date = s.get("eventDate", "Unknown")
        venue = s.get("venue", {}).get("name", "Unknown Venue")
        city = s.get("venue", {}).get("city", {}).get("name", "Unknown City")
        country = s.get("venue", {}).get("city", {}).get("country", {}).get("name", "")
        table.add_row(str(i), date, venue, f"{city}, {country}")

    console.print(table)

    index = IntPrompt.ask("Select a setlist number", choices=[str(i) for i in range(1, len(setlists)+1)])
    selected = setlists[index - 1]

    try:
        # Safely extract all songs from all sets
        songs = []
        for s in data.get("sets", {}).get("set", []):
            for song in s.get("song", []):
                name = song.get("name")
                if name:
                    songs.append(name)
    except (KeyError, IndexError):
        print("[red]This setlist doesn't contain a valid set of songs.[/red]")
        exit()

    return songs



def process_setlists_from_file(file_path, access_token, playlist_id):
    try:
        with open(file_path, "r") as f:
            urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"[red]❌ File not found: {file_path}[/red]")
        return

    all_added = 0

    for url in urls:
        try:
            songs, artist_name = get_setlist_from_url(url)
        except Exception as e:
            print(f"[yellow]⚠️ Skipping invalid setlist: {url} — {e}[/yellow]")
            continue

        if not songs:
            print(f"[yellow]⚠️ No songs found in setlist: {url}[/yellow]")
            continue

        print(f"\n🎤 Adding {len(songs)} songs from [bold]{artist_name}[/bold]'s setlist...")
        added = add_songs_to_playlist(access_token, songs, artist_name, playlist_id)
        all_added += added

    print(f"\n[green]✅ Finished. Added {all_added} songs in total.[/green]")




# Main CLI Flow
import click
from rich.prompt import Prompt
from rich import print
from rich.prompt import Confirm

from rich.prompt import Prompt, Confirm

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Add setlist.fm songs to a Spotify playlist.")
    parser.add_argument("--playlist", help="Spotify playlist URL")
    parser.add_argument("--file", help="Path to a text file with Setlist.fm URLs")
    parser.add_argument("--setlist", help="Single Setlist.fm URL")
    args = parser.parse_args()

    access_token = get_spotify_token()
    user_id = get_current_user_id(access_token)

    if not user_id:
        print("[red]❌ Could not retrieve Spotify user ID.[/red]")
        return

    if args.playlist:
        playlist_id = extract_playlist_id(args.playlist)
        if not playlist_id:
            print("[red]❌ Invalid Spotify playlist URL.[/red]")
            return
    else:
        
        # Ask whether to create a new playlist or use an existing one
        create_new = Confirm.ask("Do you want to create a new Spotify playlist?", default=False)

        if create_new:
            playlist_name = Prompt.ask("Enter new playlist name")
            playlist_description = Prompt.ask("Playlist description", default="")
            playlist_id = create_spotify_playlist(access_token, user_id, playlist_name, playlist_description)
            if not playlist_id:
                print("[red]❌ Playlist creation failed.[/red]")
                return
        else:
            playlist_id = Prompt.ask("Enter existing Spotify playlist ID")
            playlist_id = extract_playlist_id(playlist_id)

    if args.setlist:
        # Use single setlist from CLI
        setlist_url = args.setlist
        songs, artist_name = get_setlist_from_url(setlist_url)
        if not songs:
            print("[yellow]⚠️ No songs found in setlist.[/yellow]")
            return
        print(f"\n🎤 Adding {len(songs)} songs from [bold]{artist_name}[/bold]'s setlist...")
        added = add_songs_to_playlist(access_token, songs, artist_name, playlist_id)
        print(f"[green]✅ Added {added} songs to the playlist.[/green]")

    elif args.file:
        # Use file of setlists from CLI
        process_setlists_from_file(args.file, access_token, playlist_id)

    else:


        # Ask whether user wants to add from a single URL or a file
        mode = Prompt.ask(
            "Add songs from a [bold]single[/bold] setlist or from a [bold]file[/bold]?",
            choices=["single", "file"], default="single"
        )

        if mode == "single":
            setlist_url = Prompt.ask("Enter Setlist.fm setlist URL")
            try:
                songs, artist_name = get_setlist_from_url(setlist_url)
            except Exception as e:
                print(f"[red]❌ Failed to process setlist: {e}[/red]")
                return

            if not songs:
                print("[yellow]⚠️ No songs found in setlist.[/yellow]")
                return

            print(f"\n🎤 Adding {len(songs)} songs from [bold]{artist_name}[/bold]'s setlist...")
            added = add_songs_to_playlist(access_token, songs, artist_name, playlist_id)
            print(f"[green]✅ Added {added} songs to the playlist.[/green]")

        elif mode == "file":
            file_path = Prompt.ask("Enter path to text file with Setlist.fm URLs")
            process_setlists_from_file(file_path, access_token, playlist_id)


if __name__ == "__main__":
    main()
