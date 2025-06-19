import os
import re
import sqlite3
import faiss
import numpy as np
from langchain_core.tools import Tool
from sentence_transformers import SentenceTransformer
from jania import env

EMBEDDINGS_MODEL = env("EMBEDDINGS_MODEL", "all-MiniLM-L6-v2")
STOCK_SEARCH_MODE = str(env("STOCK_SEARCH_MODE", "true")).lower() == "true"

def comprobar_stock_real(input: str, session_id: str = "desconocido") -> str:
    conn, cur = None, None
    try:
        conn = sqlite3.connect("STOCK.db")
        cur = conn.cursor()
        if STOCK_SEARCH_MODE:
            nums = re.findall(r'\d+(?:[.,]\d+)?|\d+[\\/]\d+', input)
            condiciones = [f"Descripcion LIKE '%{n.replace(',', '.').replace('\\\\', '/')}%'" for n in nums]
            where_clause = " AND ".join(condiciones) if condiciones else "1=1"
        else:
            where_clause = "1=1"

        try:
            cur.execute(f"""
                SELECT Articulo, Descripcion, UPC,
                       [Stock UD], [Stock KG], [Stock ML], [Stock M2],
                       embedding
                FROM STOCK
                WHERE {where_clause}
            """)
            rows = cur.fetchall()
        except Exception as e:
            return f"Error ejecutando la consulta principal: {e}"

        if not rows:
            try:
                cur.execute("""
                    SELECT Articulo, Descripcion, UPC,
                           [Stock UD], [Stock KG], [Stock ML], [Stock M2],
                           embedding 
                    FROM STOCK
                """)
                rows = cur.fetchall()
            except Exception as e:
                return f"Error ejecutando la consulta alternativa: {e}"

        if not rows:
            return "No hay datos en la base de STOCK."

        emb_list, meta = [], []
        for idx, r in enumerate(rows):
            raw = r[7]
            try:
                if isinstance(raw, str):
                    vec = np.fromstring(raw.strip("[]"), sep=',', dtype='float32')
                else:
                    vec = np.frombuffer(raw, dtype='float32')
                if vec.size == 0:
                    continue
                emb_list.append(vec)
                meta.append(r)
            except Exception:
                continue

        if not emb_list:
            return "No se encontraron embeddings válidos en la base."

        try:
            embs = np.vstack(emb_list).astype('float32')
        except Exception as e:
            return f"Error al apilar embeddings: {e}"

        try:
            index = faiss.IndexFlatL2(embs.shape[1])
            index.add(embs)
        except Exception as e:
            return f"Error al inicializar o poblar el índice FAISS: {e}"

        try:
            model = SentenceTransformer(EMBEDDINGS_MODEL)
            q = model.encode([input], convert_to_numpy=True).astype('float32')
        except Exception as e:
            return f"Error cargando el modelo de embeddings: {e}"

        k = min(40, len(emb_list))
        try:
            D, I = index.search(q, k)
        except Exception as e:
            return f"Error en la búsqueda FAISS: {e}"

        resp = ""
        for pos, (i, d) in enumerate(zip(I[0], D[0]), 1):
            try:
                r = meta[i]
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
            except Exception as e:
                resp += f"Error al procesar resultado #{pos}: {e}\n"
        return resp if resp else "No se encontraron resultados relevantes."
    except Exception as e:
        return f"Error general: {e}"
    finally:
        try:
            if cur:
                cur.close()
            if conn:
                conn.close()
        except:
            pass

def comprobar_stock_wrapper(*args, **kwargs):
    if args:
        input_value = args[0]
    elif 'input' in kwargs:
        input_value = kwargs['input']
    else:
        input_value = ''

    session_id = kwargs.get("session_id", "desconocido")
    return comprobar_stock_real(input_value, session_id=session_id)

def get_tools():
    return [Tool(
        name="comprobar_stock",
        func=comprobar_stock_wrapper,
        description="Dado un artículo solicitado por el usuario se busca su disponibilidad en la base de datos {input = 'articulo consultado'} (SOLO UN ARTÍCULO POR CONSULTA). Devuelve los 40 productos más cercanos a la búsqueda."
    )]
