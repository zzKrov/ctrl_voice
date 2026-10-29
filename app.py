import streamlit as st
import streamlit.components.v1 as components
import paho.mqtt.client as mqtt
import json
import random
import string
from bokeh.models import CustomJS
from bokeh.models.widgets import Button
from streamlit_bokeh_events import streamlit_bokeh_events

st.set_page_config(
    page_title="Control por Voz // IoT",
    page_icon="🎙️",
    layout="centered"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Plus+Jakarta+Sans:wght@400;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], .stApp {
    background-color: #060913 !important;
    color: #e2e8f0 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

[data-testid="stHeader"] { background: transparent !important; }

div[data-testid="stCustomComponentV1"], iframe {
    background: transparent !important;
    border: none !important;
    display: block !important;
    margin: 0 auto !important;
}
</style>
""", unsafe_allow_html=True)

# Inyección para estilizar el botón de Bokeh en paleta Galaxy Blue
components.html("""
<script>
(function() {
    function fixBokehButton() {
        const iframes = window.parent.document.querySelectorAll('iframe');
        iframes.forEach(f => {
            try {
                const doc = f.contentDocument || f.contentWindow.document;
                if (doc && doc.querySelector('.bk-btn') && !doc.getElementById('galaxy-btn-fix')) {
                    doc.body.style.background = 'transparent';
                    doc.documentElement.style.background = 'transparent';
                    f.style.background = 'transparent';
                    f.style.border = 'none';

                    const style = doc.createElement('style');
                    style.id = 'galaxy-btn-fix';
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
                            background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 50%, #0284c7 100%) !important;
                            color: #ffffff !important;
                            border: 1px solid rgba(56, 189, 248, 0.45) !important;
                            border-radius: 25px !important;
                            font-family: 'Plus Jakarta Sans', sans-serif !important;
                            font-weight: 600 !important;
                            font-size: 0.92rem !important;
                            padding: 10px 24px !important;
                            box-shadow: 0 0 16px rgba(37, 99, 235, 0.5) !important;
                            cursor: pointer !important;
                            transition: all 0.2s ease !important;
                            outline: none !important;
                            width: 260px !important;
                            height: 44px !important;
                        }
                        .bk-btn:hover {
                            box-shadow: 0 0 25px rgba(56, 189, 248, 0.7) !important;
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

if 'last_cmd' not in st.session_state:
    st.session_state.last_cmd = "Sin órdenes recientes"
if 'matched_action' not in st.session_state:
    st.session_state.matched_action = "Esperando entrada de voz..."

def interpretar_comando(txt):
    t = txt.lower().strip()
    if any(w in t for w in ["enciende", "prende", "encender", "prender", "luz on", "luces on"]):
        return {"topic_suffix": "cmqtt_s", "payload": {"Act1": "ON"}, "action": "💡 Encender luz"}
    if any(w in t for w in ["apaga", "apagar", "desactiva", "luz off", "luces off", "corta"]):
        return {"topic_suffix": "cmqtt_s", "payload": {"Act1": "OFF"}, "action": "🌑 Apagar luz"}
    if any(w in t for w in ["abre", "abrir", "puerta abierta", "porton", "compuerta abierta"]):
        return {"topic_suffix": "cmqtt_a", "payload": {"Analog": 100.0}, "action": "🚪 Abrir compuerta (180°)"}
    if any(w in t for w in ["cierra", "cerrar", "puerta cerrada", "bloquea"]):
        return {"topic_suffix": "cmqtt_a", "payload": {"Analog": 0.0}, "action": "🔒 Cerrar compuerta (0°)"}
    return {"topic_suffix": "cmqtt_s", "payload": {"Act1": t}, "action": f"Comando libre transmitido: '{t}'"}

def emitir_orden(broker, port, topic, payload):
    cid = f"Vox_Client_{''.join(random.choices(string.ascii_letters + string.digits, k=6))}"
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

with st.sidebar:
    st.markdown("### Configuración de Enlace")
    broker = st.text_input("Broker MQTT:", value="broker.mqttdashboard.com")
    port = st.number_input("Puerto:", value=1883)
    prefijo = st.text_input("Prefijo de Usuario / Wokwi:", value="lizalda")

st.markdown("""
<div style="background: linear-gradient(145deg, #0d152d 0%, #070d1e 100%); border:1px solid rgba(56,189,248,0.3); border-top:3px solid #38bdf8; border-radius:12px; padding:22px; text-align:center; box-shadow:0 8px 25px rgba(0,0,0,0.7); margin-bottom:1.2rem;">
    <div style="font-size:1.5rem; font-weight:700; color:#ffffff;">Control por Voz</div>
    <div style="font-size:0.88rem; color:#94a3b8; margin-top:4px;">
        Presione el botón e indique una orden (ej. <i>"encender la luz"</i>, <i>"apagar la luz"</i>, <i>"abrir puerta"</i> o <i>"cerrar puerta"</i>).
    </div>
</div>
""", unsafe_allow_html=True)

stt_button = Button(label="🎙️ Iniciar Reconocimiento", width=260, height=44)
stt_button.js_on_event("button_click", CustomJS(code="""
    var SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
        alert("El navegador no soporta reconocimiento de voz nativo. Utilice Google Chrome o Microsoft Edge.");
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

if result and "GET_TEXT" in result:
    texto = str(result.get("GET_TEXT")).strip()
    interp = interpretar_comando(texto)
    
    base_top = prefijo.strip().rstrip('/')
    topic_final = f"{base_top}/{interp['topic_suffix']}" if base_top else interp['topic_suffix']
    
    ok, err = emitir_orden(broker, int(port), topic_final, interp['payload'])
    
    if ok:
        st.session_state.last_cmd = texto
        st.session_state.matched_action = interp['action']
        st.success(f"Comando transmitido: {interp['action']}")
    else:
        st.error(f"Falla de transmisión: {err}")

st.write("")

st.markdown(f"""
<div style="background:#0a1128; border:1px solid rgba(56,189,248,0.25); border-left:4px solid #38bdf8; border-radius:8px; padding:16px;">
    <div style="font-size:0.75rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.1em; font-family:'JetBrains Mono';">Entrada detectada:</div>
    <div style="font-size:1.1rem; font-weight:600; color:#ffffff; margin:4px 0 8px 0;">"{st.session_state.last_cmd}"</div>
    <div style="font-size:0.75rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.1em; font-family:'JetBrains Mono';">Acción ejecutada:</div>
    <div style="font-size:0.95rem; color:#2dd4bf; font-weight:600;">{st.session_state.matched_action}</div>
</div>
""", unsafe_allow_html=True)
