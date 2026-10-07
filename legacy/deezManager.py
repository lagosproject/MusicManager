import deezer
from decouple import config
import time
from pprint import pprint
import subprocess

# Referencias librerias
# Deezer: https://deezer-python.readthedocs.io/en/stable/installation.html

class DeezManager:
    def __init__(self,spoManager):
        self.isActive = False
        self.dzclient = ""
        self.spoManager = spoManager
        self.sp = spoManager.sp

    def DeezGUI(self):
        if self.isActive == False:
            subprocess.call([r'getToken.bat'])
            self.dzclient = deezer.Client(access_token=config('API_TOKEN'))
            self.isActive = True
        exit = False
        while not exit:
            print()
            print('------------------------------------------------------')
            print('Bienvenido a Deezer, ¿que desea hacer?')
            print('1. Copiar playlist de Spotify a Deezer')
            print('2. Copiar guardados de Spotify a Deezer')
            print('0. Salir')
            print()
            opcion = input('Ingrese una opcion: ')
            if opcion == '1':
                playlist = input('Ingrese la playlist de Spotify: ')
                playlistDeezer = input('Ingrese el ID de la playlist de Deezer: ')
                self.copyToDeezerPlaylist(playlist,playlistDeezer)
            elif opcion == '2':
                self.copyToDeezerSaved()
            elif opcion == '0':
                exit = True

    def copyToDeezerPlaylist(self,playlist,playlistDeezer):
        pl_id = self.spoManager.playlistIdGenerator(playlist)
        pl_id_deez = 'playlist/'+playlistDeezer+'/tracks'
        
        response = self.sp.playlist(pl_id,
                                fields='name,description',
                                additional_types=['track'])
        print('Copiando lista ',response['name'])
        
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
                dezzerSearch = self.dzclient.search(search)
                time.sleep(0.1)
                # print(search_results)
                x = dezzerSearch.total
                if x > 0: 
                    search_results = dezzerSearch[0]
                    print('Añadiendo ',search_results,' : ',search)
                    elemsTandas.append(search_results.id)
                else:
                    notFound.append(search)
                    print('No se encontró ',search)

                if len(elemsTandas) >= 1:
                    try:
                        print('Enviando tanda')
                        self.dzclient.request('POST',pl_id_deez,songs=elemsTandas,order=0)
                        time.sleep(0.1)
                        anadidas += len(elemsTandas)
                    except:
                        tryLater.append(elemsTandas)
                    elemsTandas.clear()
            if len(elemsTandas) > 0:
                try:
                    self.dzclient.request('POST',pl_id_deez,songs=elemsTandas,order=0)
                except:
                    print('Canciones de la tanda ya estaban en la lista')
                    tryLater.append(elemsTandas)
                elemsTandas.clear()
            # pprint(response['items'])
            offset = offset + len(response['items'])
            print('Procesando ',offset,'/',response['total'])

        print()
        print('Añadiendo ',len(tryLater),' canciones que no se encontraron')
        for elem in tryLater:
            try:
                print(elem)
                self.dzclient.request('POST',pl_id_deez,songs=elem,order=0)
                time.sleep(0.1)
            except:
                print('Error al añadir ',elem)
                break

        print('No se encontraron las siguientes canciones:')
        pprint(notFound)

        print('Se anadieron ',anadidas,' canciones de ',offset,' en total')  

    def copyToDeezerSaved(self):
        #Checkear datosde la playlist
        notFound = []
        offset = 0
        while True:
            response = self.sp.current_user_saved_tracks(limit=20,
                                        offset=offset)
            
            if len(response['items']) == 0:
                print('Terminado para copysaved')
                break
            
            for elem in response['items']:
                # Meter datos de la playlist
                search = ""
                search += elem['track']['name']
                for artist in elem['track']['artists']:
                    search += " "+artist['name']
                dezzerSearch = self.dzclient.search(search)

                time.sleep(0.1)
                
                x = dezzerSearch.total
                if x > 0: 
                    search_results = dezzerSearch[0]
                    print('Añadiendo ',search_results,' : ',search)
                    try:
                        self.dzclient.add_user_track(search_results.id)
                    except:
                        print('Ya existia o da error')
                else:
                    print('No se encontró ',search)
                    notFound.append(search)
            # pprint(response['items'])
            offset = offset + len(response['items'])
            print('Procesando ',offset,'/',response['total'])

        print('Canciones que no se encontraron')
        pprint(notFound)