from functions import *

### System Variables
scriptName = 'Playlist Export'

def main():
    print(f'### Initialising {colored(scriptName, "white", attrs=["bold"])}...')

    ### Open playlist file
    if outputDirectory != '':
        outputDirFix = os.path.normpath(os.path.join(outputDirectory, f'{playlistToExport}.m3u'))
    else:
        outputDirFix = os.path.normpath(os.path.join(playlistToExport, '.m3u'))

    ### Check if playlist file exists and create
    if os.path.exists(f'{outputDirFix}'):
        match exportPlaylistBehaviour:
            case 'replace':
                playlistFile = open(f'{outputDirFix}', 'w')
                if includeM3UMetadata == 'True':
                    playlistFile.write(f'#EXTM3U\n')
                    playlistFile.write(f'#PLAYLIST: {playlistToExport}\n')
            case 'append':
                playlistFile = open(f'{outputDirFix}', 'a')
            case _:
                print(f'## Error: Unable to determine export behaviour. Exiting...')
                exit()
    else:
        print("Does not exist.")



    ### Get Playlists from source PMS
    existingPlaylists = sourcePlexServer.playlists()
    
    ### Set custom library path if needed
    if customLibraryPath != '':
        currentLibraryPath = sourceSectionName.locations[0]
        
    ### Locate wanted playlist
    progressTitle = f'### Creating M3U playlist for {colored(playlistToExport, m3uPlaylistColour, attrs=["bold"])} on {colored(targetServerName, targetServerColour, attrs=["bold"])}'    
    for playlist in existingPlaylists:
        if playlist.title == playlistToExport:
            playlistLength = len(playlist)

            with alive_bar(playlistLength, enrich_print=False, title=progressTitle, title_length=(titleLength+26), dual_line=True) as bar:
                for track in playlist:
                    if includeM3UMetadata == 'True':
                        playlistFile.write(f'#EXTINF:{math.ceil(track.duration/1000)},{track.grandparentTitle} – {track.title}\n')
                    
                    ### Replace current library path with custom library path or remove for portable
                
                    pathFix = track.locations[0].replace(currentLibraryPath, '').replace('/', '', 1)
                    
                    # ## TODO: if portable. change path to local. so remove?
                    if createPortablePlaylist == 'True':
                        pathFix = track.locations[0].replace(currentLibraryPath, '').replace('/', '', 1)
                        pathFix = os.path.normpath(pathFix)

                        ## Set approriate slashes for file paths
                        if customLibraryPath[0].isalpha():
                            pathFix = pathFix.replace('/', '\\')
                        elif customLibraryPath.startswith('/'):
                            pathFix = pathFix.replace('\\', '/')
                        else:
                            print("Error, unknown OS path")

                        playlistFile.write(f'{os.path.normpath(pathFix)}\n')

                    elif customLibraryPath != '':
                        pathFix = track.locations[0].replace(currentLibraryPath, '').replace('/', '', 1)
                        pathFix = os.path.join(customLibraryPath, pathFix)
                        pathFix = os.path.normpath(pathFix)

                        ## Set approriate slashes for file paths
                        if customLibraryPath[0].isalpha():
                            pathFix = pathFix.replace('/', '\\')
                        elif customLibraryPath.startswith('/'):
                            pathFix = pathFix.replace('\\', '/')
                        else:
                            print("Error, unknown OS path")

                        playlistFile.write(f'{os.path.normpath(pathFix)}\n')
                    else:
                        playlistFile.write(f'{track.locations[0]}\n')

                    ### Create output dir if it doesn't exist
                    os.makedirs(outputDirectory, exist_ok=True)

                    ### Copy track file to output dir
                    if createPortablePlaylist == 'True':
                        shutil.copy2(pathFix, outputDirectory)

                    bar.text = f'## Adding {colored(track.grandparentTitle, artistColour, attrs=["bold"])} - {colored(track.title, trackColour, attrs=["bold"])} from {colored(sourceServerName, sourceServerColour, attrs=["bold"])}'
                    bar()
                bar.title = f'### {colored(playlistLength, "green", attrs=["bold"])} tracks added to {colored(playlistToExport, "cyan", attrs=["bold"])}.m3u'
    
    playlistFile.close()

if __name__ == "__main__":
    main()
