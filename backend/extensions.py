from psycopg_pool import ConnectionPool
from config import Config
import psycopg
from langchain_openai import OpenAIEmbeddings
from langchain_elasticsearch import ElasticsearchStore
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver

# Importar configuraciones
config = Config()
# ORM
db = SQLAlchemy()
# Auth
jwt = JWTManager()
# Pool de conexiones a PostgreSQL
connection_kwargs = {
    "autocommit": True,
    "prepare_threshold": 0,
}
pool = ConnectionPool(conninfo=config.DB_URI
        ,min_size=1
        ,max_size=50
        ,timeout=30
        ,kwargs=connection_kwargs)

checkpointer = PostgresSaver(pool)

# ===== TEST: Funciones de testeo =====
def test_PostgreSQL():
    try:
        print("===> Test PostGresSQL:", end=" ")
        conn = psycopg.connect(config.DB_URI)
        conn.close()
        print("ok")
    except Exception as e:
        print("Error conectando a SQL: ", e)

def test_Elasticsearch():
    try:
        print("===> Test Elasticsearch:", end=" ")
        db_query = ElasticsearchStore(
            es_url="http://104.155.144.31:9200",
            es_user="elastic",
            es_password="oAAGB7cMU7LnILqdN1el",
            index_name="lg-proddata",
            embedding=OpenAIEmbeddings())
        print("ok")
    except Exception as e:
        print("Error conectando a Elasticsearch: ", e)

def test_Pool():
    try:
        print("===> Test Pool:", end=" ")
        with pool.connection() as conn:
            conn.execute("SELECT 1")
            print("ok")
    except Exception as e:
        print("Error conectando a Pool: ", e)