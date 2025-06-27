import os
import sys
import pandas as pd
import sqlite3
import numpy as np
from sentence_transformers import SentenceTransformer

def excel_a_sqlite(excel_file='STOCK.xlsx', db_file='STOCK.db', tabla='STOCK'):
    columnas = [
        "Familia", "Articulo", "Descripcion", "Tarifa 14", "Coste Medio",
        "UPC", "Fecha UPC", "Stock UD", "Stock KG", "Stock ML", "Stock M2"
    ]
    try:
        df = pd.read_excel(excel_file, usecols=columnas)
    except Exception as e:
        print(f"ERROR: No se pudo leer el Excel '{excel_file}': {e}")
        sys.exit(1)
    if 'Fecha UPC' in df.columns:
        df['Fecha UPC'] = df['Fecha UPC'].astype(str)
    try:
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
        print(f'Conversión completada: {db_file} con la tabla {tabla}.')
    except Exception as e:
        print(f"ERROR al crear la base de datos: {e}")
        sys.exit(1)

def poblar_embeddings(db_file='STOCK.db', tabla='STOCK', model='all-MiniLM-L6-v2'):
    try:
        modelo = SentenceTransformer(model)
    except Exception as e:
        print(f"ERROR: No se pudo cargar el modelo de embeddings '{model}': {e}")
        sys.exit(2)
    try:
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
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
    except Exception as e:
        print(f"ERROR al poblar embeddings: {e}")
        sys.exit(3)

if __name__ == "__main__":
    excel_file = os.getenv("EXCEL_STOCK_FILE", "STOCK.xlsx")
    db_file = os.getenv("DB_STOCK_FILE", "STOCK.db")
    tabla = os.getenv("TABLA_STOCK", "STOCK")
    modelo = os.getenv("EMBEDDINGS_MODEL", "all-MiniLM-L6-v2")
    print(f"Excel: {excel_file}")
    print(f"DB: {db_file}")
    print(f"Tabla: {tabla}")
    print(f"Modelo de embeddings: {modelo}")

    excel_a_sqlite(excel_file, db_file, tabla)
    poblar_embeddings(db_file, tabla, modelo)
    print("Base de datos lista y embeddings calculados.")
