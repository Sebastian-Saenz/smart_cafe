import os
import csv
from pathlib import Path
from flask import Blueprint, request, jsonify
from langchain.docstore.document import Document
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_elasticsearch import ElasticsearchStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from psycopg_pool import PoolTimeout
from config import Config
from extensions import checkpointer

client_bp = Blueprint('client', __name__)
config = Config()

def get_docs():
    docs = []
    with open(config.CSV_STOCK_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            text = (
                f"Producto: {r['name']}. "
                f"Precio: S/{r['price']}. "
                f"Descripción: {r['description']}. "
                f"Stock: {r['stock']} unidades."
            )
            docs.append(Document(page_content=text, metadata={'id': r['id']}))
    return docs

@client_bp.route('/agent', methods=['GET'])
def client_agent():
    id_agente = request.args.get('idagente')
    msg = request.args.get('msg')

    # 1. Configurar ElasticsearchStore
    store = ElasticsearchStore(
        es_url=config.ES_URL,
        es_user=config.ES_USER,
        es_password=config.ES_PASSWORD,
        index_name="stock",
        embedding=OpenAIEmbeddings()
    )

    # 3. Reindexar el CSV si este cambio
    last_mtime = getattr(store, "_last_mtime", None)
    current_mtime = os.path.getmtime(config.CSV_STOCK_PATH)

    if last_mtime != current_mtime:
        print("CSV fue actualizado...")
        if store.client.indices.exists(index="stock"):
            store.client.indices.delete(index="stock")
        store.add_documents(get_docs())
        store._last_mtime = current_mtime

    # 4. Preparar herramienta RAG
    retriever = store.as_retriever(search_kwargs={"k": 3})
    tool_rag = retriever.as_tool(
        name="stock_search",
        description="Consulta de stock"
    )
    # prueba = retriever.invoke("Algo dulce")
    # prueba = retriever.invoke("Algo caliente")
    # print([d.page_content for d in prueba])

    # 5. Inicializamos el modelo
    model = ChatOpenAI(model="gpt-4.1-2025-04-14")

    # 6. Herramientas y Prompt
    tolkit = [tool_rag]
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
            Eres el amable asistente virtual de **Esencia Cafetería** ☕🍰  
            Hablas con entusiasmo, cercanía y usando emojis. Siempre breve, claro y conversacional (máx. 20 palabras por respuesta).

            ---

            ### 🧠 Reglas generales:

            - Para el primer mensaje inicia con: **“Hola, gracias por contactar con Esencia Cafetería 😊 ¿En qué podemos ayudarte hoy?”**
            - No uses signos de apertura “¡” o “¿”.
            - Para preguntas, cierra con “?”.
            - Usa **stock_search** en cada mensaje relacionado a productos.
            - Consulta el historial para detectar pedidos anteriores o datos relevantes.  
            - Si no hay info, responde: **“Lo siento, no cuento con esa info 😕”**
            - Nunca inventes productos fuera del CSV.
            - Solo responde con: **“disponible”** o **“agotado”** (no menciones cantidades).
            - Usa este formato para respuestas de productos:  
            **“Sí, tenemos <producto> a <precio>. ¿Lo quieres para delivery o recoger en la cafetería? 😊”**

            ---

            ### 💬 Flujo conversacional:

            1. **Saludo inicial** con calidez:  
            “Hola, gracias por contactar con Esencia Cafetería 😊 ¿En qué podemos ayudarte hoy?”
            2. Si el cliente no sabe qué pedir, sugiere **2 o 3 productos populares con más stock**.
            3. Al consultar un producto, responde con:  
            - Nombre, breve descripción, precio y disponibilidad.  
            - Luego pregunta: **“¿Recoges en tienda o domicilio (S/4–7 aprox.)?”**
            4. Resume el pedido y pregunta: **“¿Deseas algo más?”** 🍩☕
            5. Si elige **delivery**, solicita dirección y confirma:  
            **“Genial 😊 El pago es por Yape al 987 654 321.”**
            6. Cierra con:  
            **“¡Gracias! Pedido en camino 🚴 Nos vemos pronto 😊”**

            ---

            ### ✨ Estilo:

            - Entusiasta y cercano.
            - Siempre con emojis.
            - Muy breve y conversacional.

        """),
        ("human", "{messages}")
    ])

    # 7. Crear y ejecutar agente
    agent_executor = create_react_agent(model, tolkit, checkpointer=checkpointer, prompt=prompt)
    config_agent = {"configurable": {"thread_id": id_agente}}
    try:
        response = agent_executor.invoke({"messages": [HumanMessage(content=msg)]}, config=config_agent)
    except PoolTimeout:
        pool.check()
        print("error")

    reply = response['messages'][-1].content
    # return response['messages'][-1].content
    return jsonify({"reply": reply})
