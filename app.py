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
# CONFIGURACIÓN GENERAL
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Krov VOX-LINK // Control Vocal Ciberfísico",
    page_icon="🎙️",
    layout="centered"
)

# ------------------------------------------------------------------
# ESTILOS KROV NOIR
# ------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;600;700&family=Spectral:wght@600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], .stApp {
    background-color: #030407 !important;
    color: #f1f5f9 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

[data-testid="stHeader"] { background: transparent !important; }

/* Contenedores nativos estilizados: CERO cajas vacías */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(145deg, rgba(16, 12, 30, 0.95) 0%, rgba(6, 4, 14, 0.98) 100%) !important;
    border: 1px solid rgba(192, 132, 252, 0.3) !important;
    border-top: 3px solid #c084fc !important;
    border-radius: 12px !important;
    padding: 1.5rem !important;
    box-shadow: 0 12px 35px rgba(0, 0, 0, 0.8) !important;
    margin-bottom: 1.2rem !important;
}

.radar-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.2em;
    color: #c084fc;
    text-transform: uppercase;
}

iframe {
    background: transparent !important;
    display: block;
    margin: 0 auto;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# ESTADO
# ------------------------------------------------------------------
if 'vox_xp' not in st.session_state:
    st.session_state.vox_xp = 80
if 'last_cmd' not in st.session_state:
    st.session_state.last_cmd = "Sin órdenes registradas"
if 'matched_action' not in st.session_state:
    st.session_state.matched_action = "EN ESPERA"

# ------------------------------------------------------------------
# PARSER DIFUSO DE VOZ
# ------------------------------------------------------------------
def interpretar_comando(txt):
    t = txt.lower().strip()
    if any(w in t for w in ["enciende", "prende", "encender", "prender", "luz on", "luces on"]):
        return {"topic_suffix": "cmqtt_s", "payload": {"Act1": "ON"}, "action": "💡 ENCENDER LUCES"}
    if any(w in t for w in ["apaga", "apagar", "desactiva", "luz off", "luces off", "corta"]):
        return {"topic_suffix": "cmqtt_s", "payload": {"Act1": "OFF"}, "action": "🌑 APAGAR LUCES"}
    if any(w in t for w in ["abre", "abrir", "puerta abierta", "porton", "compuerta abierta"]):
        return {"topic_suffix": "cmqtt_a", "payload": {"Analog": 100.0}, "action": "🚪 ABRIR COMPUERTA (180°)"}
    if any(w in t for w in ["cierra", "cerrar", "puerta cerrada", "bloquea"]):
        return {"topic_suffix": "cmqtt_a", "payload": {"Analog": 0.0}, "action": "🔒 CERRAR COMPUERTA (0°)"}
    return {"topic_suffix": "voice_ctrl", "payload": {"Act1": t}, "action": f"🗣️ COMANDO PERSONALIZADO: '{t}'"}

# ------------------------------------------------------------------
# CLIENTE MQTT
# ------------------------------------------------------------------
def emitir_orden(broker, port, topic, payload):
    cid = f"Krov_Vox_{''.join(random.choices(string.ascii_letters + string.digits, k=6))}"
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cid)
    except Exception:
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=cid)
        except Exception:
            client = mqtt.Client(client_id=cid)
            
    try:
        client.connect(broker, port, keepalive=15)
        client.loop_start()
        client.publish(topic, json.dumps(payload), qos=1).wait_for_publish(timeout=2.5)
        client.loop_stop()
        client.disconnect()
        return True, None
    except Exception as e:
        return False, str(e)

# ------------------------------------------------------------------
# BARRA LATERAL
# ------------------------------------------------------------------
with st.sidebar:
    st.markdown("### KROV // PARÁMETROS VOZ")
    broker = st.text_input("Broker:", value="broker.mqttdashboard.com")
    port = st.number_input("Puerto:", value=1883)
    prefijo = st.text_input("Prefijo de Tópico (opcional):", value="lizalda")
    
    st.divider()
    st.markdown(f"**XP de Enlace Vocal:** `{st.session_state.vox_xp}`")
    st.markdown(f"**Nivel de Autorización:** `VOX-{min(st.session_state.vox_xp // 60, 5)}`")

