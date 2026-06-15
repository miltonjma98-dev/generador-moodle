import json
import logging
from typing import List, Dict, Any, Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fallback imports
try:
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig
except ImportError:
    genai = None

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    import openai
except ImportError:
    openai = None


# Definimos el esquema de respuesta compatible con Gemini en formato diccionario nativo.
# Evitamos usar Pydantic directamente para el schema de Gemini porque Pydantic v2 genera 
# campos como 'default' o 'anyOf' que no son soportados por la API de Gemini y provocan 
# el error "Unknown field for Schema: default".
GEMINI_QUIZ_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "questions": {
            "type": "ARRAY",
            "description": "Lista de preguntas generadas o extraídas del documento.",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "type": {
                        "type": "STRING",
                        "description": "Tipo de pregunta. Debe ser estrictamente 'multichoice' (opción múltiple) o 'essay' (abierta/ensayo)."
                    },
                    "name": {
                        "type": "STRING",
                        "description": "Título corto identificativo de la pregunta (ej. 'Fotosíntesis - Fase Luminosa')."
                    },
                    "questiontext": {
                        "type": "STRING",
                        "description": "El enunciado completo de la pregunta. Puede contener formato HTML básico."
                    },
                    "generalfeedback": {
                        "type": "STRING",
                        "description": "Retroalimentación general y detallada de la pregunta. Se autogenera explicando la respuesta correcta e incluyendo referencias bibliográficas reales (Libro, Autor, Año) obtenidas de fuentes académicas confiables."
                    },
                    "answers": {
                        "type": "ARRAY",
                        "description": "Lista de opciones de respuesta. Obligatorio y debe tener al menos 4 opciones únicamente si el type es 'multichoice'. Para 'essay', omitir.",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "text": {
                                    "type": "STRING",
                                    "description": "Texto de la opción de respuesta."
                                },
                                "fraction": {
                                    "type": "NUMBER",
                                    "description": "Fracción de la calificación. Debe ser 100 para la opción correcta y 0 para las incorrectas."
                                },
                                "feedback": {
                                    "type": "STRING",
                                    "description": "Retroalimentación específica de por qué esta opción es correcta o incorrecta."
                                }
                            },
                            "required": ["text", "fraction", "feedback"]
                        }
                    },
                    "graderinfo": {
                        "type": "STRING",
                        "description": "Criterios de evaluación clave e información para el calificador. Obligatorio únicamente si el type es 'essay'. Para 'multichoice', omitir."
                    }
                },
                "required": ["type", "name", "questiontext", "generalfeedback"]
            }
        }
    },
    "required": ["questions"]
}


