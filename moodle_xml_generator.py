import html
from typing import List, Dict, Any

def escape_xml_text(text: str) -> str:
    """Escapes XML entities if they are outside CDATA, but generally we wrap in CDATA."""
    if not text:
        return ""
    # We do a basic escape if someone tries to inject characters that break XML structure
    return html.escape(text)

def generate_moodle_xml(questions: List[Dict[str, Any]]) -> str:
    """
    Generates a valid Moodle XML string from a list of structured questions.
    
    Supports:
    - multichoice (opción múltiple)
    - essay (abierta / ensayo)
    """
    xml_lines = []
    xml_lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    xml_lines.append('<quiz>')
    
    for question in questions:
        q_type = question.get("type", "multichoice")
        name = question.get("name", "Pregunta")
        question_text = question.get("questiontext", "")
        general_feedback = question.get("generalfeedback", "")
        
        if q_type == "multichoice":
            xml_lines.append('  <!-- Pregunta de opción múltiple -->')
            xml_lines.append('  <question type="multichoice">')
            xml_lines.append('    <name>')
            xml_lines.append(f'      <text>{escape_xml_text(name)}</text>')
            xml_lines.append('    </name>')
            xml_lines.append('    <questiontext format="html">')
            xml_lines.append(f'      <text><![CDATA[{question_text}]]></text>')
            xml_lines.append('    </questiontext>')
            xml_lines.append('    <generalfeedback format="html">')
            xml_lines.append(f'      <text><![CDATA[{general_feedback}]]></text>')
            xml_lines.append('    </generalfeedback>')
            xml_lines.append('    <defaultgrade>1.0000000</defaultgrade>')
            xml_lines.append('    <penalty>0.3333333</penalty>')
            xml_lines.append('    <hidden>0</hidden>')
            xml_lines.append('    <single>true</single>')
            xml_lines.append('    <shuffleanswers>true</shuffleanswers>')
            xml_lines.append('    <answernumbering>abc</answernumbering>')
            xml_lines.append('    <correctfeedback format="html">')
            xml_lines.append('      <text><![CDATA[¡Correcto!]]></text>')
            xml_lines.append('    </correctfeedback>')
            xml_lines.append('    <partiallycorrectfeedback format="html">')
            xml_lines.append('      <text><![CDATA[No es totalmente correcto.]]></text>')
            xml_lines.append('    </partiallycorrectfeedback>')
            xml_lines.append('    <incorrectfeedback format="html">')
            
            # Find the correct answer text to put in incorrectfeedback
            correct_ans = "la opción correcta."
            answers = question.get("answers", [])
            for ans in answers:
                if float(ans.get("fraction", 0)) == 100:
                    correct_ans = ans.get("text", "")
                    break
                    
            xml_lines.append(f'      <text><![CDATA[Incorrecto. La respuesta correcta es {correct_ans}.]]></text>')
            xml_lines.append('    </incorrectfeedback>')
            
            # Add answers
            for ans in answers:
                fraction = ans.get("fraction", 0)
                # Ensure it's formatted as integer string if 100 or 0
                fraction_str = str(int(float(fraction)))
                ans_text = ans.get("text", "")
                ans_feedback = ans.get("feedback", "")
                
                xml_lines.append(f'    <answer fraction="{fraction_str}" format="html">')
                xml_lines.append(f'      <text>{escape_xml_text(ans_text)}</text>')
                xml_lines.append('      <feedback format="html">')
                xml_lines.append(f'        <text><![CDATA[{ans_feedback}]]></text>')
                xml_lines.append('      </feedback>')
                xml_lines.append('    </answer>')
                
            xml_lines.append('  </question>')
            
        elif q_type == "essay":
            grader_info = question.get("graderinfo", "")
            
            xml_lines.append('  <!-- Pregunta abierta tipo ensayo -->')
            xml_lines.append('  <question type="essay">')
            xml_lines.append('    <name>')
            xml_lines.append(f'      <text>{escape_xml_text(name)}</text>')
            xml_lines.append('    </name>')
            xml_lines.append('    <questiontext format="html">')
            xml_lines.append(f'      <text><![CDATA[{question_text}]]></text>')
            xml_lines.append('    </questiontext>')
            xml_lines.append('    <generalfeedback format="html">')
            xml_lines.append(f'      <text><![CDATA[{general_feedback}]]></text>')
            xml_lines.append('    </generalfeedback>')
            xml_lines.append('    <defaultgrade>1.0000000</defaultgrade>')
            xml_lines.append('    <penalty>0.0000000</penalty>')
            xml_lines.append('    <hidden>0</hidden>')
            xml_lines.append('    <responseformat>editor</responseformat>')
            xml_lines.append('    <responserequired>1</responserequired>')
            xml_lines.append('    <responsefieldlines>15</responsefieldlines>')
            xml_lines.append('    <attachments>0</attachments>')
            xml_lines.append('    <attachmentsrequired>0</attachmentsrequired>')
            xml_lines.append('    <graderinfo format="html">')
            xml_lines.append(f'      <text><![CDATA[{grader_info}]]></text>')
            xml_lines.append('    </graderinfo>')
            xml_lines.append('    <responsetemplate format="html">')
            xml_lines.append('      <text><![CDATA[]]></text>')
            xml_lines.append('    </responsetemplate>')
            xml_lines.append('  </question>')
            
    xml_lines.append('</quiz>')
    return "\n".join(xml_lines)
