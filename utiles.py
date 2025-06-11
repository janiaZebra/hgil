import pandas as pd
import sqlite3
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
def excel_a_sqlite(excel_file='STOCK.xlsx', db_file='STOCK.db', tabla='STOCK'):
    columnas = [
        "Familia", "Articulo", "Descripcion", "Tarifa 14", "Coste Medio",
        "UPC", "Fecha UPC", "Stock UD", "Stock KG", "Stock ML", "Stock M2"
    ]
    df = pd.read_excel(excel_file, usecols=columnas)
    if 'Fecha UPC' in df.columns:
        df['Fecha UPC'] = df['Fecha UPC'].astype(str)
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute(f'DROP TABLE IF EXISTS {tabla}')
    c.execute(f'''
        CREATE TABLE {tabla} (
            Familia TEXT,
            Articulo TEXT,
            Descripcion TEXT,
            "Tarifa 14" REAL,
            "Coste Medio" REAL,
            UPC TEXT,
            "Fecha UPC" TEXT,
            "Stock UD" REAL,
            "Stock KG" REAL,
            "Stock ML" REAL,
            "Stock M2" REAL,
            embedding BLOB
        )
    ''')
    for _, row in df.iterrows():
        c.execute(f'''
            INSERT INTO {tabla} 
            (Familia, Articulo, Descripcion, "Tarifa 14", "Coste Medio", UPC, "Fecha UPC",
             "Stock UD", "Stock KG", "Stock ML", "Stock M2", embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
        ''', (
            row['Familia'], row['Articulo'], row['Descripcion'], row['Tarifa 14'], row['Coste Medio'],
            row['UPC'], row['Fecha UPC'], row['Stock UD'], row['Stock KG'], row['Stock ML'], row['Stock M2']
        ))
    conn.commit()
    conn.close()
    print(f'¡Conversión completada! Se ha creado {db_file} con la tabla {tabla}.')
    poblar_embeddings(db_file, tabla)


def poblar_embeddings(db_file='STOCK.db', tabla='STOCK'):
    modelo = SentenceTransformer('all-MiniLM-L6-v2')
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    # Selecciona todas las filas donde el embedding es NULL
    c.execute(f"SELECT rowid, Descripcion FROM {tabla} WHERE embedding IS NULL")
    filas = c.fetchall()
    if not filas:
        print("No hay descripciones nuevas para procesar.")
        conn.close()
        return
    descripciones = [desc if desc is not None else "" for _, desc in filas]
    embeddings = modelo.encode(descripciones, show_progress_bar=True).astype(np.float32)
    for (rowid, _), emb in zip(filas, embeddings):
        c.execute(f"UPDATE {tabla} SET embedding=? WHERE rowid=?", (emb.tobytes(), rowid))
    conn.commit()
    conn.close()
    print(f"Embeddings generados para {len(filas)} filas.")

def cargar_embeddings(db_file='STOCK.db', tabla='STOCK'):
    """
    Carga todos los embeddings y metadatos de la tabla.
    """
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute(f"SELECT rowid, Articulo, Descripcion, embedding FROM {tabla} WHERE embedding IS NOT NULL")
    datos = []
    vecs = []
    for rowid, articulo, desc, emb_blob in c.fetchall():
        if emb_blob is None:
            continue
        emb = np.frombuffer(emb_blob, dtype=np.float32)
        datos.append((rowid, articulo, desc))
        vecs.append(emb)
    conn.close()
    if not vecs:
        raise RuntimeError("No hay embeddings cargados en la tabla.")
    mat = np.vstack(vecs).astype('float32')
    return datos, mat

def buscar_similares_faiss(texto_query, datos, mat, modelo=None, k=5):
    """
     Devuelve (rowid, articulo, desc, distancia_faiss) para los k más similares.
     """
    if modelo is None:
        from sentence_transformers import SentenceTransformer
        modelo = SentenceTransformer('all-MiniLM-L6-v2')
    emb_query = modelo.encode([texto_query]).astype('float32')
    index = faiss.IndexFlatL2(mat.shape[1])
    index.add(mat)
    dist, idx = index.search(emb_query, k)
    resultados = []
    for i, d in zip(idx[0], dist[0]):
        rowid, articulo, desc = datos[i]
        resultados.append((rowid, articulo, desc, d))
    return resultados


# Ejemplo de uso:
if __name__ == "__main__":
    # 1. Crea la tabla desde un Excel
    # excel_a_sqlite('TU_ARCHIVO.xlsx', 'STOCK.bd', 'STOCK')
    # 2. Pobla la columna de embeddings
    # poblar_embeddings('STOCK.bd', 'STOCK')
    # 3. Busca similares (puedes repetir este paso todas las veces que quieras)
    modelo = SentenceTransformer('all-MiniLM-L6-v2')
    datos, mat = cargar_embeddings('STOCK.bd', 'STOCK')
    resultados = buscar_similares_faiss("METRO LINEAL CHAPA GALVANIZADA 1MM DES. 200", datos, mat, modelo, k=5)
    for rowid, articulo, desc, distancia in resultados:
        print(f"[distancia={distancia:.4f}] {articulo}: {desc}")
