import asyncio
import streamlit as st
import websockets
from bleak import BleakClient, BleakScanner
from PolarH10 import PolarH10
from functools import partial

# UUID du capteur cardiaque Polar H10
HEART_RATE_UUID = "00002a37-0000-1000-8000-00805f9b34fb"
BATTERY_LEVEL_UUID = "00002a19-0000-1000-8000-00805f9b34fb"

# Liste des clients WebSocket connectés
clients = set()

# Interface Streamlit
st.title("💓 Serveur WebSocket - Polar H10")

# Création des boutons
col1, col2 = st.columns(2)  # Création de 2 colonnes

with col1 :
    start_button = st.button("🚀 Start")

with col2 :
    stop_button = st.button("❌ Stop")

status_connect = st.empty()  # Conteneur pour afficher les messages de l'état de connexion
heart_rate_display = st.empty()  # Zone pour afficher la FC
battery_level_display = st.empty()
status_ws = st.empty() # zone pour état du serveur WS
status_send = st.empty() # affiche l'envoie de la FC

# Fonction pour scanner et connecter le Polar H10
async def connect_polar_h10():
    """Recherche et connecte le Polar H10 en Bluetooth."""
    status_connect.write("🔍 Scan des appareils BLE...")
    devices = await BleakScanner.discover()

    polar_device_found = False

    for device in devices:
        if device.name:
            status_connect.write(f"🔎 Détecté : {device.name}, {device.address}")

        if device.name and "Polar" in device.name:
            polar_device_found = True
            async with BleakClient(device) as client:
                status_connect.success(f"✅ Connecté à {device.name} ({device.address})")

                async def callback(sender, data):
                    heart_rate = data[1]
                    heart_rate_display.write(f"❤️ Fréquence cardiaque : {heart_rate} BPM")
                    await send_data_to_clients(heart_rate)

                await client.start_notify(HEART_RATE_UUID, callback)

                # Lire le niveau de la batterie toutes les 5 secondes
                async def battery_level_callback():
                    battery_level = await client.read_gatt_char(BATTERY_LEVEL_UUID)
                    battery_percentage = battery_level[0]  # Le niveau de la batterie est un octet
                    battery_level_display.write(f"🔋 {battery_percentage}%")
                    await asyncio.sleep(5)  # Attendre 5 secondes avant de vérifier à nouveau

                asyncio.create_task(battery_level_callback()) # lecture du niv de batterie en // de la FC

                while True:
                    await asyncio.sleep(1)

    if not polar_device_found:
        st.error("❌ Aucun Polar H10 détecté.")

# Envoi des données aux clients WebSocket (Unity)
async def send_data_to_clients(heart_rate):
    """Envoie la fréquence cardiaque aux clients WebSocket connectés"""
    if not clients:
        status_ws.warning("⚠️ Aucun client WebSocket connecté.")
        return

    message = str(heart_rate)
    status_send.write(f"📤 Envoi de la FC : {message}")
    await asyncio.gather(*[client.send(message) for client in clients])

# Gestion des connexions WebSocket avec Unity
async def websocket_handler(websocket, path):
    """Gère la connexion WebSocket avec Unity."""
    clients.add(websocket)
    status_ws.write(f"🔗 Unity connecté (Total : {len(clients)})")

    try:
        async for message in websocket:
            st.write(f"📩 Message reçu depuis Unity : {message}")
    except websockets.ConnectionClosed as e:
        status_ws.warning(f"⚠️ Unity déconnecté : {e}")
    finally:
        clients.remove(websocket)
        status_ws.write("🔴 WebSocket déconnecté.")

# Lancement du serveur WebSocket et connexion au Polar H10
async def start_server():
    """Démarre le serveur WebSocket et la connexion au Polar H10."""
    server = await websockets.serve(partial(websocket_handler, path="/"), "0.0.0.0", 8765)
    status_ws.success("🚀 Serveur WebSocket lancé sur ws://0.0.0.0:8765")
    await asyncio.gather(server.wait_closed(), connect_polar_h10())

# Gestion des boutons Streamlit
if start_button:
    asyncio.run(start_server())

if stop_button:
    status_ws.write("⛔ Relancez l'appli pour recommencer.")


