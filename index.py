import os
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from LL_parser import Grammar, Rule
from google import genai

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ll-1-checker-web-app.vercel.app", 
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=True,
)

class RuleIn(BaseModel):
    lhs: str
    rhs: List[str]

class GrammarInput(BaseModel):
    grammar: List[RuleIn]
    start_symbol: str

class TraceInput(GrammarInput):
    input_string: str
    max_steps: int = 100

def build_grammar_from_input(data: GrammarInput) -> Grammar:
    """
    Crea una instancia Grammar, le inyecta las reglas desde el modelo Pydantic,
    y retorna el objeto listo para compute_first/follow y tabla.
    """
    # Reconstruimos el string con saltos de línea:
    lines = []
    for r in data.grammar:
        rhs = " | ".join(r.rhs).replace("ε", "_")
        lines.append(f"{r.lhs} -> {rhs}")
    # Aseguramos que la primera línea defina start_symbol:
    content = "\n".join(lines)
    g = Grammar()
    g.load_from_string(content)
    g.compute_first()
    g.compute_follow()
    g.build_ll1_table()
    return g

@app.get("/")
def hello_wordl():
    return {
        "Message" : "Hola mundo"
    }

@app.post("/grammar/load")
def first_follow(data: GrammarInput):
    g = build_grammar_from_input(data)

    raw_first  = g.get_first()   
    raw_follow = g.get_follow()

    # Sustituir "_" por "ε"
    first_sets = {
        nt: [sym if sym != "_" else "ε" for sym in syms]
        for nt, syms in raw_first.items()
    }
    follow_sets = {
        nt: [sym if sym != "_" else "ε" for sym in syms]
        for nt, syms in raw_follow.items()
    }

    terminals     = g.get_terminals()
    non_terminals = g.get_non_terminals()

    for nt in non_terminals:
        if nt not in first_sets:
            first_sets[nt] = []
        if nt not in follow_sets:
            follow_sets[nt] = []

    is_ll1, conflicts = g.is_ll1()
    output_conflicts = []
    # FIRST/FIRST
    for prod, syms in conflicts['first_conflicts'].items():
        m = re.match(r"(.+?) \| (.+)", prod)
        if m:
            p1, p2 = m.group(1).strip(), m.group(2).strip()
            nt = p1.split("→")[0].strip()
            output_conflicts.append({
                "non_terminal": nt,
                "type": "FIRST/FIRST conflict",
                "productions": [p1, p2],
                "intersection": sorted(list(syms)),
                "suggestion": f"Factoriza las producciones de {nt} que comienzan con símbolos comunes."
            })

    # FIRST/FOLLOW
    for nt, data_ in conflicts['follow_conflicts'].items():
        output_conflicts.append({
            "non_terminal": nt,
            "type": "FIRST/FOLLOW conflict",
            "first":        sorted(list(data_['first'])),
            "follow":       sorted(list(data_['follow'])),
            "intersection": sorted(list(data_['intersection'])),
            "suggestion":   f"Revisa si ε debe estar en FIRST({nt}) o si {nt} debe eliminar la producción ε."
        })

    raw = g.table
    parse_table = {}
    for nt, row in raw.items():
        parse_table[nt] = {}
        for t, entries in row.items():
            if not entries:
                parse_table[nt][t] = ""
            else:
                parts = []
                for e in entries:
                    if isinstance(e, Rule):
                        parts.append(repr(e).replace("_","ε"))
                    else:
                        parts.append(str(e))
                parse_table[nt][t] = " | ".join(parts)

    return {
        "is_LL1":       is_ll1,
        "terminals":     terminals,
        "non_terminals": non_terminals,
        "first_sets":    first_sets,
        "follow_sets":   follow_sets,
        "conflicts":     output_conflicts,
        "parse_table":   parse_table,
    }

@app.post("/grammar/run-input")
async def trace_tree(data: TraceInput):
    g = build_grammar_from_input(data)

    result = g.parse_2(
        input_string=data.input_string,
        max_steps   =data.max_steps
    )
    for step in result["trace"]:
        step["rule"] = step["rule"].replace("_", "ε")
    return result


# —————— ENDPOINT CHATBOT (Gemini GenAI) ——————

SYSTEM_PROMPT = """
Eres un asistente experto en gramáticas LL(1) y respondes siempre en español.
• Si te preguntan una gramatica LL1 y no dice cual, dile que especifique sobre que la gramática
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

@app.post("/grammar/chatbot", response_model=ChatResponse)
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