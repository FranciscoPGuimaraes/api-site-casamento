from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
import json
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Pessoa(BaseModel):
    name: str
    confirmed: bool

class Convidado(BaseModel):
    code: str
    host: Pessoa
    conjuge: Optional[Pessoa] = None
    dependentes: Optional[List[Pessoa]] = []

def get_connection():
    return psycopg2.connect(
        user=os.getenv("user"),
        password=os.getenv("password"),
        host=os.getenv("host"),
        port=os.getenv("port"),
        dbname=os.getenv("dbname")
    )

@app.get("/")
def root():
    return {"message": "API do casamento funcionando com Supabase!"}

@app.post("/convidados")
def adicionar_convidado(convidado: Convidado):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT 1 FROM convidados WHERE code = %s", (convidado.code,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Código já existente")

        cur.execute("""
            INSERT INTO convidados (code, host_name, host_confirmed, conjuge_name, conjuge_confirmed, dependentes)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            convidado.code,
            convidado.host.name,
            convidado.host.confirmed,
            convidado.conjuge.name if convidado.conjuge else None,
            convidado.conjuge.confirmed if convidado.conjuge else None,
            json.dumps([dep.dict() for dep in convidado.dependentes])
        ))

        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Convidado adicionado com sucesso"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/convidados")
def listar_convidados():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM convidados")
        rows = cur.fetchall()
        convidados = []

        for row in rows:
            convidados.append(Convidado(
                code=row[0],
                host=Pessoa(name=row[1], confirmed=row[2]),
                conjuge=Pessoa(name=row[3], confirmed=row[4]) if row[3] else None,
                dependentes=[Pessoa(**d) for d in row[5]] if row[5] else []
            ))

        cur.close()
        conn.close()
        return convidados
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/convidados/{code}")
def buscar_convidado(code: str):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM convidados WHERE code = %s", (code,))
        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Convidado não encontrado")

        convidado = Convidado(
            code=row[0],
            host=Pessoa(name=row[1], confirmed=row[2]),
            conjuge=Pessoa(name=row[3], confirmed=row[4]) if row[3] else None,
            dependentes=[Pessoa(**d) for d in row[5]] if row[5] else []
        )

        cur.close()
        conn.close()
        return convidado
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.put("/convidados/{code}")
def confirmar_presenca(code: str, convidado: Convidado):
    if code != convidado.code:
        raise HTTPException(status_code=400, detail="Código inconsistente")
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE convidados
            SET host_name = %s, host_confirmed = %s,
                conjuge_name = %s, conjuge_confirmed = %s,
                dependentes = %s
            WHERE code = %s
        """, (
            convidado.host.name,
            convidado.host.confirmed,
            convidado.conjuge.name if convidado.conjuge else None,
            convidado.conjuge.confirmed if convidado.conjuge else None,
            json.dumps([dep.dict() for dep in convidado.dependentes]),
            code
        ))

        conn.commit()
        cur.close()
        conn.close()
        return {"message": f"Confirmação atualizada para '{code}'"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
