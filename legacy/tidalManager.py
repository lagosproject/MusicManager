import tidalapi
import json
import time
from pprint import pprint

# TIDAL: https://tidalapi.netlify.app/

class TidalManager:
    def __init__(self,spoManager):
        self.isActive = False
        self.tidalclient = ""
        self.spoManager = spoManager
        self.sp = spoManager.sp
        self.tidal = tidalapi.Session()

    def loadData(self):
        f = open('datos_tidal.json')
        data = json.load(f)
        f.close()
        return data

    def TidalGUI(self):
        if self.isActive == False:
            tidal_data = self.loadData()
            self.tidalclient = self.tidal.load_oauth_session(token_type=tidal_data["TOKEN_TYPE"],access_token=tidal_data["access_token"],expiry_time=tidal_data["expiry_time"])
            self.isActive = True
        exit = False
        while not exit:
            print()
            print('------------------------------------------------------')
            print('Bienvenido a Deezer, ¿que desea hacer?')
            print('1. Copiar playlist de Spotify a Tidal')
            print('2. Copiar guardados de Spotify a Tidal')
            print('0. Salir')
            print()
            opcion = input('Ingrese una opcion: ')
            if opcion == '1':
                playlist = input('Ingrese la playlist de Spotify: ')
                playlistDeezer = input('Ingrese el ID de la playlist de Deezer: ')
                self.copyToTidalPlaylist(playlist,playlistDeezer)
            elif opcion == '2':
                self.testeo()
            elif opcion == '0':
                exit = True

    def testeo(self):
        tidalSearch = self.tidal.search("Kings of the beat",models=[tidalapi.media.Track],limit=1)
        print(tidalSearch['tracks'][0].id)

    def copyToTidalPlaylist(self,playlist,playlistDeezer):
            pl_id = self.spoManager.playlistIdGenerator(playlist)
            
            
            response = self.sp.playlist(pl_id,
                                    fields='name,description',
                                    additional_types=['track'])
            print('Copiando lista ',response['name'])

            pl_tidal = self.tidal.user.create_playlist(response['name'], response['description'])
            
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
                    tidalSearch = self.tidal.search(search,models=[tidalapi.media.Track],limit=1)
                    time.sleep(0.1)
                    # print(search_results)
                    x = len(tidalSearch['tracks'])
                    if x > 0: 
                        search_results = tidalSearch['tracks'][0]
                        print('Añadiendo ',search_results.name,' : ',search)
                        elemsTandas.append(search_results.id)
                    else:
                        notFound.append(search)
                        print('No se encontró ',search)

                    if len(elemsTandas) >= 1:
                        try:
                            print('Enviando tanda')
                            pl_tidal.add(elemsTandas)#añadir id del elem,ento osea elemtandas
                            time.sleep(0.1)
                            anadidas += len(elemsTandas)
                        except:
                            tryLater.append(elemsTandas)
                        elemsTandas.clear()
                if len(elemsTandas) > 0:
                    try:
                        pl_tidal.add(elemsTandas)#añadir id del elem,ento
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
                    pl_tidal.add([elem])#añadir id del elem,ento elem
                    time.sleep(0.1)
                except:
                    print('Error al añadir ',elem)
                    break

            print('No se encontraron las siguientes canciones:')
            pprint(notFound)

            print('Se anadieron ',anadidas,' canciones de ',offset,' en total')  