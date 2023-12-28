import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Set up your Spotify API credentials
client_id = '8152067cbd434f5985aaf83ca5dfcae6'
client_secret = '057dcc11e7654601bddd827d45984d03'


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

song_name = "see you again wiz"
results = get_song_attributes(song_name)
lisr = []
for index, result in enumerate(results, start=1):
    if 0 <= result['popularity'] <= 33:
        rating = '\U00002b50 (Unpopular)'
    elif 33 <= result['popularity'] <= 66:
        rating = '\U0001f31f (Quite Popular)'
    else:
        rating = '\U00002728 (Very Popular)'
    lisr.append(f'Result {index}:\n'
                f'**Song Name**: {result['song_name']}\n'
                f'**Artist(s)**: {', '.join(result['artists'])}\n'
                f'Track URL: [Click Here]({result['external_urls']['spotify']})\n'
                f'Popularity: {result['popularity']} {rating}')