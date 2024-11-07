from functions import *

### System variables
scriptName = 'Playlist Import'

sourceSearchFilter = { 'userRating>>': '0' }
sourceTracksCache=(f'source{sourceServerName}Cache.pkl')

targetSearchFilter = {}
targetTracksCache=(f'target{targetServerName}Cache.pkl')

### Loads data from a PMS or local file. Can save to a local file
def getTrackValues(plexServer, tracksCache, libraryName, searchFilter={}):
    serverName = plexServer.friendlyName
    
    ### Check if existing trackCache already exists, if so load it.
    if loadServerData == 'True':
        if os.path.isfile(tracksCache):
            progressTitle = f'### Reading liked tracks from {tracksCache}'.ljust(titleLength)
            with alive_bar(1, title=progressTitle) as bar:
                with open(tracksCache, 'rb') as file:
                    trackValues = dill.load(file)
                    bar()
    else:
        ### Load tracks from the PMS
            with alive_bar(1, title=f'### Reading liked tracks from {colored(serverName, sourceServerColour, attrs=["bold"])} PMS'.ljust(titleLength)) as bar:
                trackValues = plexServer.library.section(libraryName).all(libtype='track', filters=searchFilter)
                bar()

    ### Save data to local file
    if saveServerData == 'True':
        with alive_bar(1, title=f'### Writing {tracksCache} to disk'.ljust(titleLength)) as bar:
            file = open(tracksCache, 'wb')
            dill.dump(trackValues, file)
            file.close()
            bar()

    print(f'### {colored(serverName, sourceServerColour, attrs=["bold"])} liked tracks: {colored(len(trackValues), likedTracksColour, attrs=["bold"])}')
    return trackValues

def main():
    print(f'### Initialising {colored(scriptName, "white", attrs=["bold"])}...')
    sourceTracks = getTrackValues(sourcePlexServer, sourceTracksCache, sourceMusicLibrary, sourceSearchFilter)
    sourceTracks = dedupe(sourceTracks, sourceServerName)
    # targetTracks = getTrackValues(targetTracksCache, targetServerName, targetSearchFilter)

    ### Sync ratings between source and target server
    ratedTracks, skippedTracks, errorTracks = 0, 0, 0
    progressTitle = f'### Syncing ratings from {colored(sourceServerName, sourceServerColour, attrs=["bold"])} to {colored(targetServerName, targetServerColour, attrs=["bold"])}'
    with alive_bar(len(sourceTracks), enrich_print=False, title=progressTitle, title_length=(titleLength+13), dual_line=True) as bar:
        for sourceTrack in sourceTracks:
            bar.text = f'## {colored(sourceTrack.grandparentTitle, artistColour, attrs=["bold"])} - {colored(sourceTrack.title, trackColour, attrs=["bold"])}'

            ## Search using title as GUIDs differ bewtween PMS's
            try:
                artistSearch = targetPlexServer.library.section(targetMusicLibrary).search(title=sourceTrack.grandparentTitle, libtype='artist')
                artist = refineList(artistSearch, sourceTrack)
            except:
                errorTracks+=1
                print(f'## Cannot find artist {colored(sourceTrack.grandparentTitle, artistColour, attrs=["bold"])} on {colored(targetServerName, targetServerColour, attrs=["bold"])}. Skipping track...')
                bar()
                continue

            ## Search using GUID as its the same server
            try:
                albumSearch = artist.albums()
                albumConfirmation = sourcePlexServer.library.section(sourceMusicLibrary).search(guid=sourceTrack.parentGuid, libtype='album')
                album = refineList(albumSearch, albumConfirmation[0])
            except:
                errorTracks+=1
                print(f'## Cannot find album {colored(sourceTrack.parentTitle, albumColour, attrs=["bold"])} on {colored(targetServerName, targetServerColour, attrs=["bold"])}. Skipping track...')
                bar()
                continue

            ## Counting on album selection to be accurate enough not to need to verify track
            try:
                trackSearch = album.tracks()
                track = refineList(trackSearch, sourceTrack)
            except:
                errorTracks+=1
                print(f'## Cannot find track {colored(sourceTrack.title, trackColour, attrs=["bold"])} on {colored(targetServerName, targetServerColour, attrs=["bold"])}. Skipping track...')
                bar()
                continue

            if track.userRating != sourceTrack.userRating:
                track.rate(sourceTrack.userRating)
                ratedTracks+=1
            else:
                # print(f"Skipping: {track.title}. Already rated correctly.")
                skippedTracks+=1

            bar()

        bar.title =  f'### Ratings from {colored(sourceServerName, sourceServerColour, attrs=["bold"])} synced to {colored(targetServerName, targetServerColour, attrs=["bold"])}'

    print(f'### {colored(ratedTracks, ratedTracksColour, attrs=["bold"])} ratings synced from {colored(sourceServerName, sourceServerColour, attrs=["bold"])} to {colored(targetServerName, targetServerColour, attrs=["bold"])} - Tracks skipped: {colored(skippedTracks, skippedTracksColour, attrs=["bold"])} - Track Errors: {colored(errorTracks, errorTracksColour, attrs=["bold"])}')

if __name__ == "__main__":
    main()