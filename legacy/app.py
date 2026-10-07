import sys
sys.path.append(".")

from spoManager import SpoManager
from ytManager import YtManager
from deezManager import DeezManager
from tidalManager import TidalManager

# Todo: incializar en el bucle solo si lo llaman

# Inicios de sesion
# Spotify
spoManager = SpoManager()
sp = spoManager.sp
# YTMusic
ytManager = None
ytmusic = None 
# Deezer
deezManager = None
dzclient = None

tidalManager = None
tdClient = None

# Funciones apoyo
def getDeezer():
    global deezManager, dzclient
    if deezManager == None:
        deezManager = DeezManager(spoManager)
    elif dzclient == None:
        dzclient = deezManager.dzclient
    return deezManager

def getYTMusic():
    global ytManager,ytmusic
    if ytManager == None:
        ytManager = YtManager(spoManager)
    elif ytmusic == None:
        ytmusic = ytManager.ytmusic
    return ytManager

def getTidalManager():
    global tidalManager, tdClient
    if tidalManager == None:
        tidalManager = TidalManager(spoManager)
    elif tdClient == None:
        tdClient = tidalManager.tidalclient
    return tidalManager

# copyToDeezerPlaylist('05OTaAnmlHWcj6Qjc5aaIo','10398132242') # Copiando Tremendo Merengue

exit = False
while not exit:
    print('------------------------------------------------------')
    print('Selecciona el servicio que te interese:')
    print('1. Spotify')
    print('2. Deezer')
    print('3. Youtube Music')
    print('4. Tidal')
    print('0. Salir')
    # Obtenemos la entrada del usuario
    print()
    print('Introduzca opcion:')
    opcion = input()
    if opcion == "1":
        spoManager.SpotyGUI()
    elif opcion == "2":
        getDeezer().DeezGUI()
    elif opcion == "3":
        getYTMusic().YtGUI()
    elif opcion == "4":
        getTidalManager().TidalGUI()
    elif opcion == "0":
        exit = True

print('Hasta la proxima')