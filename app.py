import streamlit as st
import streamlit.components.v1 as components
import paho.mqtt.client as mqtt
import json
import time
import random
from bokeh.models import CustomJS
from bokeh.models.widgets import Button
from streamlit_bokeh_events import streamlit_bokeh_events

WOKWI_PROJECT_ID = "479234255516779521"

st.set_page_config(
    page_title="Control Vocal // Gemelo Digital",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed"
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
[data-testid="stSidebar"] { display: none !important; }

.block-container {
    max-width: 1400px !important;
    padding-top: 1.2rem !important;
    padding-bottom: 2rem !important;
}

.panel-card {
    background: linear-gradient(145deg, #0d152d 0%, #070d1e 100%);
    border: 1px solid rgba(56, 189, 248, 0.25);
    border-top: 3px solid #38bdf8;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 1.2rem;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
}

div[data-testid="stCustomComponentV1"], iframe {
    background: transparent !important;
    border: none !important;
    display: block !important;
    margin: 0 auto !important;
}
</style>
""", unsafe_allow_html=True)

# Estilización de botón Bokeh
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
                        html, body { background: transparent !important; margin: 0 !important; overflow: hidden !important; }
                        .bk-root { display: flex !important; justify-content: center !important; width: 100% !important; }
                        .bk-btn {
                            background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 50%, #0284c7 100%) !important;
                            color: #ffffff !important;
                            border: 1px solid rgba(56, 189, 248, 0.4) !important;
                            border-radius: 25px !important;
                            font-family: 'Plus Jakarta Sans', sans-serif !important;
                            font-weight: 600 !important;
                            font-size: 0.92rem !important;
                            padding: 10px 24px !important;
                            box-shadow: 0 0 16px rgba(37, 99, 235, 0.5) !important;
                            cursor: pointer !important;
                            width: 260px !important;
                            height: 44px !important;
                        }
                    `;
                    doc.head.appendChild(style);
                }
            } catch(e) {}
        });
    }
    setInterval(fixBokehButton, 100);
})();
</script>
""", height=0, width=0)

# ==============================================================================
# GATEWAY DE VOZ
# ==============================================================================
def create_mqtt_client(client_prefix: str) -> mqtt.Client:
    cid = f"{client_prefix}_{int(time.time())}_{random.randint(1000, 9999)}"
    try:
        return mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=cid)
    except (AttributeError, TypeError):
        return mqtt.Client(client_id=cid, clean_session=True)

class VoiceCommandGateway:
    def __init__(self, broker: str = "broker.mqttdashboard.com", port: int = 1883, device_id: str = "esp32_main"):
        self.device_id = device_id
        self.topic_digital = f"devices/{device_id}/cmd/digital"
        self.topic_analog = f"devices/{device_id}/cmd/analog"
        
        self._client = create_mqtt_client("Streamlit_Voice")
        try:
            self._client.connect(broker, port, keepalive=30)
            self._client.loop_start()
        except Exception:
            pass

    def dispatch(self, transcript: str):
        t = transcript.lower().strip()
        
        if any(w in t for w in ["enciende", "prende", "encender", "activar luz"]):
            self._client.publish(self.topic_digital, json.dumps({"state": "ON"}), qos=1)
            return "💡 Luz activada (ON)"
            
        elif any(w in t for w in ["apaga", "apagar", "desactiva", "desactivar luz"]):
            self._client.publish(self.topic_digital, json.dumps({"state": "OFF"}), qos=1)
            return "🌑 Luz desactivada (OFF)"
            
        elif any(w in t for w in ["abre", "abrir", "porton", "compuerta abierta"]):
            self._client.publish(self.topic_analog, json.dumps({"angle": 180}), qos=1)
            return "🚪 Servomotor a 180° (Apertura)"
            
        elif any(w in t for w in ["cierra", "cerrar", "bloquea", "compuerta cerrada"]):
            self._client.publish(self.topic_analog, json.dumps({"angle": 0}), qos=1)
            return "🔒 Servomotor a 0° (Cierre)"
            
        return f"Comando no reconocido: '{transcript}'"

@st.cache_resource
def get_voice_gateway() -> VoiceCommandGateway:
    return VoiceCommandGateway()

gateway = get_voice_gateway()

# ==============================================================================
# INTERFAZ Y PANTALLA DIVIDIDA
# ==============================================================================
st.title("🎙️ Control Vocal // Gemelo Digital")
st.caption(f"Traducción automática de comandos hacia `{gateway.device_id}`")

