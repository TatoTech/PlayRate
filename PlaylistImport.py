from functions import *

### System Variables
scriptName = 'Playlist Import'

def main():
    print(f'### Initialising {colored(scriptName, "white", attrs=["bold"])}...')

    ### Open m3u playlist
    with open(m3uPlaylistPath, 'r') as m3uPlaylist:
        playlistItems = m3uPlaylist.readlines()

    # Add each line that does not contain meta data to the array
    trackPaths = [playlistItem.strip() for playlistItem in playlistItems if not playlistItem.startswith('#')]

    # Verify track paths in m3u do exist
    verifiedTracks, unverifiedTracks = 0, 0
    progressTitle = f'### Verifying {colored(len(trackPaths),"white", attrs=["bold"])} track paths in {colored(m3uPlaylistName, m3uPlaylistColour, attrs=["bold"])} M3U playlist'
    with alive_bar(len(trackPaths), enrich_print=False, title=progressTitle, title_length=(titleLength+26), dual_line=True) as bar:
        for path in trackPaths:
            if os.path.exists(path):
                bar.text = f'The file {colored(path, "white", attrs=["bold"])} {colored("does", "green", attrs=["bold"])} exist.' 
                verifiedTracks+=1
            else:
                print(f'## The file {colored(path, "white", attrs=["bold"])} {colored("does not", "red", attrs=["bold"])} exist.')
                unverifiedTracks+=1
            bar()
        bar.title = f'### M3U Track Paths: {colored(verifiedTracks, "green", attrs=["bold"])} verified - {colored(unverifiedTracks, "red", attrs=["bold"])} unverified'

    ### Split the track path up to determine artist, album, and track
    splitMediaPath = userMediaPath.split(os.path.sep)
    noUnwantedChunks = len(splitMediaPath)
    identifiedTracks = 0
    artists, releases, tracks = [], [], []

    progressTitle = f'### Identifying Artists, Releases, and Tracks from {colored(m3uPlaylistName, m3uPlaylistColour, attrs=["bold"])}'
    with alive_bar(len(trackPaths), enrich_print=False, title=progressTitle, title_length=(titleLength+13), dual_line=True) as bar:
        for path in trackPaths: # For each track in playlist
            i = 0
            for pathChunk in path.split(os.path.sep): # Split string into chunks
                if pathChunk not in splitMediaPath: # Remove USER_MEDIA_PATH chunks
                    ### Determine Artist, Release, and Tracks
                    match (i-noUnwantedChunks) % 3:
                        case 0:
                            trackChunk = pathChunk.rsplit('.', 1)[0]
                            trackName = trackChunk.split(' ', 1)[1]
                            tracks.append(trackName)
                            identifiedTracks+=1 # Only track counts. Else tracks get counted multiple times.
                        case 1:
                            artists.append(pathChunk)
                        case 2:
                            releases.append(pathChunk)
                        case _:
                            print(f'Error: Unable to determine artist, release, or track name. Exiting...')
                            exit()
                    i+=1
            bar()
        bar.title = f'### M3U Playlist:    {colored(identifiedTracks,"green", attrs=["bold"])} identified'


    ### Match artists on PMS
    matchedTracks, skippedTracks, i = 0, 0, 0
    forbiddenArtists = ['Soundtracks', 'Various Artists']
    pmsTracks = []
    progressTitle = f'### Matching tracks from {colored(m3uPlaylistName, m3uPlaylistColour, attrs=["bold"])} on {colored(targetPlexServer.friendlyName, targetServerColour, attrs=["bold"])}'
    with alive_bar(len(trackPaths), enrich_print=False, title=progressTitle, title_length=(titleLength+26), dual_line=True) as bar:
        for artist in artists:
            ### Search in the target music library for the artist
            try:
                ### Various Artists will break this script. Deal with them seperately.
                if artist not in forbiddenArtists:
                    artistSearch = targetSectionName.search(title=artist, libtype='artist')
                    if artistSearch[0].title == artists[i]:
                        pmsArtist = artistSearch[0]
                else:
                    pmsArtist = "FORBIDDEN_ARTIST"
                    # print(f'## {pmsArtist} is a forbidden artist. Cannot search.')
            except:
                skippedTracks+=1
                print(f'## Cannot find artist {colored(pmsArtist, artistColour, attrs=["bold"])} on {colored(targetServerName, targetServerColour, attrs=["bold"])}. Skipping track...')
                i+=1
                bar()
                continue
            
            ### Using found artist, list all albums, interate through and match with known album name
            try:
                if pmsArtist != 'FORBIDDEN_ARTIST':
                    releaseSearch = pmsArtist.albums()
                else:
                    questions = ['who', 'what', 'why', 'when', 'how']
                    if any(question in releases[i].lower() for question in questions):
                        releaseName = releases[i].replace('_','?')
                    else:
                        releaseName = releases[i].replace('_',':')
                    releaseSearch = targetSectionName.search(title=releaseName, libtype='album')

                for item in releaseSearch:
                        ## Special characters removed as certain OS's can't handle them in filenames (which is where we get them from for this)
                        if removeSpecialChars(item.title) == removeSpecialChars(releases[i]):
                            releaseConfirmation = item

                release = refineList(releaseSearch, releaseConfirmation)
            except:
                skippedTracks+=1
                print(f'## Cannot find release {colored(releases[i], albumColour, attrs=["bold"])} on {colored(targetServerName, targetServerColour, attrs=["bold"])}. Skipping track...')
                i+=1
                bar()
                continue

            ### Using found album, list all tracks, iterate through and match with known track name
            try:
                bar.text(f'## Searching for {colored(removeFtArtists(artists[i]), artistColour, attrs=["bold"])} - {colored(removeSpecialChars(tracks[i]), trackColour, attrs=["bold"])}')
                trackSearch = release.tracks()
                for item in trackSearch:
                    ## Featured artists removed as Plex show them in artist field. Special characters too.
                    if removeSpecialChars(item.title) == removeSpecialChars(removeFtArtists(tracks[i])):
                        trackConfirmation = item
                track = refineList(trackSearch, trackConfirmation)
                pmsTracks.append(track)
                matchedTracks+=1
            except:
                skippedTracks+=1
                print(f'## Cannot find track {colored(removeFtArtists(tracks[i]), trackColour, attrs=["bold"])} on {colored(targetServerName, targetServerColour, attrs=["bold"])} Skipping track...')
                i+=1
                bar()
                continue

            i+=1
            bar()
        bar.title=f'### PMS Server:      {colored(matchedTracks, ratedTracksColour, attrs=["bold"])} matched - {colored(skippedTracks, skippedTracksColour, attrs=["bold"])} skipped'
   
    ### Create playlist
    appendedTracks, skippedTracks, preexistingTracks, removedTracks = 0, 0, 0, 0
    targetExistingPlaylists = targetPlexServer.playlists()

    ### Replace - Remove existing playlist and create from scratch
    if importPlaylistBehaviour == 'replace':
        progressTitle = f'### Creating {colored(m3uPlaylistName, m3uPlaylistColour, attrs=["bold"])} on {colored(targetServerName, targetServerColour, attrs=["bold"])}'
        with alive_bar(len(targetExistingPlaylists), enrich_print=False, title=progressTitle, title_length=(titleLength+26), dual_line=True) as bar:
            ### Delete existing playlists with the same name
            for pmsPlaylist in targetExistingPlaylists:
                if pmsPlaylist.title == m3uPlaylistName:
                    pmsPlaylistName = pmsPlaylist.title
                    pmsPlaylist.delete()
                    bar.text = f'## Playlist {colored(pmsPlaylist.title, m3uPlaylistColour, attrs=["bold"])} deleted!'
                bar()

            Playlist.create(targetPlexServer, m3uPlaylistName, section=targetSectionName, items=pmsTracks)

            bar.title = (f'### PMS Playlist:    {colored(pmsPlaylistName, m3uPlaylistColour, attrs=["bold"])} on {colored(targetServerName, targetServerColour, attrs=["bold"])} replaced')
    
    ### Sync - Remove unwanted tracks, then run append code
    if importPlaylistBehaviour == 'sync':
        progressTitle = f'### Removing {colored(len(pmsTracks),"white", attrs=["bold"])} unwated tracks from {colored(m3uPlaylistName, m3uPlaylistColour, attrs=["bold"])} on {colored(targetServerName, targetServerColour, attrs=["bold"])}'
        for pmsPlaylist in targetExistingPlaylists:
            if pmsPlaylist.title == m3uPlaylistName:
                ## Compare playlist tracks with pmsTracks to determine what needs to be removed
                for playlistTrack in pmsPlaylist:
                    if playlistTrack not in pmsTracks:
                        removedTracks+=1
                        bar.text = f'## {colored(removeFtArtists(playlistTrack.title), trackColour, attrs=["bold"])} removed from playlist.'
                        pmsPlaylist.removeItems(playlistTrack)

    ### Append - Add missing tracks to playlist
    if importPlaylistBehaviour == 'append' or importPlaylistBehaviour == 'sync':
        progressTitle = f'### Appending {colored(len(pmsTracks),"white", attrs=["bold"])} tracks to {colored(m3uPlaylistName, m3uPlaylistColour, attrs=["bold"])} on {colored(targetServerName, targetServerColour, attrs=["bold"])}'
        for pmsPlaylist in targetExistingPlaylists:
            if pmsPlaylist.title == m3uPlaylistName:
                with alive_bar(len(pmsTracks), enrich_print=False, title=progressTitle, title_length=(titleLength+39), dual_line=True) as bar:
                    ## Compare pmsTracks with playlist items and only add the new
                    for track in pmsTracks: ## Loop through playlist
                        if track not in pmsPlaylist: ## Check if it needs to be added
                            appendedTracks+=1
                            pmsPlaylist.addItems(track)
                            bar.text = f'## {colored(removeFtArtists(track.title), trackColour, attrs=["bold"])} added to playlist'
                        elif track in pmsPlaylist:
                            preexistingTracks+=1
                            bar.text = f'## {colored(removeFtArtists(track.title), trackColour, attrs=["bold"])} already on playlist'
                        else:
                            skippedTracks+=1
                            bar.text = f'## {colored(removeFtArtists(track.title), trackColour, attrs=["bold"])} error. Skipping...'
                        bar()
                    bar.title = (f'### PMS Playlist:    {colored(appendedTracks, "green", attrs=["bold"])} appended - {colored(preexistingTracks, "yellow", attrs=["bold"])} pre-exist - {colored(removedTracks, "red", attrs=["bold"])} removed')
                    # Temp till I find a use for it or remove it
                    if skippedTracks >= 1:
                        print(f'{skippedTracks} tracks skipped')
    else:
        print(f'## Invalid existing playlist behaviour selected. Exiting...')
        exit()

if __name__ == "__main__":
    main()



            