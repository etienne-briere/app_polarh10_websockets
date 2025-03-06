import asyncio
import websockets
import streamlit as st
from bleak import BleakClient, BleakScanner

# 🎯 Adresse du serveur WebSocket (remplace par l'URL Render/Railway)
SERVER_URL = "wss://test-websockets-5h6z.onrender.com/ws"

# UUID de la capteur cardiaque du Polar H10
HEART_RATE_UUID = "00002a37-0000-1000-8000-00805f9b34fb"
BATTERY_LEVEL_UUID = "00002a19-0000-1000-8000-00805f9b34fb"

# Interface Streamlit
st.title("💓📩 PolarH10 - WebSocket📩💓")

# Création des boutons
col1, col2 = st.columns(2)  # Création de 2 colonnes

with col1 :
    start_button = st.button("🚀 Connect and Send Heart Data")

with col2 :
    stop_button = st.button("❌ Stop")

# Zones d'affichage
status_connect = st.empty()  # Conteneur pour afficher les messages de l'état de connexion
battery_level_display = st.empty()

heart_rate_display = st.empty()  # Zone pour afficher la FC
status_ws = st.empty() # zone pour état du serveur WS
status_send = st.empty() # affiche l'envoie de la FC

async def send_heart_rate():
    """Trouve le Polar H10 et envoie la fréquence cardiaque au serveur WebSocket."""
    running = True  # Démarre l'envoi des données

    status_connect.write("🔍 Recherche du Polar H10...")
    devices = await BleakScanner.discover()

    polar_address = None
    for device in devices:
        if device.name and "Polar" in device.name:
            polar_address = device.address
            status_connect.write(f"✅ Polar H10 trouvé : {device.name} ({device.address})")

            # Connection au serveur WebSockets
            async with websockets.connect(SERVER_URL) as websocket:
                # Connexion au Polar identifié
                async with BleakClient(polar_address) as client:
                    status_connect.success(f"🔗 Connecté a {device.name} !")

                    async def callback(sender, data):
                        if not running:
                            return  # Stoppe l'envoi si le bouton stop est pressé
                        heart_rate = data[1]
                        heart_rate_display.write(f"❤️ FC : {heart_rate} BPM")

                        # Envoie la FC au serveur WebSocket
                        await websocket.send(str(heart_rate))
                        status_ws.write(f"📤 Envoyé au serveur WebSocket : {heart_rate} BPM")

                    await client.start_notify(HEART_RATE_UUID, callback)

                    # Lire le niveau de la batterie toutes les 5 secondes
                    async def battery_level_callback():
                        while running:
                            battery_level = await client.read_gatt_char(BATTERY_LEVEL_UUID)
                            battery_percentage = battery_level[0]  # Le niveau de la batterie est un octet
                            battery_level_display.write(f"🔋 {battery_percentage}%")
                            await asyncio.sleep(5)  # Attendre 5 secondes avant de vérifier à nouveau

                    asyncio.create_task(battery_level_callback())  # lecture du niv de batterie en // de la FC

                    # Boucle infinie pour garder la connexion active
                    while running:
                        await asyncio.sleep(1)

                    # Arrêt propre de la connexion BLE
                    await client.stop_notify(HEART_RATE_UUID)
                    status_connect.write("🔌 Déconnexion du Polar H10.")
                    await websocket.close()
                    status_ws.write("⛔ WebSocket fermé.")

    if not polar_address:
        status_connect.error("❌ Aucun Polar H10 détecté.")
        return

# Exécute le script
if start_button:
    asyncio.run(send_heart_rate())

if stop_button:
    running = False  # Arrête proprement la boucle
    status_ws.write("⛔ Arrêt demandé, fermeture en cours...")


