import os
import logging
import duckdb
from dotenv import load_dotenv
load_dotenv()
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
DB_NAME=os.getenv("DB_NAME")

def connect_db():
    if not DB_NAME:
        raise ValueError("Missing DuckDB name.")
    try:
        conn=duckdb.connect(DB_NAME)
        conn.table("test").show()
        logging.info("Successfully connected to duckdb")
        return conn
    except Exception as e:
        logging.error(f"error connecting to the database: {str(e)}")
        raise

if __name__=="__main__":
    connect_db()