import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
import random
import string
from bokeh.models import CustomJS
from bokeh.models.widgets import Button
from streamlit_bokeh_events import streamlit_bokeh_events

# ------------------------------------------------------------------
# CONFIGURACIÓN & ESTILOS KROV NOIR
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Krov VOX-LINK // Control Vocal Ciberfísico",
    page_icon="🎙️",
    layout="centered"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;600;700&family=Spectral:wght@600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], .stApp {
    background-color: #030407 !important;
    color: #f1f5f9 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

[data-testid="stHeader"] { background: transparent !important; }

.vox-card {
    background: linear-gradient(145deg, rgba(16, 12, 30, 0.95) 0%, rgba(6, 4, 14, 0.98) 100%);
    border: 1px solid rgba(192, 132, 252, 0.3);
    border-top: 3px solid #c084fc;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 12px 35px rgba(0, 0, 0, 0.8);
    text-align: center;
    margin-bottom: 16px;
}

.radar-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.2em;
    color: #c084fc;
    text-transform: uppercase;
}

/* Ocultar artefactos de Bokeh */
iframe {
    background: transparent !important;
    display: block;
    margin: 0 auto;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# ESTADO DE SESIÓN & GAMIFICACIÓN
# ------------------------------------------------------------------
if 'vox_xp' not in st.session_state:
    st.session_state.vox_xp = 50
if 'last_cmd' not in st.session_state:
    st.session_state.last_cmd = "Sin órdenes registradas"
if 'matched_action' not in st.session_state:
    st.session_state.matched_action = "EN ESPERA"

# ------------------------------------------------------------------
# PARSER DIFUSO DE VOZ (MAPEO NATURAL A WOKWI)
# ------------------------------------------------------------------
def interpretar_comando_voz(texto_reconocido):
    t = texto_reconocido.lower().strip()
    
    # 1. Luz / LED ON
    if any(w in t for w in ["enciende", "prende", "encender", "prender", "luz on", "luces on", "abrir luz"]):
        return {"topic_suffix": "cmqtt_s", "payload": {"Act1": "ON"}, "action": "💡 ENCENDER LUCES"}
        
    # 2. Luz / LED OFF
    if any(w in t for w in ["apaga", "apagar", "desactiva", "luz off", "luces off", "corta"]):
        return {"topic_suffix": "cmqtt_s", "payload": {"Act1": "OFF"}, "action": "🌑 APAGAR LUCES"}
        
    # 3. Servo / Compuerta Abierta (180°)
    if any(w in t for w in ["abre", "abrir", "puerta abierta", "porton", "compuerta abierta", "despliega"]):
        return {"topic_suffix": "cmqtt_a", "payload": {"Analog": 100.0}, "action": "🚪 ABRIR COMPUERTA (180°)"}
        
    # 4. Servo / Compuerta Cerrada (0° o 90°)
    if any(w in t for w in ["cierra", "cerrar", "puerta cerrada", "bloquea", "retrae"]):
        return {"topic_suffix": "cmqtt_a", "payload": {"Analog": 0.0}, "action": "🔒 CERRAR COMPUERTA (0°)"}
        
    # 5. Modo Genérico (publica el texto literal)
    return {"topic_suffix": "voice_ctrl", "payload": {"Act1": t}, "action": f"🗣️ COMANDO PERSONALIZADO: '{t}'"}

# ------------------------------------------------------------------
# PUBLICADOR MQTT
# ------------------------------------------------------------------
def emitir_orden_mqtt(broker, port, topic, payload):
    cid = f"Krov_Vox_{''.join(random.choices(string.ascii_letters + string.digits, k=6))}"
    try:
        import paho.mqtt.enums as mqtt_enums
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cid)
    except Exception:
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=cid)
        except Exception:
            client = mqtt.Client(client_id=cid)
            
    try:
        client.connect(broker, port, keepalive=15)
        client.loop_start()
        client.publish(topic, json.dumps(payload), qos=1).wait_for_publish(timeout=3.0)
        client.loop_stop()
        client.disconnect()
        return True, None
    except Exception as e:
        return False, str(e)

# ------------------------------------------------------------------
# BARRA LATERAL
# ------------------------------------------------------------------
with st.sidebar:
    st.markdown("**CANAL BROKER // VOZ**")
    broker = st.text_input("Broker:", value="broker.mqttdashboard.com")
    port = st.number_input("Puerto:", value=1883)
    prefijo = st.text_input("Prefijo de Usuario / Wokwi:", value="lizalda")
    
    st.divider()
    st.markdown(f"**XP de Enlace Vocal:** `{st.session_state.vox_xp}`")
    st.markdown(f"**Nivel Operativo:** `VOX-{min(st.session_state.vox_xp // 50, 5)}`")