# ------------------------------------------------------------------
# BANNER PRINCIPAL (100% AUTOCONTENIDO)
# ------------------------------------------------------------------
st.markdown("""
<div style="background:linear-gradient(145deg, rgba(16,12,30,0.95), rgba(6,4,14,0.98)); border:1px solid rgba(192,132,252,0.3); border-top:3px solid #c084fc; border-radius:12px; padding:24px; text-align:center; box-shadow:0 12px 35px rgba(0,0,0,0.8); margin-bottom:1.2rem;">
    <div class="radar-badge">● PROTOCOLO CIBERFÍSICO VOX-LINK ACTIVO</div>
    <svg width="100" height="100" viewBox="0 0 100 100" style="margin: 12px auto; display:block;">
        <circle cx="50" cy="50" r="44" fill="none" stroke="rgba(192, 132, 252, 0.2)" stroke-width="2"/>
        <circle cx="50" cy="50" r="28" fill="none" stroke="#c084fc" stroke-width="1.5" stroke-dasharray="6 4"/>
        <circle cx="50" cy="50" r="14" fill="rgba(192, 132, 252, 0.25)" stroke="#00f0ff" stroke-width="2"/>
        <path d="M 45 42 L 55 42 M 50 35 L 50 55 M 43 55 L 57 55" stroke="#ffffff" stroke-width="2" stroke-linecap="round"/>
    </svg>
    <div style="font-family:'Spectral', Georgia; font-size:1.7rem; font-weight:700;">Reconocimiento Vocal de Órdenes</div>
    <div style="font-size:0.86rem; color:#94a3b8; margin-top:4px;">Pulsa el botón, acepta el permiso de micrófono y habla en español (Chrome o Edge).</div>
</div>
""", unsafe_allow_html=True)

# Botón STT Bokeh
stt_button = Button(label="🎙️ ACTIVAR MICRÓFONO", width=260, height=48)
stt_button.js_on_event("button_click", CustomJS(code="""
    var SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
        alert("El navegador no soporta reconocimiento de voz. Usa Google Chrome o Microsoft Edge.");
        return;
    }
    var rec = new SpeechRec();
    rec.continuous = false;
    rec.interimResults = false;
    rec.lang = 'es-CO';

    rec.onresult = function (e) {
        var val = e.results[0][0].transcript;
        if (val != "") {
            document.dispatchEvent(new CustomEvent("GET_TEXT", {detail: val}));
        }
    };
    rec.start();
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
# PROCESAMIENTO REACTIVO
# ------------------------------------------------------------------
if result and "GET_TEXT" in result:
    texto = str(result.get("GET_TEXT")).strip()
    interp = interpretar_comando(texto)
    
    base_top = prefijo.strip().rstrip('/')
    topic_final = f"{base_top}/{interp['topic_suffix']}" if base_top else interp['topic_suffix']
    
    ok, err = emitir_orden(broker, int(port), topic_final, interp['payload'])
    
    if ok:
        st.session_state.last_cmd = texto
        st.session_state.matched_action = interp['action']
        st.session_state.vox_xp += 25
        st.success(f"✅ Transmitido al ESP32: **{interp['action']}**")
    else:
        st.error(f"Falla de emisión MQTT: {err}")

# Panel de Telemetría Vocal (Nativo con border=True: CERO cajas vacías)
with st.container(border=True):
    st.markdown('<div style="font-family:\'JetBrains Mono\'; font-size:0.75rem; color:#d4af37;">ÚLTIMA LOCUCIÓN CAPTURADA:</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:1.15rem; font-weight:600; color:#ffffff; margin: 4px 0 10px 0;">"{st.session_state.last_cmd}"</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-family:\'JetBrains Mono\'; font-size:0.75rem; color:#00f0ff;">ACCIÓN CIBERFÍSICA ASOCIADA:</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:1.05rem; color:#00ff88; font-weight:700;">{st.session_state.matched_action}</div>', unsafe_allow_html=True)
