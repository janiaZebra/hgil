import os
import sqlite3
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from langchain_core.tools import Tool

EMBEDDINGS_MODEL = os.getenv("EMBEDDINGS_MODEL", "all-MiniLM-L6-v2")

def consultar_productos(queries: list[str]) -> str:
    conn = sqlite3.connect("STOCK.db")
    cur = conn.cursor()

    cur.execute("SELECT Articulo, Descripcion, embedding FROM STOCK")
    rows = cur.fetchall()

    emb_list, meta = [], []
    for r in rows:
        raw = r[2]
        vec = (np.fromstring(raw.strip("[]"), sep=',', dtype='float32')
               if isinstance(raw, str)
               else np.frombuffer(raw, dtype='float32'))
        emb_list.append(vec)
        meta.append(r)

    embs = np.vstack(emb_list).astype('float32')
    index = faiss.IndexFlatL2(embs.shape[1])
    index.add(embs)

    model = SentenceTransformer(EMBEDDINGS_MODEL)

    query_embs = model.encode(queries, convert_to_numpy=True).astype('float32')
    k = 30

    D, indices = index.search(query_embs, k)

    combined_results = {}
    for distances, idxs in zip(D, indices):
        for dist, idx in zip(distances, idxs):
            if idx not in combined_results or dist < combined_results[idx]:
                combined_results[idx] = dist

    top_45_indices = sorted(combined_results, key=combined_results.get)[:45]

    resp = []
    for idx in top_45_indices:
        r = meta[idx]
        resp.append(f"{r[1]} [{r[0]}]")

    return '\n'.join(resp)

def consultar_productos_wrapper(input, **kwargs):
    if isinstance(input, str):
        import json
        try:
            queries = json.loads(input)
            if not isinstance(queries, list):
                queries = [input]
        except Exception:
            queries = [input]
    else:
        queries = input
    return consultar_productos(queries)


def get_tools():
    return [Tool(
        name="consultar_productos",
        func=consultar_productos_wrapper,
        description="""Realiza búsqueda semántica en la base de datos.
Recibe una lista con hasta 3 cadenas diferentes.
Ejemplo de entrada válida: ["Cable cobre", "chapa Corrugada", "Chapa"]
Utilizar entradas diferentes para obtener resultados variados.
Devuelve los 45 productos semánticamente más cercanos combinados."""
    )]