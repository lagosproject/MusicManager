import spotipy
from spotipy.oauth2 import SpotifyOAuth
import random
from pprint import pprint
from datetime import datetime as dt
from utilities import Utilities as utils

# Referencias librerias
# Spotipy: https://spotipy.readthedocs.io/en/2.19.0/?highlight=fields

from music_manager.config import settings

class SpoManager:
    def __init__(self):
        self.sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=settings.spotipy_client_id,
                client_secret=settings.spotipy_client_secret,
                redirect_uri=settings.spotipy_redirect_uri,
                scope="user-library-read,user-follow-read,playlist-modify-public,playlist-modify-private",
                cache_path=settings.cache_path
            )
        )
        #self.user = self.sp.current_user()

    def SpotyGUI(self):
        exit = False
        while not exit:
            print()
            print('------------------------------------------------------')
            print('Bienvenido a Spotify, ¿que desea hacer?')
            print('1. Crear macro playlists')
            print('2. Obtener posibles faltantes de una playlist')
            print('3. Obtener posibles duplicadas guardadas')
            print('4. Obtener posibles duplicadas de una playlist')
            print('5. Borrar cacnicones de una playlis que estan en otra')
            print('6. Obener top de artistas de una playlist')
            print('7. Obtener novedades')
            print('8. Obtener recomendaciones de una playlist')
            print('9. Obtener recomendaciones basados en artistas')
            print('10. Obtener canciones no disponibles en España de una playlist')
            print('11. Crear playlist family friendly')
            print('12. Crear Macro y family friendly')
            print('13. Crear extended mixes')
            print('14. Crear playlist de artista dado otra playlist')
            print('0. Salir')
            print()
            opcion = input('Ingrese una opcion: ')
            if opcion == '1':
                playlist = input('Ingrese la playlist: ')
                self.createMacroPlaylist(playlist)
            elif opcion == '2':
                playlist = input('Ingrese la playlist: ')
                self.potentiallyMissingSongs(playlist)
            elif opcion == '3':
                self.getDuplicatedSaved()
            elif opcion == '4':
                playlist = input('Ingrese la playlist: ')
                self.getDuplicatedPlaylist(playlist)
            elif opcion == '5':
                playlist = input('Ingrese la playlist filtro: ')
                playlist2 = input('Ingrese la playlist a filtrar: ')
                self.deleteFromPlaylist(playlist,playlist2)
            elif opcion == '6':
                playlist = input('Ingrese la playlist: ')
                self.getArtistTop(playlist)
            elif opcion == '7':
                self.getNovedades()
            elif opcion == '8':
                playlist = input('Ingrese la playlist: ')
                amountSeed = input('Ingrese la cantidad de elementos para semilla: ')
                amountLimit = input('Ingrese la cantidad de elementos para recomendacion: ')
                self.getRecomendatiosFromPlaylist(playlist,amountSeed,amountLimit)
            elif opcion == '9':
                amountSeed = input('Ingrese la cantidad de elementos para semilla: ')
                amountLimit = input('Ingrese la cantidad de elementos para recomendacion: ')
                self.getRecomendatiosFromArtist(amountSeed,amountLimit)
            elif opcion == '10':
                playlist = input('Ingrese la playlist: ')
                self.getNoDisponiblesSpain(playlist)
            elif opcion == '11':
                playlist = input('Ingrese la playlist: ')
                self.createFamilyFriendlyPlaylist(playlist)
            elif opcion == '12':
                print('Creando Macro Playlist')
                self.createMacroPlaylist('https://open.spotify.com/playlist/2GHIEBMJKaUqkoDVOIxFao?si=efcbe08e376244c3')
                print('Creando Family Friendly Playlist')
                self.createFamilyFriendlyPlaylist('https://open.spotify.com/playlist/5i8jCq2ISdWXwgXBVb5Nys?si=fed615f2388e45d2')
            elif opcion == '13':
                playlistBase = input('Ingrese la playlist de base: ')
                self.getExtendedMixes(playlistBase)
            elif opcion == '14':
                playlistBase = input('Ingrese la playlist de base: ')
                artistas = []
                artista = input('Ingrese el artista a buscar (deje en blanco para terminar): ')               
                while artista:
                    artistas.append(artista)
                    artista = input('Ingrese el artista a buscar (deje en blanco para terminar): ')
                
                self.getSongsFromArtistInPlaylist(playlistBase,artistas)
            elif opcion == '0':
                exit = True

    def playlistIdGenerator(self,playlist):
        playlistId = playlist
        if 'spotify:playlist:' in playlist:
            return playlist
        if 'https://open.spotify.com/playlist' in playlist:
            playlistId = playlist.split('/')[4].split('?')[0]
        return 'spotify:playlist:'+playlistId

    def checkPlaylist(self,playlist,result):
        pl_id = self.playlistIdGenerator(playlist)
        offset = 0
        while True:           
            response = self.sp.playlist_items(pl_id,
                                        offset=offset,
                                        fields='items.track.id,total',
                                        additional_types=['track'])
            
            if len(response['items']) == 0:
                print('Terminado para <',playlist,'> con ',offset, ' items')
                break
            
            y = 0
            for elem in response['items']:
                result[elem['track']['id']] = offset+y
                y+=1
            offset = offset + len(response['items'])     

    def getSavedTracks(self,result,filter=None):
        offset = 0
        while True:
            response = self.sp.current_user_saved_tracks(limit=20,
                                        offset=offset)
            
            if len(response['items']) == 0:
                print('Terminado para saved con ',offset, ' items')
                break
            
            for elem in response['items']:
                if filter is None:
                    result.append('spotify:track:'+elem['track']['id'])
                else:
                    if elem['track']['id'] not in filter:
                        result.append('spotify:track:'+elem['track']['id'])
                    filter[elem['track']['id']] = True

            offset = offset + len(response['items'])  
        
    def getSavedAlbums(self,result,filter=None):
        offset = 0
        while True:
            response = self.sp.current_user_saved_albums(limit=20,
                                        offset=offset)
            
            if len(response['items']) == 0:
                print('Terminado para saved albums con ',offset,' items')
                break
            
            for elem in response['items']:
                for track in elem['album']['tracks']['items']:
                    if filter is None:
                        result.append('spotify:track:'+track['id'])
                    else:
                        if track['id'] not in filter:
                            result.append('spotify:track:'+track['id'])
                        filter[track['id']] = True
                
            offset = offset + len(response['items'])

    def getSavedArtists(self,result: list):
        after=None
        artistas = {}
        while True:
            response = self.sp.current_user_followed_artists(limit = 20,after=after)
            after=response['artists']['cursors']['after']

            if len(response['artists']['items']) == 0:
                print('Terminado de obtener artistas')
                break

            for elem in response['artists']['items']:
                if elem['id'] not in artistas:
                    artistas[elem['id']] = elem['name']
                    result.append(elem['uri'])
                else:
                    return

    def addPlaylistSongs(self, playlist, result, filter=None):
        pl_id = self.playlistIdGenerator(playlist)
        offset = 0

        while True:
            response = self.sp.playlist_items(pl_id,
                                        offset=offset,
                                        fields='items.track.id,total',
                                        additional_types=['track'])
            
            if len(response['items']) == 0:
                print('Terminado para ',playlist,' con ',offset, ' items')
                break
            
            for elem in response['items']:
                if filter is None:
                    result.append('spotify:track:'+elem['track']['id'])
                else:
                    if elem['track']['id'] not in filter:
                        result.append('spotify:track:'+elem['track']['id'])
                    filter[elem['track']['id']] = True

            offset = offset + len(response['items'])

    def addPlaylistsSongs(self, result, filter=None, *playlist):
        for p in playlist:
            self.addPlaylistSongs(p,result,filter)

    def cleanList(self,playlist,items):
        elemsDeleted = []
        for k,v in items.items():
            if v != True:
                elem = {}
                elem['uri'] = 'spotify:track:'+k
                elem['positions'] = [v]
                elemsDeleted.append(elem)
        # pprint(elemsDeleted)
        offset = 0
        while True:
            try:
                self.sp.playlist_remove_specific_occurrences_of_items(playlist, elemsDeleted[offset:offset+100])
            except:
                print('Error al borrar elementos de la playlist')
            offset += 100
            if offset > len(elemsDeleted):
                break

    def cleanAllOcurrences(self,playlist,items):
        elemsDeleted = []
        for k,v in items.items():
            if v != True:
                elemsDeleted.append('spotify:track:'+k)
        
        offset = 0
        while True:
            try:
                self.sp.playlist_remove_all_occurrences_of_items(playlist, elemsDeleted[offset:offset+100])
            except:
                print('Error al borrar elementos de la playlist')
            offset += 100
            if offset > len(elemsDeleted):
                break

    def createMacroPlaylist(self,playlist):
        cancionesPlaylist = {}
        cacncionesPorAnadir = []
        self.checkPlaylist(playlist,cancionesPlaylist)
        self.addPlaylistsSongs(cacncionesPorAnadir,cancionesPlaylist,'3xf4p0pKyfZ0cOpRevLGC0','05OTaAnmlHWcj6Qjc5aaIo','3HD2idzM5B9mlHI64o7XMn')
        self.getSavedTracks(cacncionesPorAnadir,cancionesPlaylist)
        self.getSavedAlbums(cacncionesPorAnadir,cancionesPlaylist)

        # pprint(cacncionesPorAnadir)
        self.addSongsToPlaylist(playlist,cacncionesPorAnadir)
        
        self.cleanList(playlist,cancionesPlaylist) 

    def createFamilyFriendlyPlaylist(self,playlist):
        cancionesPlaylist = {}
        songsToEliminate = []
        songsMacro = []
        self.checkPlaylist(playlist,cancionesPlaylist)
        
        self.addPlaylistSongs('https://open.spotify.com/playlist/2GHIEBMJKaUqkoDVOIxFao?si=08d5ca48d6724e30',songsMacro)
        self.addPlaylistSongs('https://open.spotify.com/playlist/3xf4p0pKyfZ0cOpRevLGC0?si=443de4d12edf4ff0',songsToEliminate)

        primerFiltro = []
        self.filterResultsList(songsMacro,songsToEliminate,primerFiltro)

        segundoFiltro = []
        self.filterResultsList(primerFiltro,cancionesPlaylist,segundoFiltro)
        self.cleanAllOcurrences(playlist,cancionesPlaylist)
        self.addSongsToPlaylist(playlist,segundoFiltro)

    def addSongsToPlaylist(self, playlist, songs):
        playlistId = self.playlistIdGenerator(playlist)
        self.cleanSongList(songs)
        offset = 0
        if(len(songs)>0):
            while True:
                self.sp.playlist_add_items(playlistId,songs[offset:offset+100])
                offset += 100
                if offset >= len(songs):
                    break

    def cleanSongList(self,playlist):
        for cancion in playlist:
            if not 'spotify:track:' in cancion:
                playlist.remove(cancion)
                print('Problema con la cancion: ',cancion,' ha sido eliminada')

    def getDuplicatedPlaylist(self,playlist):
        pl_id = self.playlistIdGenerator(playlist)
        offset = 0
        duplicated = {}
        samename = {}
        potenciales = 0
        probables = 0
        pocoProbables = 0
        while True:
            response = self.sp.playlist_items(pl_id,
                                        offset=offset,
                                        fields='items.track.id,items.track.name,items.track.artists.name,total',
                                        additional_types=['track'])
            
            if len(response['items']) == 0:
                print('Terminado para ',playlist)
                break
            
            for elem in response['items']:
                # print(elem)
                if elem['track']['id'] in duplicated:
                    print('------------------------------------------------------')
                    print('Potencial copia en ',elem['track']['name'])
                    pprint(elem['track']['artists'])
                    potenciales += 1
                elif elem['track']['name'] in samename:
                    coincidencia = False
                    probTem = 0
                    for artist in elem['track']['artists']:
                        #print(artist['name'])
                        for otherartits in samename[elem['track']['name']]:
                            if artist['name'] in otherartits['name']:
                                coincidencia = True
                                probTem += 1
                    if coincidencia:
                        print('------------------------------------------------------')
                        print('Probable copia en ',elem['track']['name'])
                        if probTem == len(elem['track']['artists']) and probTem == len(samename[elem['track']['name']]):
                            print('Todos los artistas coinciden')
                            probables += 1
                        else:
                            print('Algunos artistas coinciden')
                            pocoProbables += 1
                        print('Artistas primero')
                        pprint(elem['track']['artists'])
                        print('Artistas segundo')
                        pprint(samename[elem['track']['name']])

                else:
                    duplicated[elem['track']['id']] = True
                    samename[elem['track']['name']] = elem['track']['artists']
            # pprint(response['items'])
            offset = offset + len(response['items'])
        print('Potenciales: ',potenciales)
        print('Probables: ',probables)
        print('Poco Probables: ',pocoProbables)

    def getDuplicatedSaved(self):
        offset = 0
        duplicated = {}
        samename = {}
        potenciales = 0
        probables = 0
        pocoProbables = 0
        while True:
            response = self.sp.current_user_saved_tracks(limit=20,
                                offset=offset)
            
            if len(response['items']) == 0:
                print('Terminado para saved')
                break
            
            for elem in response['items']:
                # print(elem)
                if elem['track']['id'] in duplicated:
                    print('------------------------------------------------------')
                    print('Potencial copia en ',elem['track']['name'])
                    pprint(elem['track']['artists'])
                    potenciales += 1
                elif elem['track']['name'] in samename:
                    coincidencia = False
                    probTem = 0
                    for artist in elem['track']['artists']:
                        #print(artist['name'])
                        for otherartits in samename[elem['track']['name']]:
                            if artist['name'] in otherartits['name']:
                                coincidencia = True
                                probTem += 1
                    if coincidencia:
                        print('------------------------------------------------------')
                        print('Probable copia en ',elem['track']['name'])
                        if probTem == len(elem['track']['artists']) and probTem == len(samename[elem['track']['name']]):
                            print('Todos los artistas coinciden')
                            probables += 1
                        else:
                            print('Algunos artistas coinciden')
                            pocoProbables += 1
                        print('Artistas primero')
                        salida = []
                        for artist in elem['track']['artists']:
                            salida.append(artist['name'])
                        pprint(salida)
                        print('Artistas segundo')
                        salida = []
                        for artist in samename[elem['track']['name']]:
                            salida.append(artist['name'])
                        pprint(salida)

                else:
                    duplicated[elem['track']['id']] = True
                    samename[elem['track']['name']] = elem['track']['artists']
            # pprint(response['items'])
            offset = offset + len(response['items'])
        print('Potenciales: ',potenciales)
        print('Probables: ',probables)
        print('Poco Probables: ',pocoProbables)

    def potentiallyMissingSongs(self, playlist):
        pl_id = self.playlistIdGenerator(playlist)
        offset = 0

        artistas = {}
        canciones = {}

        while True:
            response = self.sp.playlist_items(pl_id,
                                        offset=offset,
                                        fields='items.track.id,items.track.name,items.track.artists.name,total',
                                        additional_types=['track'])
            
            if len(response['items']) == 0:
                print('Terminado para ',playlist)
                break
            
            for elem in response['items']:
                # print(elem)
                canciones[elem['track']['id']] = True
                for artist in elem['track']['artists']:
                    artistas[artist['name']] = True

            offset = offset + len(response['items'])

        offset = 0
        while True:
            response = self.sp.current_user_saved_tracks(limit=20,
                                        offset=offset)
            
            if len(response['items']) == 0:
                print('Terminado para saved')
                break
            
            for elem in response['items']:
                if elem['track']['id'] not in canciones:
                    for artist in elem['track']['artists']:
                        if artist['name'] in artistas:
                            print('------------------------------------------------------')
                            print('Coincidencia dada por: ',artist['name'])
                            print('Potencial falta: ',elem['track']['name'])
                            for artistaPrint in elem['track']['artists']:
                                print(artistaPrint['name'])
                            break
                #print(elem)
                
            # pprint(response['items'])
            offset = offset + len(response['items'])

    def deleteFromPlaylist(self, playlistFrom,playlistRemove):
        cancionesPlaylistRemove = {}
        cancionesPlaylistFrom = {}
        cancionesABorrar = {}
        self.checkPlaylist(playlistFrom,cancionesPlaylistFrom)
        self.checkPlaylist(playlistRemove,cancionesPlaylistRemove)
        for k,v in cancionesPlaylistFrom.items():
            if k in cancionesPlaylistRemove:
                cancionesABorrar[k] = cancionesPlaylistRemove[k]
                
        self.cleanList(playlistRemove,cancionesABorrar)
        print('Deleted duplicated elements')

    def getArtistTop(self, playlist):
        artistas = {}
        pl_id = self.playlistIdGenerator(playlist)
        offset = 0
        while True:           
            response = self.sp.playlist_items(pl_id,
                                        offset=offset,
                                        fields='items.track.id,total,items.track.artists.name',
                                        additional_types=['track'])
            
            if len(response['items']) == 0:
                print('Terminado para <',playlist,'> con ',offset, ' items')
                break
            
            y = 0
            for elem in response['items']:
                for artist in elem['track']['artists']:
                    if artist['name'] in artistas:
                        artistas[artist['name']] += 1
                    else:
                        artistas[artist['name']] = 1
                y+=1
            offset = offset + len(response['items']) 
        
        response = sorted(artistas.items(), key=lambda x: x[1], reverse=True)[:100]
        formatedResponse = ""
        lastElem = 0
        for elem in response:
            if lastElem == elem[1]:
                formatedResponse += " , " + elem[0] 
            else:
                formatedResponse += "\n" + str(elem[1])+' : '+str(elem[0])
            lastElem = elem[1]
        utils.normalSave(formatedResponse,'artistas')
        pass

    def filterResuls(self, songs: dict, filter:dict ,result: list):
        for k,v in songs.items():
            if not k[14:] in filter:
                result.append(k)

    def filterResultsList(self, songs, filter,result: list):
        for song in songs:
            if not song in filter:
                result.append(song)

    def getNovedades(self):
        # self.user['id']
        abc = dt.today()
        formated = abc.strftime('%Y-%m-%d')
        newPlaylist = self.sp.user_playlist_create('grmapal2', 'Novedades '+formated,public=False,description='Novedades de Spotify')
        newPlaylist = newPlaylist['uri']
        print('Creamos playlist: ',newPlaylist)
        after=None
        artistas = {}
        canciones = {}
        
        month, year = (abc.month-5, abc.year) if abc.month > 5 else (12-(5-abc.month), abc.year-1)
        pre_month = abc.replace(day=1, month=month, year=year)
        while True:
            response = self.sp.current_user_followed_artists(limit = 20,after=after)
            after=response['artists']['cursors']['after']

            if len(response['artists']['items']) == 0:
                print('Terminado de obtener artistas')
                break

            for elem in response['artists']['items']:
                if elem['id'] not in artistas:
                    artistas[elem['id']] = elem['name']
                else:
                    print('Terminado de obtener artistas')
                    print('Se han encontrado ',len(canciones), ' nuevas canciones')
                    salidaMacro = {}
                    self.checkPlaylist('https://open.spotify.com/playlist/2GHIEBMJKaUqkoDVOIxFao?si=8630b8930d5549be',salidaMacro)         
                    filtrado = []
                    self.filterResuls(canciones,salidaMacro,filtrado)
                    self.addSongsToPlaylist(newPlaylist,filtrado)
                    print('Playlist de novedades completa')
                    return

                responseSingle = self.sp.artist_albums(elem['id'],album_type='single',limit=1)
                responseAlbum = self.sp.artist_albums(elem['id'],album_type='album',limit=1)
                dateSingle =  dt.strptime(responseSingle['items'][0]['release_date'], "%Y-%m-%d")
                dataAlbum = dt.strptime("1700-10-02", "%Y-%m-%d")
                if len(responseAlbum['items']) > 0:
                    dataAlbum = dt.strptime(responseAlbum['items'][0]['release_date'], "%Y-%m-%d")
                albumToExtract = ""
                if dateSingle > dataAlbum:
                    albumToExtract = responseSingle
                    if pre_month > dateSingle:
                        continue
                else:
                    albumToExtract = responseAlbum
                    if pre_month > dataAlbum:
                        continue
                response = self.sp.album_tracks(albumToExtract['items'][0]['uri'])
                for track in response['items']:
                    canciones[track['uri']] = True

    def getRecomendatiosFromPlaylist(self, playlist, amountSeed, amountExit):
        songs = []
        self.addPlaylistSongs(playlist,songs)
        amountSeedReal = int(amountSeed)
        if amountSeedReal > 5:
            amountSeedReal = 5
        elems = random.sample(songs,int(amountSeedReal))
        response = self.sp.recommendations(seed_tracks=elems,limit=int(amountExit))
        
        result = []
        for elem in response['tracks']:
            result.append(elem['uri'])

        newPlaylist = self.sp.user_playlist_create('grmapal2', 'Recomendaciones',public=False,description='Recomendaciones dadas')
        newPlaylist = newPlaylist['uri']

        filtrado = []
        self.filterResultsList(result,songs,filtrado)
        # pprint(filtrado)
        self.addSongsToPlaylist(newPlaylist,filtrado)

    def getRecomendatiosFromArtist(self, amountSeed, amountExit):
        artistas = []
        self.getSavedArtists(artistas)
        amountSeedReal = int(amountSeed)
        if amountSeedReal > 5:
            amountSeedReal = 5
        elems = random.sample(artistas,int(amountSeedReal))
        response = self.sp.recommendations(seed_artists=elems,limit=int(amountExit))

        result = []
        for elem in response['tracks']:
            result.append(elem['uri'])
        
        newPlaylist = self.sp.user_playlist_create('grmapal2', 'Recomendaciones artistas',public=False,description='Recomendaciones dadas')
        newPlaylist = newPlaylist['uri']

        self.addSongsToPlaylist(newPlaylist,result)

    def getNoDisponiblesSpain(self,playlist):
        pl_id = self.playlistIdGenerator(playlist)
        offset = 0

        while True:
            response = self.sp.playlist_items(pl_id,
                                        offset=offset,
                                        fields='items.track.uri,items.track.name,items.track.artists.name,items.track.available_markets,total',
                                        additional_types=['track'])

            if len(response['items']) == 0:
                print('Terminado para ',playlist,' con ',offset, ' items')
                break

            for elem in response['items']: 
                if len(elem['track']['available_markets']) > 0:     
                    if not 'ES' in elem['track']['available_markets']:
                        print(elem['track']['available_markets'])
                        print(elem['track']['name'], ' no disponible en España')
                        print(elem['track']['artists'][0]['name'])
                        print(elem['track']['uri'])
                        print('\n')

            offset = offset + len(response['items'])

    def getExtendedMixes(self,playlist):
        songs = []
        abc = dt.today()
        formated = abc.strftime('%Y-%m-%d')
        newPlaylist = self.sp.user_playlist_create('grmapal2', 'Extended Mixes '+formated,public=False,description='Extenciones mixes de canciones')
        newPlaylist = newPlaylist['uri']
        print('Creamos playlist: ',newPlaylist)

        pl_id = self.playlistIdGenerator(playlist)
        offset = 0
        while True:
            response = self.sp.playlist_items(pl_id,
                                        offset=offset,
                                        fields='items.track.uri,items.track.name,items.track.artists.name,items.track.available_markets,total',
                                        additional_types=['track'])

            if len(response['items']) == 0:
                print('Terminado para ',playlist,' con ',offset, ' items')
                self.addSongsToPlaylist(newPlaylist,songs)
                break

            for elem in response['items']: 
                if 'extended mix' in elem['track']['name'] or 'original mix' in elem['track']['name']:
                    songs.append(elem['track']['uri'])
                else:
                    busqueda = elem['track']['name']+" extended mix "+elem['track']['artists'][0]['name']
                    print(busqueda)
                    searched = self.sp.search(busqueda,limit=1)
                    if len(searched['tracks']['items']) == 0:
                        print('- Vacio siguiente')
                        continue
                    if  not 'Extended Mix' in searched['tracks']['items'][0]['name'] and not 'extended mix' in searched['tracks']['items'][0]['name']:
                        print('- Resultado sin coincidencia',searched['tracks']['items'][0]['name'])
                        continue
                    print('======= Verificar')
                    coincidencia = False
                    probTem = 0
                    for artist in elem['track']['artists']:
                        #print(artist['name'])
                        for otherartits in searched['tracks']['items'][0]['artists']:
                            print('Comparando',otherartits['name'],'y',otherartits['name'])
                            if artist['name'] in otherartits['name']:
                                coincidencia = True
                                probTem += 1
                    if coincidencia:
                        print('------------------------------------------------------')
                        print('Probable copia en ',elem['track']['name'])
                        if probTem == len(elem['track']['artists']) and probTem == len(searched['tracks']['items'][0]['artists']):
                            print('Todos los artistas coinciden')
                            print('Añadimos ',searched['tracks']['items'][0]['name'])
                            songs.append(searched['tracks']['items'][0]['uri'])

            offset = offset + len(response['items'])

    def getSongsFromArtistInPlaylist(self,playlist,artistnames):
        """songs = []
        newPlaylist = self.sp.user_playlist_create('grmapal2', 'This is your '+artistname,public=False,description='Canciones pertenecientes al atista '+ artistname)
        newPlaylist = newPlaylist['uri']
        print('Creamos playlist: ',newPlaylist)"""

        artist_playlists = {}
        songs_to_add = {}

        # Creamos una playlist para cada artista
        for artistname in artistnames:
            newPlaylist = self.sp.user_playlist_create('grmapal2', 'This is your '+artistname, public=False, description='Canciones pertenecientes al atista '+ artistname)
            newPlaylistUri = newPlaylist['uri']
            artist_playlists[artistname] = newPlaylistUri
            songs_to_add[artistname] = []
            print('Creamos playlist para', artistname, ':', newPlaylistUri)

        pl_id = self.playlistIdGenerator(playlist)
        offset = 0
        while True:
            response = self.sp.playlist_items(pl_id,
                                        offset=offset,
                                        fields='items.track.uri,items.track.name,items.track.artists.name,total',
                                        additional_types=['track'])

            if len(response['items']) == 0:
                print('Terminado para ',playlist,' con ',offset, ' items')
                for artistname, songs in songs_to_add.items():
                    if len(songs) > 0:
                        self.addSongsToPlaylist(artist_playlists[artistname], songs)
                break

            for elem in response['items']: 
                for artista_k in elem['track']['artists']:
                    if artista_k['name'] in artistnames:
                        songs_to_add[artista_k['name']].append(elem['track']['uri'])

            offset = offset + len(response['items'])