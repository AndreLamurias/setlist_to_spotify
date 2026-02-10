from flask import Flask, render_template, request, redirect, session, url_for, flash
import os
from spotify_helper import (
    get_auth_url, REDIRECT_URI, SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET,
    get_current_user_id, create_spotify_playlist, add_songs_to_playlist, extract_playlist_id
)
from cli import get_setlist_from_url
import requests

app = Flask(__name__)
app.secret_key = os.urandom(24)

@app.route('/')
def index():
    return render_template('index.html', logged_in='token' in session)

@app.route('/login')
def login():
    return redirect(get_auth_url())

@app.route('/callback')
def callback():
    code = request.args.get('code')
    res = requests.post("https://accounts.spotify.com/api/token", data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": SPOTIFY_CLIENT_ID,
        "client_secret": SPOTIFY_CLIENT_SECRET
    })
    session['token'] = res.json().get('access_token')
    return redirect(url_for('index'))

@app.route('/sync', methods=['POST'])
def sync():
    token = session.get('token')
    if not token:
        return redirect(url_for('login'))

    setlist_url = request.form.get('setlist_url')
    mode = request.form.get('playlist_mode')  # 'new' or 'existing' 
    #playlist_url = request.form.get('playlist_url')
    
    if not setlist_url:
        flash("Setlist URL is required.")
        return redirect(url_for('index'))

    try:
        # 1. Get Songs
        songs, artist = get_setlist_from_url(setlist_url)
        user_id = get_current_user_id(token)
        playlist_id = None

        # 2. Determine Playlist Destination
        if mode == 'new':
            name_input = request.form.get('new_playlist_name')
            # Default to Artist Name if input is empty
            final_name = name_input if name_input else f"{artist} Setlist"
            playlist_id = create_spotify_playlist(token, user_id, final_name, "Created via Web App")
            
        elif mode == 'existing':
            playlist_url = request.form.get('existing_playlist_url')
            if playlist_url:
                playlist_id = extract_playlist_id(playlist_url)
            
            if not playlist_id:
                flash("Invalid existing playlist URL.")
                return redirect(url_for('index'))

        # 3. Add songs
        added_count = add_songs_to_playlist(token, songs, artist, playlist_id)
        
        flash(f"Successfully added {added_count} songs to your playlist!")
    except Exception as e:
        flash(f"Error: {str(e)}")

    return redirect(url_for('index'))

if __name__ == '__main__':
    print(f"DEBUG: Client ID is {SPOTIFY_CLIENT_ID}")
    if not SPOTIFY_CLIENT_ID:
        print("❌ ERROR: SPOTIFY_CLIENT_ID is missing from .env file!")
        exit()
    app.run(port=8888, debug=True)