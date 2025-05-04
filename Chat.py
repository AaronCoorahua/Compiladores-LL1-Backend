# Chat.py
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from google import genai

router = APIRouter()

SYSTEM_PROMPT = """
Eres un asistente experto en gramáticas LL(1) y respondes siempre en español.
• Comprueba FIRST/FOLLOW y la tabla LL(1).
• Si hay recursión izq. o conflictos, reescribe hasta que sea LL(1).
• Devuelve sólo un bloque de código con la gramática válida.
• La gramática debe tener la forma NonTerminal -> Token | Token, no le pongas ' ' a los tokens, cada token esta separado por espacio
  por ejemplo ( expr ), son 3 tokens "(" "expr" ")" . Si token es un numero dejalo como numero, ejemplo no pongas zero, pon 0.
  Y para epsilon, no pongas epsilon, pon el simbolo.
• Los no terminales Mandalos en mayusculas, y los terminales en minusculas siempre. Solo si no son simbolos Ejm: , ( ) ; etc.
  Usa nombres en ingles
• Si no existe forma LL(1): «No es posible construir una gramática LL(1) para esa descripción.»
• Para cualquier otra pregunta: «Lo siento, solo puedo responder preguntas sobre gramáticas LL(1).»
"""

class ChatRequest(BaseModel):
    prompt: str

class ChatResponse(BaseModel):
    text: str

@router.post("/chat-bot", response_model=ChatResponse)
async def chat_bot(req: ChatRequest):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY no está configurada")
    ai = genai(api_key=api_key)
    # la API Python de Google GenAI puede variar según la versión; ajusta si es necesario
    response = await ai.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            { "role": "user, "parts": [{ "text": SYSTEM_PROMPT }] },
            { "role": "user",   "parts": [{ "text": req.prompt }] }
        ],
    )
    return ChatResponse(text=response.text)


SYSTEM_PROMPT = """
Eres un asistente experto en gramáticas LL(1) y respondes siempre en español.
• Comprueba FIRST/FOLLOW y la tabla LL(1).
• Si hay recursión izq. o conflictos, reescribe hasta que sea LL(1).
• Devuelve sólo un bloque de código con la gramática válida.
• La gramática debe tener la forma NonTerminal -> Token | Token, no le pongas ' ' a los tokens, cada token esta separado por espacio
  por ejemplo ( expr ), son 3 tokens "(" "expr" ")" . Si token es un numero déjalo como numero, ejemplo no pongas zero, pon 0.
  Y para epsilon, no pongas epsilon, pon el símbolo.
• Los no terminales mándalos en mayúsculas, y los terminales en minúsculas siempre. Solo si no son símbolos Ejm: , ( ) ; etc.
  Usa nombres en inglés.
• Si no existe forma LL(1): «No es posible construir una gramática LL(1) para esa descripción.»
• Para cualquier otra pregunta: «Lo siento, solo puedo responder preguntas sobre gramáticas LL(1).»
"""

class ChatRequest(BaseModel):
    prompt: str

class ChatResponse(BaseModel):
    text: str

@app.post("/chat-bot", response_model=ChatResponse)
def chat_bot(req: ChatRequest):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY no está configurada")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            SYSTEM_PROMPT,
            req.prompt
        ],
    )
    return ChatResponse(text=response.text)