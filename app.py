import streamlit as st
import json
import os
from document_parser import extract_text
from ai_service import AIService
from moodle_xml_generator import generate_moodle_xml

# Configuración de página
st.set_page_config(
    page_title="Moodle Quiz Generator - Multi AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS Personalizados Premium
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Degradado de fondo para el banner superior */
    .hero-banner {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
        padding: 2.5rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        position: relative;
        overflow: hidden;
    }
    
    .hero-banner::after {
        content: "";
        position: absolute;
        top: -50%;
        right: -20%;
        width: 300px;
        height: 300px;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 50%;
        filter: blur(50px);
    }
    
    .hero-title {
        font-size: 2.5rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        letter-spacing: -0.025em;
    }
    
    .hero-subtitle {
        font-size: 1.1rem;
        opacity: 0.9;
        font-weight: 400;
        max-width: 700px;
    }
    
    /* Estilos de las Tarjetas de Preguntas */
    .question-card {
        background-color: #ffffff;
        border-radius: 12px;
        border: 1px solid #e5e7eb;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .question-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04);
    }
    
    .question-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #f3f4f6;
        padding-bottom: 0.75rem;
        margin-bottom: 1rem;
    }
    
    .question-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #1f2937;
    }
    
    .badge {
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    .badge-multichoice {
        background-color: #e0f2fe;
        color: #0369a1;
    }
    
    .badge-essay {
        background-color: #fef3c7;
        color: #d97706;
    }
    
    .option-row {
        padding: 0.5rem 1rem;
        border-radius: 6px;
        margin-bottom: 0.5rem;
        font-size: 0.95rem;
        display: flex;
        align-items: center;
    }
    
    .option-correct {
        background-color: #d1fae5;
        border: 1px solid #10b981;
        color: #065f46;
    }
    
    .option-incorrect {
        background-color: #f3f4f6;
        border: 1px solid #e5e7eb;
        color: #374151;
    }
    
    .feedback-box {
        background-color: #f8fafc;
        border-left: 4px solid #6366f1;
        padding: 0.75rem 1rem;
        border-radius: 0 8px 8px 0;
        font-size: 0.9rem;
        margin-top: 0.75rem;
    }
    
    .ref-box {
        background-color: #eff6ff;
        border-left: 4px solid #3b82f6;
        padding: 0.75rem 1rem;
        border-radius: 0 8px 8px 0;
        font-size: 0.9rem;
        margin-top: 0.75rem;
    }
    
    /* Panel de información de seguridad */
    .security-notice {
        background-color: #eff6ff;
        border: 1px solid #bfdbfe;
        padding: 0.75rem;
        border-radius: 8px;
        color: #1e40af;
        font-size: 0.85rem;
        margin-bottom: 1rem;
        font-weight: 500;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# Ruta del archivo de configuración local
CONFIG_FILE = "config.json"

# Cargar configuración si existe
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

# Cargar API Keys locales
saved_config = load_config()

# Helper para cargar llave priorizando Streamlit Secrets (nube) y luego config.json (local)
def get_initial_key(key_name, local_dict):
    # Intentar obtener de Streamlit Secrets (en la nube)
    if hasattr(st, "secrets"):
        try:
            if key_name in st.secrets:
                return st.secrets[key_name]
        except Exception:
            pass
    # Si no, obtener del archivo local
    return local_dict.get(key_name, "")

# Inicialización del estado de sesión
if "questions" not in st.session_state:
    st.session_state.questions = []
if "extracted_text" not in st.session_state:
    st.session_state.extracted_text = ""
if "gemini_key" not in st.session_state:
    st.session_state.gemini_key = get_initial_key("gemini_key", saved_config)
if "claude_key" not in st.session_state:
    st.session_state.claude_key = get_initial_key("claude_key", saved_config)
if "groq_key" not in st.session_state:
    st.session_state.groq_key = get_initial_key("groq_key", saved_config)
if "openrouter_key" not in st.session_state:
    st.session_state.openrouter_key = get_initial_key("openrouter_key", saved_config)

# Cabecera / Hero Banner
st.markdown("""
<div class="hero-banner">
    <div class="hero-title">Generador de Cuestionarios para Moodle</div>
    <div class="hero-subtitle">
        Sube tus archivos PDF, Word o PowerPoint. Nuestra inteligencia artificial extraerá y generará preguntas de opción múltiple y ensayo completas con retroalimentaciones y referencias bibliográficas reales de libros académicos, listas para cargar a Moodle.
    </div>
</div>
""", unsafe_allow_html=True)

# barra lateral para configuración
with st.sidebar:
    st.markdown("### 🔒 Configuración de IA Privada")
    
    st.markdown("""
    <div class="security-notice">
        🔒 <b>Modo Privado Activo</b><br>
        Las claves de acceso API están protegidas en el servidor. No son visibles ni editables por los usuarios de este sitio.
    </div>
    """, unsafe_allow_html=True)
    
    # Selector de Proveedor
    provider = st.selectbox(
        "Proveedor de IA:",
        options=[
            "Google Gemini", 
            "Anthropic Claude", 
            "Groq (Llama/Gemma)", 
            "OpenRouter (Modelos Libres)"
        ],
        index=0,
        help="Elige el proveedor del modelo de lenguaje que deseas utilizar."
    )
    
    # Determinar si la llave está configurada internamente
    active_key = ""
    if provider == "Google Gemini":
        active_key = st.session_state.gemini_key
    elif provider == "Anthropic Claude":
        active_key = st.session_state.claude_key
    elif provider == "Groq (Llama/Gemma)":
        active_key = st.session_state.groq_key
    else:
        active_key = st.session_state.openrouter_key
        
    if active_key:
        st.success(f"🟢 {provider} conectado y listo.")
    else:
        st.warning(f"⚠️ {provider} no tiene clave configurada en el servidor.")
        
    st.divider()
    
    # Modelos dinámicos
    if provider == "Google Gemini":
        model_options = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.5-flash"]
    elif provider == "Anthropic Claude":
        model_options = ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest", "claude-3-opus-latest"]
    elif provider == "Groq (Llama/Gemma)":
        model_options = [
            "llama-3.1-70b-versatile", 
            "llama-3.1-8b-instant", 
            "gemma2-9b-it", 
            "llama3-70b-8192", 
            "llama3-8b-8192"
        ]
    else:  # OpenRouter (Usa modelos libres y estables actualmente activos)
        model_options = [
            "meta-llama/llama-3-8b-instruct:free", 
            "google/gemma-2-9b-it:free", 
            "qwen/qwen-2.5-72b-instruct:free",
            "mistralai/mistral-7b-instruct:free"
        ]
        
    # Selección de modelo
    model_name = st.selectbox(
        "Modelo de IA:",
        options=model_options,
        index=0,
        help="Elige el modelo específico que procesará tu documento."
    )
    
    st.divider()
    
    # Configuración de extracción/generación
    st.markdown("#### 🎯 Estrategia")
    mode = st.radio(
        "Modo de operación:",
        options=["Extraer preguntas del documento", "Generar preguntas del tema"],
        index=0,
        help="Extraer: Busca preguntas escritas explícitamente en el documento.\nGenerar: Crea preguntas académicas nuevas sobre el tema del texto."
    )
    
    # Habilitar referencias de libros (búsqueda en internet)
    search_grounding = st.checkbox(
        "Habilitar búsqueda bibliográfica",
        value=False,
        help="Solo disponible para Google Gemini. Busca fuentes reales en internet. Desactívala si te arroja errores de límite de API."
    )
    
    st.divider()
    st.markdown("💡 *El formato de exportación XML es totalmente compatible con el importador de Moodle.*")

# Layout principal
col1, col2 = st.columns([1, 2], gap="large")

with col1:
    st.markdown("### 📥 1. Cargar Documento")
    uploaded_file = st.file_uploader(
        "Elige un archivo PDF, Word (.docx) o PowerPoint (.pptx)",
        type=["pdf", "docx", "pptx", "ppt"]
    )
    
    question_type = st.selectbox(
        "Tipo de preguntas a procesar:",
        options=["Ambas", "Opción Múltiple", "Abierta (Ensayo)"]
    )
    
    # Botón de procesar
    process_btn = st.button("🚀 Procesar Documento", use_container_width=True)
    
    if process_btn:
        if not active_key:
            st.error(f"⚠️ El proveedor '{provider}' no está configurado. El administrador de la web debe ingresar las claves API en Streamlit Secrets o config.json.")
        elif not uploaded_file:
            st.error("⚠️ Por favor, sube un documento primero.")
        else:
            file_bytes = uploaded_file.read()
            file_name = uploaded_file.name
            
            with st.spinner("Leyendo y extrayendo texto del documento..."):
                try:
                    # Extraer texto (sirve de fallback y para Word/PPTX)
                    extracted_text = extract_text(file_bytes, file_name)
                    st.session_state.extracted_text = extracted_text
                    
                    st.success("✅ Documento leído correctamente. Iniciando análisis de IA...")
                except Exception as e:
                    st.error(f"Error al leer el archivo: {str(e)}")
                    extracted_text = None
            
            if extracted_text is not None:
                with st.spinner(f"La IA ({provider}) está analizando las preguntas..."):
                    try:
                        service = AIService(provider=provider, api_key=active_key, model_name=model_name)
                        
                        # Generar/extraer preguntas pasando el archivo original (para lectura directa de PDF)
                        generate_new = (mode == "Generar preguntas del tema")
                        questions = service.generate_quiz(
                            text_content=extracted_text[:40000],
                            file_bytes=file_bytes,
                            file_name=file_name,
                            question_type=question_type,
                            search_grounding=search_grounding,
                            generate_new_questions=generate_new
                        )
                        
                        st.session_state.questions = questions
                        st.success(f"🎉 ¡Éxito! Se detectaron/generaron {len(questions)} preguntas.")
                        
                    except Exception as e:
                        st.error(f"Error al procesar con la IA: {str(e)}")
                        
    # Botones de limpieza
    if st.session_state.questions:
        st.divider()
        if st.button("🗑️ Limpiar Preguntas", use_container_width=True):
            st.session_state.questions = []
            st.session_state.extracted_text = ""
            st.rerun()

with col2:
    st.markdown("### 📝 2. Vista Previa y Edición")
    
    if not st.session_state.questions:
        st.info("ℹ️ Sube un documento y haz clic en 'Procesar Documento' para ver las preguntas aquí.")
    else:
        st.markdown(f"Se cargaron **{len(st.session_state.questions)}** preguntas. Puedes editarlas o eliminarlas antes de exportar.")
        
        # Iterar e interactuar con cada pregunta
        updated_questions = []
        for i, q in enumerate(st.session_state.questions):
            q_type = q.get("type", "multichoice")
            q_name = q.get("name", f"Pregunta {i+1}")
            q_text = q.get("questiontext", "")
            q_feedback = q.get("generalfeedback", "")
            
            # HTML Card render for visual reference
            badge_class = "badge-multichoice" if q_type == "multichoice" else "badge-essay"
            badge_text = "Opción Múltiple" if q_type == "multichoice" else "Ensayo / Abierta"
            
            # Form container to update state
            with st.container():
                st.markdown(f"""
                <div class="question-card">
                    <div class="question-header">
                        <span class="question-title"># {i+1} - {q_name}</span>
                        <span class="badge {badge_class}">{badge_text}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Edit details inside expander
                with st.expander(f"✏️ Editar / Ver Detalles de la Pregunta {i+1}", expanded=(i==0)):
                    col_name, col_type = st.columns([2, 1])
                    edit_name = col_name.text_input(f"Nombre de la Pregunta:", value=q_name, key=f"name_{i}")
                    edit_type = col_type.selectbox(
                        f"Tipo de Pregunta:", 
                        options=["multichoice", "essay"], 
                        index=0 if q_type == "multichoice" else 1,
                        key=f"type_{i}"
                    )
                    
                    edit_text = st.text_area(f"Enunciado (HTML soportado):", value=q_text, key=f"text_{i}", height=100)
                    edit_feedback = st.text_area(f"Retroalimentación general y bibliografía:", value=q_feedback, key=f"feed_{i}", height=120)
                    
                    edit_answers = []
                    edit_grader_info = ""
                    
                    if edit_type == "multichoice":
                        st.markdown("**Opciones de Respuesta (Mínimo 4):**")
                        answers_list = q.get("answers", [])
                        
                        # Ensure we have at least 4 answer fields
                        while len(answers_list) < 4:
                            answers_list.append({"text": "", "fraction": 0, "feedback": ""})
                            
                        for j, ans in enumerate(answers_list):
                            ans_text = ans.get("text", "")
                            ans_fraction = float(ans.get("fraction", 0))
                            ans_feedback = ans.get("feedback", "")
                            
                            c_fraction, c_text, c_feed = st.columns([1, 3, 3])
                            
                            # Fraction select (Correct=100, Incorrect=0)
                            is_correct = c_fraction.checkbox(
                                "Correcta", 
                                value=(ans_fraction == 100), 
                                key=f"ans_frac_{i}_{j}",
                                help="Marca esta casilla si es la respuesta correcta."
                            )
                            fraction_val = 100.0 if is_correct else 0.0
                            
                            text_val = c_text.text_input(f"Opción {chr(97+j)}:", value=ans_text, key=f"ans_text_{i}_{j}")
                            feed_val = c_feed.text_input(f"Retroalimentación {chr(97+j)}:", value=ans_feedback, key=f"ans_feed_{i}_{j}")
                            
                            edit_answers.append({
                                "text": text_val,
                                "fraction": fraction_val,
                                "feedback": feed_val
                            })
                    else:
                        edit_grader_info = st.text_area(
                            f"Información para calificar (Criterios de evaluación):", 
                            value=q.get("graderinfo", ""), 
                            key=f"grader_{i}",
                            height=100
                        )
                    
                    # Delete question button
                    delete_q = st.checkbox(f"🗑️ Eliminar esta pregunta de la exportación", key=f"del_{i}")
                    
                    # Store edited values back
                    if not delete_q:
                        updated_q = {
                            "type": edit_type,
                            "name": edit_name,
                            "questiontext": edit_text,
                            "generalfeedback": edit_feedback
                        }
                        if edit_type == "multichoice":
                            updated_q["answers"] = edit_answers
                        else:
                            updated_q["graderinfo"] = edit_grader_info
                            
                        updated_questions.append(updated_q)
                        
        # Save updates to session state
        st.session_state.questions = updated_questions
        
        # Export and Download Area
        st.divider()
        st.markdown("### 📥 3. Exportar Archivo Moodle XML")
        
        try:
            moodle_xml_data = generate_moodle_xml(st.session_state.questions)
            
            # File name suggest
            doc_name = os.path.splitext(uploaded_file.name)[0] if uploaded_file else "cuestionario"
            xml_filename = f"{doc_name}_moodle.xml"
            
            st.download_button(
                label="📥 Descargar XML para Moodle",
                data=moodle_xml_data,
                file_name=xml_filename,
                mime="text/xml",
                use_container_width=True
            )
            
            st.markdown(f"""
            > **¿Cómo importarlo en Moodle?**
            > 1. Ve a tu curso en Moodle y entra al **Banco de preguntas**.
            > 2. Haz clic en la pestaña **Importar**.
            > 3. Selecciona el formato **Formato XML de Moodle**.
            > 4. Sube el archivo `{xml_filename}` descargado y presiona **Importar**.
            """)
            
        except Exception as e:
            st.error(f"Error al generar el archivo XML: {str(e)}")
