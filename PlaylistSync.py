from functions import *

### System Variables
scriptName = 'Playlist Sync'

def main():
    print(f'### Initialising {colored(scriptName, "white", attrs=["bold"])}...')
    sourcePlaylist = sourcePlexServer.library.section(sourceMusicLibrary).playlist(sourcePlaylistName)

    foundTracks=[]

    copiedTracks, skippedTracks, errorTracks = 0, 0, 0
    progressTitle = f'### Identifying tracks from {colored(sourcePlaylistName, sourcePlaylistColour, attrs=["bold"])}'
    with alive_bar(len(sourcePlaylist), enrich_print=False, title=progressTitle, title_length=(titleLength+13), dual_line=True) as bar:
        for track in sourcePlaylist:
            bar.text = f'## {colored(track.grandparentTitle, artistColour, attrs=["bold"])} - {colored(track.title, trackColour, attrs=["bold"])}'

            ## Search using title as GUIDs differ bewtween PMS's
            try:
                artistSearch = targetPlexServer.library.section(targetMusicLibrary).search(title=track.grandparentTitle, libtype='artist')
                artist = refineList(artistSearch, track)
            except:
                skippedTracks+=1
                print(f'## Cannot find artist {colored(track.grandparentTitle, artistColour, attrs=["bold"])} on {colored(targetServerName, targetServerColour, attrs=["bold"])}. Skipping track...')
                bar()
                continue

            ## Search using GUID as its the same server
            try:
                albumSearch = artist.albums()
                albumConfirmation = sourcePlexServer.library.section(sourceMusicLibrary).search(guid=track.parentGuid, libtype='album')
                album = refineList(albumSearch, albumConfirmation[0])
            except:
                skippedTracks+=1
                print(f'## Cannot find album {colored(track.parentTitle, albumColour, attrs=["bold"])} on {colored(targetServerName, targetServerColour, attrs=["bold"])}. Skipping track...')
                bar()
                continue

            ## Counting on album selection to be accurate enough not to need to verify track
            try:
                trackSearch = album.tracks()
                track = refineList(trackSearch, track)
            except:
                skippedTracks+=1
                print(f'## Cannot find track {colored(track.title, trackColour, attrs=["bold"])} on {colored(targetServerName, targetServerColour, attrs=["bold"])}. Skipping track...')
                bar()
                continue

            ## Store found tracks to an array
            try:
                foundTracks.append(track)
                bar()
            except:
                print(f'Cannot add {track.title} to array')
                errorTracks+=1
                bar()
                continue

    # Check to see if playlist already exists, if not create it
    try:
        targetPlaylist = targetPlexServer.playlist(targetPlaylistName)
    except NotFound:
        print(f'## Creating playlist {colored(targetPlaylistName, targetPlaylistColour, attrs=["bold"])} on {colored(targetServerName, targetServerColour, attrs=["bold"])}')
        targetPlaylist = Playlist.create(targetPlexServer, targetPlaylistName, items=foundTracks)

    # Add tracks to playlist
    progressTitle = f'### Adding tracks to {colored(targetPlaylistName, targetPlaylistColour, attrs=["bold"])}'
    with alive_bar(len(sourcePlaylist), enrich_print=False, title=progressTitle, title_length=(titleLength+13), dual_line=True) as bar:
        for track in foundTracks:
            bar.text = f'## {colored(track.grandparentTitle, albumColour, attrs=["bold"])} - {colored(track.title, trackColour, attrs=["bold"])}'
            ## Check if track already exists in playlist
            try:
                ## If so skip
                if track in targetPlaylist.items():
                    # print(f'## {colored(track.title, "white", attrs=["bold"])} already on {colored(targetPlaylistName, "cyan", attrs=["bold"])}')
                    skippedTracks+=1
            except NotFound:
                # Otherwise add track to playlist
                targetPlaylist.addItems(track)
                copiedTracks+=1

            bar()

    print(f'### {colored(copiedTracks, copiedTracksColour, attrs=["bold"])} tracks added to playlist on {colored(targetServerName, targetServerColour, attrs=["bold"])} - Tracks skipped: {colored(skippedTracks, skippedTracksColour, attrs=["bold"])} - Track Errors: {colored(errorTracks, errorTracksColour, attrs=["bold"])}')
    


if __name__ == "__main__":
    main()