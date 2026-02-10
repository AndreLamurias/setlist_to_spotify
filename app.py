import threading
import uuid
import time
from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
import os
from spotify_helper import (
    get_auth_url, REDIRECT_URI, SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET,
    get_current_user_id, create_spotify_playlist, add_songs_to_playlist, extract_playlist_id
)
from cli import get_setlist_from_url
import requests

app = Flask(__name__)
app.secret_key = os.urandom(24)


task_status = {}

def background_sync(task_id, token, setlist_url, playlist_mode, new_name, existing_url):
    try:
        # 1. Get Songs
        songs, artist = get_setlist_from_url(setlist_url)
        if not songs:
            task_status[task_id] = {'finished': True, 'success': False, 'message': "No songs found."}
            return

        # 2. Get/Create Playlist
        user_id = get_current_user_id(token)
        playlist_id = None

        if playlist_mode == 'new':
            final_name = new_name if new_name else f"{artist} Setlist"
            playlist_id = create_spotify_playlist(token, user_id, final_name, "Created via Web App")
        elif playlist_mode == 'existing':
            if existing_url:
                playlist_id = extract_playlist_id(existing_url)

        if not playlist_id:
            task_status[task_id] = {'finished': True, 'success': False, 'message': "Invalid Playlist ID."}
            return

        # Define the callback to update global dict
        def update_progress(current, total, message):
            task_status[task_id].update({
                'current': current,
                'total': total,
                'status': message,
                'percent': int((current / total) * 100) if total > 0 else 0
            })

        # 3. Add songs with callback
        added_count = add_songs_to_playlist(token, songs, artist, playlist_id, progress_callback=update_progress)
        
        # Mark complete
        task_status[task_id].update({
            'finished': True, 
            'success': True, 
            'message': f"Done! Added {added_count} songs.",
            'percent': 100
        })

    except Exception as e:
        task_status[task_id] = {'finished': True, 'success': False, 'message': f"Error: {str(e)}"}

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

@app.route('/start_sync_job', methods=['POST'])
def start_sync_job():
    token = session.get('token')
    if not token:
        return jsonify({'error': 'Not logged in'}), 401

    # Generate a unique ID for this job
    task_id = str(uuid.uuid4())
    
    # Initialize status
    task_status[task_id] = {
        'current': 0, 'total': 1, 'status': 'Starting...', 'percent': 0, 'finished': False
    }

    # Extract form data
    data = request.json
    thread = threading.Thread(target=background_sync, args=(
        task_id, 
        token, 
        data.get('setlist_url'), 
        data.get('playlist_mode'), 
        data.get('new_playlist_name'), 
        data.get('existing_playlist_url')
    ))
    thread.start()

    return jsonify({'task_id': task_id})

@app.route('/status/<task_id>')
def status(task_id):
    return jsonify(task_status.get(task_id, {'error': 'Unknown task'}))

if __name__ == '__main__':
    print(f"DEBUG: Client ID is {SPOTIFY_CLIENT_ID}")
    if not SPOTIFY_CLIENT_ID:
        print("❌ ERROR: SPOTIFY_CLIENT_ID is missing from .env file!")
        exit()
    app.run(port=8888, debug=True)