# ------------------------------------------------------------------
# VISOR HOLOGRÁFICO PROCEDURAL (SIN NECESIDAD DE IMÁGENES LOCALES)
# ------------------------------------------------------------------
st.markdown("""
<div class="vox-card">
    <div class="radar-badge">● PROTOCOLO CIBERFÍSICO VOX-LINK ACTIVO</div>
    <svg width="120" height="120" viewBox="0 0 100 100" style="margin: 15px auto;">
        <circle cx="50" cy="50" r="45" fill="none" stroke="rgba(192, 132, 252, 0.2)" stroke-width="2"/>
        <circle cx="50" cy="50" r="30" fill="none" stroke="#c084fc" stroke-width="1.5" stroke-dasharray="6 4"/>
        <circle cx="50" cy="50" r="14" fill="rgba(192, 132, 252, 0.25)" stroke="#00f0ff" stroke-width="2"/>
        <path d="M 45 42 L 55 42 M 50 35 L 50 55 M 43 55 L 57 55" stroke="#ffffff" stroke-width="2" stroke-linecap="round"/>
    </svg>
    <div style="font-family:'Spectral', Georgia; font-size:1.8rem; font-weight:700;">Reconocimiento Vocal de Órdenes</div>
    <div style="font-size:0.88rem; color:#94a3b8; margin-top:4px;">Presiona el botón, acepta el micrófono en Chrome/Edge y dicta tu instrucción en español.</div>
</div>
""", unsafe_allow_html=True)

# Botón STT con Bokeh
stt_button = Button(label="🎙️ ACTIVAR MICRÓFONO", width=260, height=48)
stt_button.js_on_event("button_click", CustomJS(code="""
    var SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
        alert("El navegador no soporta reconocimiento de voz. Usa Google Chrome o Microsoft Edge.");
        return;
    }
    var recognition = new SpeechRec();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'es-CO';

    recognition.onresult = function (e) {
        var value = e.results[0][0].transcript;
        if (value != "") {
            document.dispatchEvent(new CustomEvent("GET_TEXT", {detail: value}));
        }
    };
    recognition.start();
"""))

result = streamlit_bokeh_events(
    stt_button,
    events="GET_TEXT",
    key="listen_voice",
    refresh_on_update=False,
    override_height=65,
    debounce_time=0
)

# ------------------------------------------------------------------
# PROCESAMIENTO REACTIVO DE LA ORDEN
# ------------------------------------------------------------------
if result and "GET_TEXT" in result:
    texto = str(result.get("GET_TEXT")).strip()
    interpretacion = interpretar_comando_voz(texto)
    
    # Determinar tópico según prefijo
    base_top = prefijo.strip().rstrip('/')
    topic_final = f"{base_top}/{interpretacion['topic_suffix']}" if base_top else interpretacion['topic_suffix']
    
    ok, err = emitir_orden_mqtt(broker, int(port), topic_final, interpretacion['payload'])
    
    if ok:
        st.session_state.last_cmd = texto
        st.session_state.matched_action = interpretacion['action']
        st.session_state.vox_xp += 20
        st.success(f"✅ Transmitido al ESP32: **{interpretacion['action']}**")
    else:
        st.error(f"Falla de emisión MQTT: {err}")

# Panel de Telemetría Vocal
st.markdown(f"""
<div style="background:rgba(12, 16, 26, 0.85); border:1px solid rgba(255,255,255,0.08); border-radius:8px; padding:16px;">
    <div style="font-family:'JetBrains Mono'; font-size:0.75rem; color:#d4af37;">ÚLTIMA LOCUCIÓN DETECTADA:</div>
    <div style="font-size:1.15rem; font-weight:600; color:#ffffff; margin: 4px 0 10px 0;">"{st.session_state.last_cmd}"</div>
    <div style="font-family:'JetBrains Mono'; font-size:0.75rem; color:#00f0ff;">ACCIÓN CIBERFÍSICA ASOCIADA:</div>
    <div style="font-size:1rem; color:#00ff88; font-weight:700;">{st.session_state.matched_action}</div>
</div>
""", unsafe_allow_html=True)
