import asyncio
import streamlit as st
import websockets
from bleak import BleakClient, BleakScanner
from functools import partial

# UUID du capteur cardiaque Polar H10
HEART_RATE_UUID = "00002a37-0000-1000-8000-00805f9b34fb"
BATTERY_LEVEL_UUID = "00002a19-0000-1000-8000-00805f9b34fb"

# Liste des clients WebSocket connectés
clients = set()

# Interface Streamlit
st.title("💓 Serveur WebSocket - Polar H10")
st.write("Cette application permet d'envoyer la fréquence cardiaque à Unity via WebSocket.")

# Initialisation des variables dans session_state
if "polar_connected" not in st.session_state:
    st.session_state.polar_connected = False


# Création des boutons
col1, col2, col3 = st.columns(3)  # Création de 3 colonnes

with col1:
    connect_polar_button = st.button("🔗 Connecter le Polar H10")
    status_connect = st.empty()  # Conteneur pour afficher les messages de l'état de connexion
    heart_rate_display = st.empty() # affiche la FC
    battery_level_display = st.empty()
    status_send = st.empty() # affiche l'envoie de la FC

with col2:
    start_server_button = st.button("🚀 Démarrer le serveur WS")
    status_ws = st.empty()

with col3:
    stop_server_button = st.button("❌ Arrêter le serveur")


# Fonction pour scanner et connecter le Polar H10
async def connect_polar_h10():
    """Recherche et connecte le Polar H10 en Bluetooth."""
    status_connect.write("🔍 Scan des appareils BLE...")
    devices = await BleakScanner.discover()

    for device in devices:
        if device.name:
            status_connect.write(f"🔎 Détecté : {device.name}, {device.address}")

        if device.name and "Polar" in device.name:
            async with BleakClient(device) as client:
                status_connect.success(f"✅ Connecté à {device.name} ({device.address})")
                st.session_state.polar_connected = True # Update état de connexion

                async def callback(sender, data):
                    heart_rate = data[1]
                    heart_rate_display.write(f"❤️ FC : {heart_rate} BPM")
                    await send_data_to_clients(heart_rate)

                await client.start_notify(HEART_RATE_UUID, callback)

                # Lire le niveau de la batterie toutes les 5 secondes
                async def battery_level_callback():
                    battery_level = await client.read_gatt_char(BATTERY_LEVEL_UUID)
                    battery_percentage = battery_level[0]  # Le niveau de la batterie est un octet
                    battery_level_display.write(f"🔋 {battery_percentage}%")
                    await asyncio.sleep(5)  # Attendre 5 secondes avant de vérifier à nouveau

                asyncio.create_task(battery_level_callback())  # lecture du niv de batterie en // de la FC

                while True:
                    await asyncio.sleep(1)

    if not st.session_state.polar_connected :
        status_connect.error("❌ Aucun Polar H10 détecté.")

# Envoi des données aux clients WebSocket
async def send_data_to_clients(heart_rate):
    """Envoie la fréquence cardiaque aux clients WebSocket connectés"""
    if not clients:
        status_ws.warning("⚠️ Aucun client WebSocket connecté.")
        return

    message = str(heart_rate)
    status_send.write(f"📤 Envoi de la FC : {message}")
    await asyncio.gather(*[client.send(message) for client in clients])


# Gestion des connexions WebSocket
async def websocket_handler(websocket, path):
    """Gère la connexion WebSocket avec Unity."""
    clients.add(websocket)
    status_ws.write(f"🔗 Unity connecté (Total : {len(clients)})")

    try:
        async for message in websocket:
            st.write(f"📩 Message reçu depuis Unity : {message}")
    except websockets.ConnectionClosed:
        status_ws.warning("⚠️ Unity déconnecté")
    finally:
        clients.remove(websocket)
        status_ws.write("🔴 WebSocket déconnecté.")


# Démarrer le serveur WebSocket
async def start_server():
    """Démarre le serveur WebSocket"""
    if not st.session_state.polar_connected:
        status_ws.error("❌ Connectez d'abord le Polar H10 !")
        return

    server = await websockets.serve(partial(websocket_handler, path="/"), "0.0.0.0", 8765)
    status_ws.success("🚀 Serveur WebSocket lancé sur ws://0.0.0.0:8765")
    await server.wait_closed()


# Gestion des boutons
if connect_polar_button:
    asyncio.run(connect_polar_h10())
    #asyncio.create_task(connect_polar_h10()) # lance connection sans bloquer

if start_server_button:
    asyncio.run(start_server())  # lance le serveur WebSocket sans bloquer la connexion

if stop_server_button:
    st.warning("⛔ Serveur arrêté.")