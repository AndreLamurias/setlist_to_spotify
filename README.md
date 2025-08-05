# Setlist to spotify

Script to retrieve setlists from setlist.fm and add the songs to a spotify playlist.

It can receive the setlist link from the command line or read a file with one setlist link per line.

It can also add the songs to an existing playlist or to a new one.

Note: Most of the code was made with ChatGPT.

## Setup
1. **Spotify API Keys**

Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard):

- Create an app  
- Note the **Client ID** and **Client Secret**  
- Set a **Redirect URI** to: `http://localhost:8888/callback`  

2. **Setlist.fm API Key**

- Sign up at [https://api.setlist.fm/docs/](https://api.setlist.fm/docs/)
- Get your API key

3. **Create a `.env` file**

```env
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SETLIST_FM_API_KEY=your_setlist_fm_api_key
REDIRECT_URI=http://localhost:8888/callback
```


## Usage

```bash
python cli.py
```

You’ll be prompted to either create a playlist or add songs to an existing one, and to choose a Setlist.fm URL or file of URLs.


```bash
cli.py  --file .\pdc.txt
```

**Add many setlists from a file**


```bash
cli.py --playlist https://open.spotify.com/playlist/5EOKPnynRSKHTFNN1r8Buq?si=62d645a8ab994e09 --file kglw_setlists.txt
```

**Add many setlists from a file to a specific playlist.**


```bash
cli.py --playlist https://open.spotify.com/playlist/5EOKPnynRSKHTFNN1r8Buq?si=62d645a8ab994e09 --setlist https://www.setlist.fm/setlist/air/2025/parque-do-ibirapuera-sao-paulo-brazil-3b51b4dc.html
```

**Add a single setlist to a specific playlist.**
