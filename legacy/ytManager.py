# Referencias librerias
# YTMusic: https://ytmusicapi.readthedocs.io/en/latest/usage.html

from ytmusicapi import YTMusic
import time
from pprint import pprint

class YtManager:
    def __init__(self,spoManager):
        self.ytmusic = YTMusic('headers_auth.json')
        self.spoManager = spoManager
        self.sp = spoManager.sp

    def YtGUI(self):
        exit = False
        while not exit:
            print()
            print('------------------------------------------------------')
            print('Bienvenido a YoutubeMusic, ¿que desea hacer?')
            print('1. Copiar playlist de Spotify a YoutubeMusic')
            print('2. Copiar guardados de Spotify a YoutubeMusic')
            print('0. Salir')
            print()
            opcion = input('Ingrese una opcion: ')
            if opcion == '1':
                playlist = input('Ingrese la playlist: ')
                self.copyToYTMusic(playlist)
            elif opcion == '2':
                self.copyToYTMusicSaved()
            elif opcion == '0':
                exit = True

    def copyToYTMusic(self,playlist):
        pl_id = self.spoManager.playlistIdGenerator(playlist)
        
        response = self.sp.playlist(pl_id,
                                fields='name,description',
                                additional_types=['track'])
        print('Copiando lista ',response['name'])
        playlistId = self.ytmusic.create_playlist(response['name'], response['description'])

        #Checkear datosde la playlist
        offset = 0
        anadidas = 0
        tryLater = []
        notFound = []
        while True:
            response = self.sp.playlist_items(pl_id,
                                        offset=offset,
                                        fields='items.track.name,items.track.artists.name,total',
                                        additional_types=['track'])
            
            if len(response['items']) == 0:
                print('Terminado para ',playlist)
                break
            
            elemsTandas = []
            for elem in response['items']:
                # Meter datos de la playlist
                search = ""
                search += elem['track']['name']
                search = search.replace('(', '')
                search = search.replace(')', '')
                for artist in elem['track']['artists']:
                    search += " "+artist['name']
                search_results = self.ytmusic.search(search,filter='songs',limit=1,ignore_spelling=True)
                time.sleep(0.1)
                # print(search_results)
                x = len(search_results)
                if x > 0: 
                    print('Añadiendo ',search_results[0]['videoId'],' : ',search)
                    elemsTandas.append(search_results[0]['videoId'])
                else:
                    notFound.append(search)
                    print('No se encontró ',search)

                if len(elemsTandas) >= 10:
                    try:
                        print('Enviando tanda')
                        self.ytmusic.add_playlist_items(playlistId, elemsTandas)
                        time.sleep(5)
                        anadidas += len(elemsTandas)
                    except:
                        tryLater.append(elemsTandas)
                    elemsTandas.clear()
            if len(elemsTandas) > 0:
                self.ytmusic.add_playlist_items(playlistId, elemsTandas)
                elemsTandas.clear()
            # pprint(response['items'])
            offset = offset + len(response['items'])
            print('Procesando ',offset,'/',response['total'])

        print('Añadiendo ',len(tryLater),' canciones que no se encontraron')
        for elem in tryLater:
            try:
                self.ytmusic.add_playlist_items(playlistId, elem)
            except:
                print('Error al añadir ',elem)
                exit()

        print('No se encontraron las siguientes canciones:')
        pprint(notFound)

        print('Se anadieron ',anadidas,' canciones de ',offset,' en total')


    def copyToYTMusicSaved(self):
        #Checkear datosde la playlist
        offset = 0
        tryLater = []
        while True:
            response = self.sp.current_user_saved_tracks(limit=20,
                                        offset=offset)
            
            if len(response['items']) == 0:
                print('Terminado para copysaved')
                break
            
            elemsTandas = []
            for elem in response['items']:
                # Meter datos de la playlist
                search = ""
                search += elem['track']['name']
                for artist in elem['track']['artists']:
                    search += " "+artist['name']
                search_results = self.ytmusic.search(search,filter='songs',limit=1,ignore_spelling=True)
                time.sleep(0.2)
                # saveResponse(search_results,'tets.json')
                
                x = len(search_results)
                if x > 0: 
                    try:
                        print('Añadiendo ',search_results[0]['feedbackTokens']['add'],' : ',search)
                        elemsTandas.append(search_results[0]['feedbackTokens']['add'])
                    except:
                        print('Error al añadir ',search)
                else:
                    print('No se encontró ',search)

                if len(elemsTandas) >= 10:
                    try:
                        self.ytmusic.edit_song_library_status(elemsTandas)
                    except:
                        tryLater.append(elemsTandas)
                    elemsTandas.clear()
            if len(elemsTandas) > 0:
                self.ytmusic.edit_song_library_status(elemsTandas)
                elemsTandas.clear()
            # pprint(response['items'])
            offset = offset + len(response['items'])
            print('Procesando ',offset,'/',response['total'])

        print('Añadiendo canciones que no se encontraron')
        for elem in tryLater:
            try:
                self.ytmusic.edit_song_library_status(elem)
            except:
                print('Error al añadir ',elem)
                exit()    