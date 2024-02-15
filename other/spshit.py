import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Set up your Spotify API credentials
client_id = 'YOUR_SPOTIFY_CLIENT_ID'
client_secret = 'YOUR_SPOTIFY_CLIENT_SECRET'

# Authenticate with the Spotify API
auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(auth_manager=auth_manager)

def get_song_attributes(sname):
    # Search for the song using the Spotify API
    resultss = sp.search(q=sname, type='track', limit=3)

    # Initialize an empty list to store the results
    song_results = []

    # Iterate through paginated results
    for track in resultss['tracks']['items']:
        # Extract relevant attributes
        artists = [artist['name'] for artist in track['artists']]
        external_urls = track['external_urls']
        popularity = track['popularity']
        asnme = track['name']  # Extract the song name

        # Extract album information, including the image URL
        album_info = track['album']
        image_url = album_info['images'][0]['url'] if album_info['images'] else None

        # Append the attributes to the results list
        song_results.append({
            'artists': artists,
            'external_urls': external_urls,
            'song_name': asnme,
            'popularity': popularity,
            'image_url': image_url
        })

    return song_results
