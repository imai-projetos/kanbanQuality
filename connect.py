import pandas as pd
import os
from dotenv import load_dotenv
import psycopg2

def load_data(source="excel"):
    if source == "excel":
        caminho_excel = r"C:\Users\proje\Downloads\BaseKanBan.xlsx"
        return pd.read_excel(caminho_excel)
    
    elif source == "postgres":
        load_dotenv()

        conn_info = {
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT"),
            "dbname": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD")
        }

        with psycopg2.connect(**conn_info) as conn:
            query = "SELECT * FROM vw_tempo_logistico"
            return pd.read_sql(query, conn)
    
    else:
        raise ValueError("Fonte de dados inválida")