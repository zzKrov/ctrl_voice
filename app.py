import streamlit as st
import streamlit.components.v1 as components
import paho.mqtt.client as mqtt
import json
import random
import string
from bokeh.models import CustomJS
from bokeh.models.widgets import Button
from streamlit_bokeh_events import streamlit_bokeh_events

# ------------------------------------------------------------------
# CONFIGURACIÓN GENERAL
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Control por Voz // Krov",
    page_icon="🎙️",
    layout="centered"
)

# ------------------------------------------------------------------
# ESTILOS OSCUROS
# ------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], .stApp {
    background-color: #04060a !important;
    color: #f1f5f9 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

[data-testid="stHeader"] { background: transparent !important; }

/* Elimina el cuadro blanco del contenedor de Bokeh */
div[data-testid="stCustomComponentV1"], iframe {
    background: transparent !important;
    border: none !important;
    display: block !important;
    margin: 0 auto !important;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# INYECCIÓN QUE ELIMINA EL BOTÓN BLANCO DENTRO DEL IFRAME DE BOKEH
# ------------------------------------------------------------------
components.html("""
<script>
(function() {
    function fixBokehButton() {
        const iframes = window.parent.document.querySelectorAll('iframe');
        iframes.forEach(f => {
            try {
                const doc = f.contentDocument || f.contentWindow.document;
                if (doc && doc.querySelector('.bk-btn') && !doc.getElementById('krov-dark-button-fix')) {
                    doc.body.style.background = 'transparent';
                    doc.documentElement.style.background = 'transparent';
                    f.style.background = 'transparent';
                    f.style.border = 'none';

                    const style = doc.createElement('style');
                    style.id = 'krov-dark-button-fix';
                    style.innerHTML = `
                        html, body {
                            background: transparent !important;
                            margin: 0 !important;
                            padding: 0 !important;
                            overflow: hidden !important;
                        }
                        .bk-root {
                            background: transparent !important;
                            display: flex !important;
                            justify-content: center !important;
                            align-items: center !important;
                            width: 100% !important;
                        }
                        .bk-btn, .bk-btn-default {
                            background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%) !important;
                            color: #ffffff !important;
                            border: 1px solid rgba(192, 132, 252, 0.7) !important;
                            border-radius: 25px !important;
                            font-family: 'Plus Jakarta Sans', sans-serif !important;
                            font-weight: 700 !important;
                            font-size: 0.95rem !important;
                            letter-spacing: 0.04em !important;
                            padding: 10px 24px !important;
                            box-shadow: 0 0 20px rgba(124, 58, 237, 0.5) !important;
                            cursor: pointer !important;
                            transition: all 0.2s ease !important;
                            outline: none !important;
                            width: 260px !important;
                            height: 44px !important;
                        }
                        .bk-btn:hover {
                            background: linear-gradient(135deg, #9333ea 0%, #c084fc 100%) !important;
                            box-shadow: 0 0 30px rgba(192, 132, 252, 0.8) !important;
                            transform: translateY(-1px) !important;
                        }
                    `;
                    doc.head.appendChild(style);
                }
            } catch(e) {}
        });
    }
    setInterval(fixBokehButton, 80);
})();
</script>
""", height=0, width=0)

# ------------------------------------------------------------------
# ESTADO
# ------------------------------------------------------------------
if 'vox_xp' not in st.session_state:
    st.session_state.vox_xp = 50
if 'last_cmd' not in st.session_state:
    st.session_state.last_cmd = "Sin órdenes recientes"
if 'matched_action' not in st.session_state:
    st.session_state.matched_action = "Esperando voz..."

# ------------------------------------------------------------------
# PARSER DE COMANDOS NATURALES
# ------------------------------------------------------------------
def interpretar_comando(txt):
    t = txt.lower().strip()
    if any(w in t for w in ["enciende", "prende", "encender", "prender", "luz on", "luces on"]):
        return {"topic_suffix": "cmqtt_s", "payload": {"Act1": "ON"}, "action": "💡 Encender luz"}
    if any(w in t for w in ["apaga", "apagar", "desactiva", "luz off", "luces off", "corta"]):
        return {"topic_suffix": "cmqtt_s", "payload": {"Act1": "OFF"}, "action": "🌑 Apagar luz"}
    if any(w in t for w in ["abre", "abrir", "puerta abierta", "porton", "compuerta abierta"]):
        return {"topic_suffix": "cmqtt_a", "payload": {"Analog": 100.0}, "action": "🚪 Abrir puerta (180°)"}
    if any(w in t for w in ["cierra", "cerrar", "puerta cerrada", "bloquea"]):
        return {"topic_suffix": "cmqtt_a", "payload": {"Analog": 0.0}, "action": "🔒 Cerrar puerta (0°)"}
    return {"topic_suffix": "voice_ctrl", "payload": {"Act1": t}, "action": f"Mensaje libre: '{t}'"}

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
    st.markdown("### Configuración de Voz")
    broker = st.text_input("Broker:", value="broker.mqttdashboard.com")
    port = st.number_input("Puerto:", value=1883)
    prefijo = st.text_input("Nombre de tu proyecto Wokwi:", value="lizalda")
    
    st.divider()
    st.markdown(f"**Puntos de voz:** `{st.session_state.vox_xp}`")

# ------------------------------------------------------------------
# TARJETA PRINCIPAL AUTOCONTENIDA
# ------------------------------------------------------------------
st.markdown("""
<div style="background: linear-gradient(145deg, #120e22 0%, #080612 100%); border:1px solid rgba(192,132,252,0.3); border-top:3px solid #c084fc; border-radius:12px; padding:24px; text-align:center; box-shadow:0 12px 30px rgba(0,0,0,0.8); margin-bottom:1.2rem;">
    <svg width="60" height="60" viewBox="0 0 100 100" style="margin: 0 auto 8px auto; display:block;">
        <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(192, 132, 252, 0.3)" stroke-width="2"/>
        <circle cx="50" cy="50" r="26" fill="none" stroke="#c084fc" stroke-width="1.8"/>
        <circle cx="50" cy="50" r="12" fill="rgba(192, 132, 252, 0.4)"/>
    </svg>
    <div style="font-size:1.6rem; font-weight:700; color:#ffffff;">Control por Voz</div>
    <div style="font-size:0.9rem; color:#94a3b8; margin-top:4px;">
        Presiona el botón, di un comando como <i>"enciende la luz"</i> o <i>"abre la puerta"</i> y el sistema lo enviará a tu circuito.
    </div>
</div>
""", unsafe_allow_html=True)

# Botón STT Bokeh
stt_button = Button(label="🎙️ Activar Micrófono", width=260, height=44)
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
    override_height=52,
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
        st.session_state.vox_xp += 20
        st.success(f"✅ Orden enviada al circuito: {interp['action']}")
    else:
        st.error(f"No se pudo enviar la orden: {err}")

st.write("")

# Tarjeta de respuesta de una sola pieza (autocontenida)
st.markdown(f"""
<div style="background:#0d0a17; border:1px solid rgba(192,132,252,0.25); border-left:4px solid #c084fc; border-radius:8px; padding:16px;">
    <div style="font-size:0.75rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.1em; font-family:'JetBrains Mono';">Lo que escuché:</div>
    <div style="font-size:1.15rem; font-weight:600; color:#ffffff; margin:4px 0 8px 0;">"{st.session_state.last_cmd}"</div>
    <div style="font-size:0.75rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.1em; font-family:'JetBrains Mono';">Acción realizada:</div>
    <div style="font-size:1rem; color:#00ff88; font-weight:700;">{st.session_state.matched_action}</div>
</div>
""", unsafe_allow_html=True)
