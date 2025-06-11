import utiles  # o utils, según tu archivo
from sentence_transformers import SentenceTransformer

# 1. Crear la tabla y poblarla desde el Excel (solo si aún no existe)
# utiles.excel_a_sqlite('STOCK.xlsx', db_file='STOCK.db', tabla='STOCK')

# 2. Poblar la columna de embeddings (hazlo después del paso anterior)
# utiles.poblar_embeddings('STOCK.db', 'STOCK')

# 3. Cargar los embeddings en memoria
datos, mat = utiles.cargar_embeddings('STOCK.db', 'STOCK')

# 4. Hacer la búsqueda
modelo = SentenceTransformer('all-MiniLM-L6-v2')
resultados = utiles.buscar_similares_faiss("CHAPA GALVanizada 3", datos, mat, modelo, k=20)

# 5. Mostrar los resultados
for rowid, articulo, desc, distancia in resultados:
    print(f"[distancia={distancia:.4f}] {articulo}: {desc}")
