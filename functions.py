import os
import re
import dill
import math
import shutil
from plexapi.server import PlexServer
from plexapi.server import Playlist
from plexapi.exceptions import NotFound
from alive_progress import alive_bar
from termcolor import colored
from dotenv import load_dotenv

### --- Docs ---
## plexapi - https://python-plexapi.readthedocs.io/en/latest/introduction.html

### --- Notes ---
## alive_bar: ANSI colour codes from termcolor consume characters but are invisible. For each coloured and bold sub string, 13 characters are consumed.
## To keep things neat the same number of formatted substrings should be used when bar.title is initialised and when updated to show completion of a loop.
## e.g. titleLength+13 for 1 formatted substring, titleLength+26 for 2 formatted substrings, etc. Add 13 characters for each substring used.

### --- Variables ---
### Load .env variables
if os.path.exists('.env'):
    load_dotenv('.env')
    ## Universal variables
    sourceServerURL = os.getenv('SOURCE_SERVER_URL')
    sourceServerToken = os.getenv('SOURCE_SERVER_TOKEN')
    sourceMusicLibrary = os.getenv('SOURCE_LIBRARY_NAME')
    targetServerURL = os.getenv('TARGET_SERVER_URL')
    targetServerToken = os.getenv('TARGET_SERVER_TOKEN')    
    targetMusicLibrary = os.getenv('TARGET_LIBRARY_NAME')
    outputDirectory = os.getenv('OUTPUT_DIRECTORY')
    ## Script specific variables
    # RatingsSync.py
    saveServerData = os.getenv('SAVE_SERVER_DATA')
    loadServerData = os.getenv('LOAD_SERVER_DATA')
    # PlaylistSync.py    
    sourcePlaylistName = os.getenv('SOURCE_PLAYLIST_NAME')
    targetPlaylistName = os.getenv('TARGET_PLAYLIST_NAME')
    # PlaylistImport.py
    m3uPlaylistName = os.getenv('M3U_PLAYLIST_NAME')
    m3uPlaylistPath = os.getenv('M3U_PLAYLIST_PATH')
    m3uPlaylistColour = os.getenv('M3U_PLAYLIST_COLOUR')
    userMediaPath = os.getenv('USER_MEDIA_PATH')
    importPlaylistBehaviour = os.getenv('IMPORT_PLAYLIST_BEHAVIOUR').lower()
    # PlaylistExport.py
    playlistToExport = os.getenv('PLAYLIST_TO_EXPORT')
    customLibraryPath = os.getenv('CUSTOM_LIBRARY_PATH')
    includeM3UMetadata = os.getenv('INCLUDE_M3U_METADATA')
    createPortablePlaylist = os.getenv('CREATE_PORTABLE_PLAYLIST')
    exportPlaylistBehaviour = os.getenv('EXPORT_PLAYLIST_BEHAVIOUR').lower()
    ## alive_progress variables
    titleLength = int(os.getenv('TITLE_LENGTH'))
    ## Set colours
    if os.getenv('DISABLE_COLOURS') == 'True':
        os.environ['NO_COLOR'] = '1'
    else:        
        ## Universal colour variables
        sourceServerColour = os.getenv('SOURCE_SERVER_COLOUR')
        targetServerColour = os.getenv('TARGET_SERVER_COLOUR')
        likedTracksColour = os.getenv('LIKED_TRACKS_COLOUR')
        artistColour = os.getenv('ARTIST_COLOUR')
        albumColour = os.getenv('ALBUM_COLOUR')
        trackColour = os.getenv('TRACK_COLOUR')
        # RatingsSync.py
        ratedTracksColour = os.getenv('RATED_TRACKS_COLOUR')
        # RatingsSync.py & PlaylistSync.py & PlaylistImport.py
        skippedTracksColour = os.getenv('SKIPPED_TRACKS_COLOUR')
        errorTracksColour = os.getenv('ERROR_TRACKS_COLOUR')
        # PlaylistSync.py & PlaylistImport.py
        sourcePlaylistColour = os.getenv('SOURCE_PLAYLIST_COLOUR')
        targetPlaylistColour = os.getenv('TARGET_PLAYLIST_COLOUR')
        copiedTracksColour = os.getenv('COPIED_TRACKS_COLOUR')
else:
    print("### Error: .env file not found. Cannot continue.")
    print('### Please look at example.env.')
    print('### Exiting...')
    exit()

### System Variables
sourcePlexServer = PlexServer(sourceServerURL, sourceServerToken)
sourceServerName = sourcePlexServer.friendlyName
sourceSectionName = sourcePlexServer.library.section(sourceMusicLibrary)

targetPlexServer = PlexServer(targetServerURL, targetServerToken)
targetServerName = targetPlexServer.friendlyName
targetSectionName = targetPlexServer.library.section(targetMusicLibrary)

### --- Functions ---
### searches through a list of items for a specific match
def refineList(itemList, searchItem):
    for item in itemList:
        match item.TYPE:
            case 'artist':
                if item.title == searchItem.grandparentTitle:
                    return item                
            case 'album':
                if item.title == searchItem.title and item.year == searchItem.year and item.type == searchItem.type:
                    return item
            case 'track':
                if item.title == searchItem.title and item.trackNumber == searchItem.trackNumber:
                    return item
            case _:
                print(f'Error. Exiting...')
                exit()
    if item == None:
        print(f'No Matching item for {searchItem.title} Found. Skipping I guess. 🤷‍♂️')

### Dedupe dictionaries (and maybe others?)
def dedupe(item, serverName):
    result = []
    seen = set()
    progressTitle = f'### Deduping {colored(serverName, sourceServerColour, attrs=["bold"])} liked tracks'
    with alive_bar(len(item), enrich_print=False, title=progressTitle.ljust(titleLength), title_length=titleLength, dual_line=True) as bar:
        for trackValue in item:
            bar.text = f'{colored(trackValue.title, trackColour, attrs=["bold"])}'

            signature = (trackValue.guid)
            if signature in seen:
                bar()
                continue

            seen.add(signature)
            result.append(trackValue)
            bar()
        bar.title = f'### Deduping liked tracks {colored("completed!", "white", attrs=["bold"])}'
        print(f'### {colored(serverName, sourceServerColour, attrs=["bold"])} deduped liked tracks: {colored(len(result), likedTracksColour, attrs=["bold"])}')
        return result
    
### Remove featured artists from string
def removeFtArtists(string):
    if 'feat.' in string:
        return string.split('feat.')[0].strip()
    elif 'ft.' in string:        
        return string.split('ft.')[0].strip()
    else:
        return string
    
### Remove special characters from string
def removeSpecialChars(string):
    pattern = r'[^a-zA-Z0-9\s]' #Any non alphanumeric character + whitespace
    # pattern = r'[^a-zA-Z0-9\s\-\_\.\(\)\[\]\,\@\&\+\=\~\{\}\$\!\#\'\"]' # Same but allowed special chars
    match = re.sub(pattern, '', string)
    return match

# Function to escape ANSI codes
def countAnsiColourCharacters(string, colouredString):
    colouredString = colouredString.replace('\033', '\\033')
    ANSICharCount = len(colouredString)-len(string)
    return ANSICharCount