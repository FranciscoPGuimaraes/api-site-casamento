import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path

app = FastAPI()

# Caminho do arquivo de persistência
DB_PATH = Path("convidados.json")

class Pessoa(BaseModel):
    name: str
    confirmed: bool

class Convidado(BaseModel):
    code: str
    host: Pessoa
    conjuge: Optional[Pessoa] = None
    dependentes: Optional[List[Pessoa]] = []

# Banco de dados em memória
convidados_db: dict[str, Convidado] = {}

# === Funções de persistência ===

def save_db():
    with DB_PATH.open("w", encoding="utf-8") as f:
        json.dump(
            {code: convidado.dict() for code, convidado in convidados_db.items()},
            f,
            ensure_ascii=False,
            indent=2
        )

def load_db():
    global convidados_db
    if DB_PATH.exists():
        with DB_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
            convidados_db = {code: Convidado(**convidado) for code, convidado in data.items()}

# Carrega os dados ao iniciar
load_db()

# === Rotas ===

@app.post("/convidados")
def adicionar_convidado(convidado: Convidado):
    if convidado.code in convidados_db:
        raise HTTPException(status_code=400, detail="Código já existente")
    convidados_db[convidado.code] = convidado
    save_db()
    return {"message": "Convidado adicionado com sucesso"}

@app.get("/convidados")
def listar_convidados():
    return list(convidados_db.values())

@app.get("/convidados/{code}")
def buscar_convidado(code: str):
    convidado = convidados_db.get(code)
    if not convidado:
        raise HTTPException(status_code=404, detail="Convidado não encontrado")
    return convidado

@app.put("/convidados/{code}")
def confirmar_presenca(code: str, convidado: Convidado):
    if code != convidado.code:
        raise HTTPException(status_code=400, detail="Código inconsistente")
    convidados_db[code] = convidado
    save_db()
    return {"message": f"Confirmação atualizada para '{code}'"}
