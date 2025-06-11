import re
import sqlite3
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from langchain_core.tools import Tool

EMBEDDINGS_MODEL = "all-MiniLM-L6-v2"

def comprobar_stock(input: str) -> str:
    nums = re.findall(r'\d+(?:[.,]\d+)?|\d+[\\/]\d+', input)
    condicion_template = r"Descripcion LIKE '%{}%'"
    condiciones = [condicion_template.format(n.replace(',', '.').replace('\\\\', '/')) for n in nums]
    where_clause = " AND ".join(condiciones) if condiciones else "1=1"

    conn = sqlite3.connect("STOCK.db")
    cur = conn.cursor()
    cur.execute("""
        SELECT Articulo, Descripcion, UPC,
               [Stock UD], [Stock KG], [Stock ML], [Stock M2],
               embedding
        FROM STOCK
        WHERE {}
    """.format(where_clause))
    rows = cur.fetchall()

    if not rows:
        cur.execute("""
            SELECT Articulo, Descripcion, UPC,
                   [Stock UD], [Stock KG], [Stock ML], [Stock M2],
                   embedding 
            FROM STOCK
        """.format(where_clause))
        conn.close()
        rows = cur.fetchall()


    emb_list, meta = [], []
    for r in rows:
        raw = r[7]
        vec = (np.fromstring(raw.strip("[]"), sep=',', dtype='float32')
               if isinstance(raw, str)
               else np.frombuffer(raw, dtype='float32'))
        emb_list.append(vec)
        meta.append(r)

    embs = np.vstack(emb_list).astype('float32')
    index = faiss.IndexFlatL2(embs.shape[1])
    index.add(embs)

    model = SentenceTransformer(EMBEDDINGS_MODEL)
    q = model.encode([input], convert_to_numpy=True).astype('float32')
    k = 40
    D, I = index.search(q, k)

    resp = ""
    for pos, (i, d) in enumerate(zip(I[0], D[0]), 1):
        r = meta[i]
        #resp += f"{pos}. (distancia: {d:.4f}) Artículo: {r[0]}, Descripción: {r[1]} , UPC: {r[2]}, Stock Unidades: {r[3]}, Stock en KG: {r[4]}, Stock en Metros Lineales: {r[5]}, Stock en m^2: {r[6]}\n"
        stocks = []
        if r[3] not in (0, 0.0, None, ''):
            stocks.append(f"Stock Unidades: {r[3]}")
        if r[4] not in (0, 0.0, None, ''):
            stocks.append(f"Stock en KG: {r[4]}")
        if r[5] not in (0, 0.0, None, ''):
            stocks.append(f"Stock en Metros Lineales: {r[5]}")
        if r[6] not in (0, 0.0, None, ''):
            stocks.append(f"Stock en m^2: {r[6]}")
        if stocks:
            resp += f"{r[1]} [{r[0]}] -> " + ", ".join(stocks) + "\n"
        else:
            resp += f"{r[1]} -> Sin stock\n"

    conn.close()
    return resp


def get_tools():
    return [Tool(
        name="comprobar_stock",
        func=comprobar_stock,
        description="Dado un articulo solicitado por el usuario se busca su disponibilidad en la base de datos {input = 'articulo consultado'} (SOLO UN ARTICULO POR CONSULTA). Devuelve los 40 productos más cercanos a la búsqueda."
    )]