col_voice, col_twin = st.columns([1, 1.35], gap="large")

with col_voice:
    st.markdown("""
    <div class="panel-card" style="text-align:center;">
        <div style="font-size:1.1rem; font-weight:600; color:#ffffff;">Módulo de Entrada Acústica</div>
        <div style="font-size:0.86rem; color:#94a3b8; margin-top:4px;">
            Presione el botón e indique órdenes: <i>"enciende la luz"</i>, <i>"apaga la luz"</i>, <i>"abre la compuerta"</i> o <i>"cierra la compuerta"</i>.
        </div>
    </div>
    """, unsafe_allow_html=True)

    stt_button = Button(label="🎙️ Iniciar Reconocimiento", width=260, height=44)
    stt_button.js_on_event("button_click", CustomJS(code="""
        var SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRec) {
            alert("El navegador no soporta reconocimiento de voz nativo.");
            return;
        }
        var rec = new SpeechRec();
        rec.continuous = false;
        rec.interimResults = false;
        rec.lang = 'es-CO';
        rec.onresult = function (e) {
            var val = e.results[0][0].transcript;
            if (val != "") {
                document.dispatchEvent(new CustomEvent("GET_VOICE_TEXT", {detail: val}));
            }
        };
        rec.start();
    """))

    result = streamlit_bokeh_events(
        stt_button,
        events="GET_VOICE_TEXT",
        key="voice_input",
        refresh_on_update=False,
        override_height=52,
        debounce_time=0
    )

    if result and "GET_VOICE_TEXT" in result:
        texto = str(result.get("GET_VOICE_TEXT")).strip()
        resultado = gateway.dispatch(texto)
        
        st.write("")
        st.markdown(f"""
        <div style="background:#0a1128; border:1px solid rgba(56,189,248,0.25); border-left:4px solid #38bdf8; border-radius:8px; padding:16px;">
            <div style="font-size:0.72rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.1em; font-family:'JetBrains Mono';">Entrada detectada:</div>
            <div style="font-size:1.05rem; font-weight:600; color:#ffffff; margin:4px 0 8px 0;">"{texto}"</div>
            <div style="font-size:0.72rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.1em; font-family:'JetBrains Mono';">Acción Ejecutada:</div>
            <div style="font-size:0.95rem; color:#2dd4bf; font-weight:600;">{resultado}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div class="panel-card" style="margin-top:1.2rem;">
        <div style="font-family:'JetBrains Mono'; font-size:0.72rem; color:#38bdf8; text-transform:uppercase; letter-spacing:0.1em; font-weight:600; margin-bottom:6px;">Diccionario de Comandos</div>
        <div style="font-size:0.84rem; color:#cbd5e1; line-height:1.6;">
            ● <b>"Enciende la luz"</b> → LED en HIGH<br>
            ● <b>"Apaga la luz"</b> → LED en LOW<br>
            ● <b>"Abre la compuerta"</b> → Servomotor a 180°<br>
            ● <b>"Cierra la compuerta"</b> → Servomotor a 0°
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_twin:
    components.html(
        f"""
        <div style="background: linear-gradient(145deg, #0d152d 0%, #080d1e 100%);
                    border: 1px solid rgba(56, 189, 248, 0.28);
                    border-top: 3px solid #38bdf8;
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.7), 0 0 20px rgba(56,189,248,0.12);">
            <div style="display: flex; justify-content: space-between; align-items: center;
                        padding: 10px 16px; background: rgba(6, 9, 19, 0.9);
                        border-bottom: 1px solid rgba(56, 189, 248, 0.2);
                        font-family: 'JetBrains Mono', monospace; font-size: 0.72rem;">
                <div style="color: #cbd5e1; display: flex; align-items: center; gap: 8px;">
                    <span style="color: #38bdf8;">✦</span> GEMELO DIGITAL // ESP32 WOKWI
                </div>
                <div style="color: #2dd4bf; display: flex; align-items: center; gap: 6px;">
                    <span style="display:inline-block; width:7px; height:7px; border-radius:50%; background:#2dd4bf; box-shadow:0 0 8px #2dd4bf;"></span>
                    CANAL ACTIVO
                </div>
            </div>
            <iframe 
                src="https://wokwi.com/projects/{WOKWI_PROJECT_ID}?embed=1&view=diagram" 
                width="100%" 
                height="530" 
                style="border: none; display: block; background: #0c1222;"
                allow="fullscreen; autoplay">
            </iframe>
        </div>
        """,
        height=580
    )
