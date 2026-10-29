import streamlit as st
import streamlit.components.v1 as components
import paho.mqtt.client as mqtt
import json
import time
from bokeh.models import CustomJS
from bokeh.models.widgets import Button
from streamlit_bokeh_events import streamlit_bokeh_events

st.set_page_config(
    page_title="Control por Voz // IoT",
    page_icon="🎙️",
    layout="centered",
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

div[data-testid="stCustomComponentV1"], iframe {
    background: transparent !important;
    border: none !important;
    display: block !important;
    margin: 0 auto !important;
}
</style>
""", unsafe_allow_html=True)

# Inyección de estilo para el botón de Bokeh
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
# GATEWAY DE EMISIÓN DE VOZ
# ==============================================================================
class VoiceCommandGateway:
    def __init__(self, broker: str = "broker.mqttdashboard.com", port: int = 1883, device_id: str = "esp32_main"):
        self.device_id = device_id
        self.topic_digital = f"devices/{device_id}/cmd/digital"
        self.topic_analog = f"devices/{device_id}/cmd/analog"
        
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"Client_Voice_{device_id}"
        )
        try:
            self._client.connect(broker, port, keepalive=30)
            self._client.loop_start()
        except Exception:
            pass

    def dispatch(self, transcript: str):
        t = transcript.lower().strip()
        
        # Enrutamiento semántico
        if any(w in t for w in ["enciende", "prende", "encender", "activar luz"]):
            self._client.publish(self.topic_digital, json.dumps({"state": "ON"}), qos=1)
            return "💡 Luz activada (ON)"
            
        elif any(w in t for w in ["apaga", "apagar", "desactiva", "desactivar luz"]):
            self._client.publish(self.topic_digital, json.dumps({"state": "OFF"}), qos=1)
            return "🌑 Luz desactivada (OFF)"
            
        elif any(w in t for w in ["abre", "abrir", "porton", "compuerta abierta"]):
            self._client.publish(self.topic_analog, json.dumps({"angle": 180}), qos=1)
            return "🚪 Servomotor fijado en 180° (Apertura)"
            
        elif any(w in t for w in ["cierra", "cerrar", "bloquea", "compuerta cerrada"]):
            self._client.publish(self.topic_analog, json.dumps({"angle": 0}), qos=1)
            return "🔒 Servomotor fijado en 0° (Cierre)"
            
        return f"Comando no reconocido: '{transcript}'"

@st.cache_resource
def get_voice_gateway() -> VoiceCommandGateway:
    return VoiceCommandGateway()

gateway = get_voice_gateway()

st.title("🎙️ Control Vocal de Actuadores")
st.caption(f"Traducción automática de lenguaje natural a comandos para `{gateway.device_id}`")

st.markdown("""
<div style="background: linear-gradient(145deg, #0d152d 0%, #070d1e 100%); border:1px solid rgba(56,189,248,0.25); border-top:3px solid #38bdf8; border-radius:12px; padding:22px; text-align:center; margin-bottom:1.5rem;">
    <div style="font-size:1.1rem; font-weight:600; color:#ffffff;">Módulo de Entrada Acústica</div>
    <div style="font-size:0.88rem; color:#94a3b8; margin-top:4px;">
        Presione el botón e indique órdenes como: <i>"enciende la luz"</i>, <i>"apaga la luz"</i>, <i>"abre la compuerta"</i> o <i>"cierra la compuerta"</i>.
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
        <div style="font-size:0.75rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.1em; font-family:'JetBrains Mono';">Transcriptor:</div>
        <div style="font-size:1.1rem; font-weight:600; color:#ffffff; margin:4px 0 8px 0;">"{texto}"</div>
        <div style="font-size:0.75rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.1em; font-family:'JetBrains Mono';">Acción Ejecutada:</div>
        <div style="font-size:0.95rem; color:#2dd4bf; font-weight:600;">{resultado}</div>
    </div>
    """, unsafe_allow_html=True)