class AIService:
    def __init__(self, provider: str, api_key: str, model_name: str):
        if not api_key:
            raise ValueError(f"Se requiere una clave API válida para {provider}.")
        
        self.provider = provider
        self.api_key = api_key
        self.model_name = model_name

        if self.provider == "Google Gemini":
            if genai is not None:
                genai.configure(api_key=self.api_key)
            else:
                logger.warning("El paquete 'google-generativeai' no está instalado.")
                
        elif self.provider == "Anthropic Claude":
            if anthropic is not None:
                self.claude_client = anthropic.Anthropic(api_key=self.api_key)
            else:
                logger.warning("El paquete 'anthropic' no está instalado.")
                
        elif self.provider in ["Groq (Llama/Gemma)", "OpenRouter (Modelos Libres)"]:
            if openai is not None:
                if self.provider == "Groq (Llama/Gemma)":
                    self.openai_client = openai.OpenAI(
                        base_url="https://api.groq.com/openai/v1",
                        api_key=self.api_key
                    )
                else:  # OpenRouter
                    self.openai_client = openai.OpenAI(
                        base_url="https://openrouter.ai/api/v1",
                        api_key=self.api_key
                    )
            else:
                logger.warning("El paquete 'openai' no está instalado.")

    def generate_quiz(
        self, 
        text_content: str, 
        question_type: str = "Ambas", 
        search_grounding: bool = True,
        generate_new_questions: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Uses the selected provider to parse text and return structured questions.
        """
        type_instruction = ""
        if question_type == "Opción Múltiple":
            type_instruction = "Genera únicamente preguntas de opción múltiple ('multichoice'). Cada una debe tener al menos 4 opciones."
        elif question_type == "Abierta (Ensayo)":
            type_instruction = "Genera únicamente preguntas abiertas de tipo ensayo ('essay')."
        else:
            type_instruction = "Genera una combinación de preguntas de opción múltiple ('multichoice') y abiertas de tipo ensayo ('essay'). Asegúrate de que las de opción múltiple tengan al menos 4 opciones."

        behavior_instruction = ""
        if generate_new_questions:
            behavior_instruction = (
                "Tu objetivo es GENERAR preguntas NUEVAS y educativas basadas en la información y conceptos clave explicados "
                "en el texto provisto. Asegúrate de cubrir todos los temas relevantes."
            )
        else:
            behavior_instruction = (
                "Tu objetivo es DETECTAR y EXTRAER las preguntas y respuestas que ya existen explícitamente en el texto provisto. "
                "Si encuentras una pregunta de opción múltiple, extrae todas sus opciones. Si una pregunta está incompleta o no tiene "
                "retroalimentación, complétala de forma coherente utilizando el contenido del texto."
            )

        prompt = f"""
        Actúa como un experto creador de exámenes y docente.
        Analiza el siguiente contenido de texto extraído de un documento escolar o académico:
        
        === CONTENIDO DEL DOCUMENTO ===
        {text_content}
        ===============================
        
        {behavior_instruction}
        
        {type_instruction}
        
        Instrucciones específicas por tipo de pregunta:
        1. Para preguntas de opción múltiple ('multichoice'):
           - Debe haber como mínimo 4 opciones (`answers`).
           - Exactamente UNA opción debe ser correcta, la cual debe tener `fraction: 100` y una retroalimentación positiva.
           - Las opciones incorrectas deben tener `fraction: 0` y retroalimentaciones explicativas de por qué no son correctas.
           - El campo `generalfeedback` debe contener una explicación completa e instructiva de la respuesta correcta.
           
        2. Para preguntas de ensayo ('essay'):
           - No debe contener la lista `answers` (dejarla nula o vacía).
           - Debe incluir el campo `graderinfo`, detallando los criterios de evaluación clave que el docente debe considerar al calificar (por ejemplo: claridad, conceptos clave que deben mencionarse, etc.).
           - El campo `generalfeedback` debe contener una respuesta de ejemplo o una guía ideal de lo que se espera que el estudiante responda.
        
        BIBLIOGRAFÍA Y RETROALIMENTACIÓN:
        Si el documento no proporciona retroalimentación detallada o referencias bibliográficas para la pregunta, debes:
        - Autogenerar una retroalimentación rica y detallada basada en el conocimiento científico o histórico real.
        - Buscar e incluir referencias bibliográficas REALES (libros, autores, años, títulos) para fundamentar la respuesta. Coloca estas referencias de forma bonita al final del campo `generalfeedback` (ej. "Referencia recomendada: Pérez, J. (2020). Biología General. Editorial Universitaria.").
        """

        if search_grounding and self.provider == "Google Gemini":
            prompt += "\nUtiliza tu herramienta de búsqueda en Google (Google Search) para encontrar referencias bibliográficas académicas reales y libros existentes que sirvan de fuente para el tema de las preguntas generadas, e incorpóralas en la retroalimentación."
        else:
            prompt += "\nUtiliza tu conocimiento interno actualizado para buscar y citar libros de texto reales e importantes de la disciplina académica como fuente para las preguntas."

        if self.provider == "Google Gemini":
            return self._call_gemini(prompt, search_grounding)
        elif self.provider == "Anthropic Claude":
            return self._call_claude(prompt)
        elif self.provider in ["Groq (Llama/Gemma)", "OpenRouter (Modelos Libres)"]:
            return self._call_openai_compatible(prompt)
        else:
            raise ValueError(f"Proveedor no soportado: {self.provider}")

    def _call_gemini(self, prompt: str, search_grounding: bool) -> List[Dict[str, Any]]:
        if genai is None:
            raise ImportError("Instala 'google-generativeai' para usar Google Gemini.")
            
        # Generar configuración con el esquema en formato dict nativo libre de campos 'default'
        config = GenerationConfig(
            response_mime_type="application/json",
            response_schema=GEMINI_QUIZ_SCHEMA,
            temperature=0.2,
        )
        
        tools = ["google_search_retrieval"] if search_grounding else None
        
        try:
            model = genai.GenerativeModel(model_name=self.model_name, tools=tools)
            response = model.generate_content(prompt, generation_config=config)
            data = json.loads(response.text)
            return data.get("questions", [])
        except Exception as e:
            logger.error(f"Error en Gemini estructurado: {e}")
            if search_grounding:
                logger.info("Reintentando sin esquema estricto por grounding...")
                fallback_prompt = prompt + "\nDevuelve el resultado estrictamente en formato JSON válido conforme al siguiente esquema:\n" + json.dumps(GEMINI_QUIZ_SCHEMA, indent=2)
                model = genai.GenerativeModel(model_name=self.model_name, tools=tools)
                response = model.generate_content(fallback_prompt, generation_config=GenerationConfig(response_mime_type="application/json"))
                data = json.loads(response.text)
                return data.get("questions", [])
            raise e

    def _call_claude(self, prompt: str) -> List[Dict[str, Any]]:
        if anthropic is None:
            raise ImportError("Instala 'anthropic' para usar Anthropic Claude.")
            
        system_instruction = f"""
        Eres un generador de cuestionarios educativos experto. 
        Debes responder EXCLUSIVAMENTE con un objeto JSON que contenga una clave 'questions' con una lista de objetos de tipo pregunta.
        El esquema JSON debe ser exactamente el siguiente:
        {json.dumps(GEMINI_QUIZ_SCHEMA, indent=2)}
        Asegúrate de no agregar texto introductorio ni conclusiones adicionales, solo devuelve el bloque JSON.
        """
        
        try:
            logger.info(f"Llamando a la API de Claude ({self.model_name})...")
            response = self.claude_client.messages.create(
                model=self.model_name,
                max_tokens=4000,
                temperature=0.2,
                system=system_instruction,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            text_content = response.content[0].text.strip()
            
            if text_content.startswith("```json"):
                text_content = text_content[7:]
            if text_content.endswith("```"):
                text_content = text_content[:-3]
            text_content = text_content.strip()
            
            data = json.loads(text_content)
            return data.get("questions", [])
        except Exception as e:
            logger.error(f"Error al llamar a Anthropic Claude: {e}")
            raise e

    def _call_openai_compatible(self, prompt: str) -> List[Dict[str, Any]]:
        if openai is None:
            raise ImportError("Instala 'openai' para usar este proveedor.")
            
        system_instruction = f"""
        Eres un generador de cuestionarios educativos experto. 
        Debes responder EXCLUSIVAMENTE con un objeto JSON que contenga una clave 'questions' con una lista de objetos de tipo pregunta.
        El esquema JSON debe ser exactamente el siguiente:
        {json.dumps(GEMINI_QUIZ_SCHEMA, indent=2)}
        Asegúrate de no agregar texto introductorio ni conclusiones adicionales, solo devuelve el bloque JSON.
        """
        
        try:
            logger.info(f"Llamando a {self.provider} ({self.model_name})...")
            
            # En Groq forzamos modo JSON
            response_format = {"type": "json_object"} if self.provider == "Groq (Llama/Gemma)" else None
            
            response = self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                response_format=response_format
            )
            
            text_content = response.choices[0].message.content.strip()
            
            if text_content.startswith("```json"):
                text_content = text_content[7:]
            if text_content.endswith("```"):
                text_content = text_content[:-3]
            text_content = text_content.strip()
            
            data = json.loads(text_content)
            return data.get("questions", [])
        except Exception as e:
            logger.error(f"Error al llamar a {self.provider}: {e}")
            raise e
