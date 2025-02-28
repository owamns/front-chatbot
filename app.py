from flask import Flask, render_template, request, jsonify
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain_community.vectorstores.supabase import SupabaseVectorStore
from supabase import create_client
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from dotenv import load_dotenv
import re

load_dotenv()

app = Flask(__name__)

SUPABASE_URL = "https://piqwjwtcxamqtmeilwkc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBpcXdqd3RjeGFtcXRtZWlsd2tjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczOTgwNzk0OCwiZXhwIjoyMDU1MzgzOTQ4fQ.8JFcR2PPHG5bmR_ASAvaQlO-5OvWI5k3BHLPV07eV2E"
TABLE_NAME = 'documents'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
embed_model = FastEmbedEmbeddings(model_name="BAAI/bge-large-en-v1.5")


vector_store = SupabaseVectorStore(
    client=supabase,
    embedding=embed_model,
    query_name="match_documents_2",
    table_name="osinergmin_2"
)

llm = OllamaLLM(model="qwen2.5:7b")

custom_prompt_template = """Usa exclusivamente la siguiente información sobre normas y resoluciones de OSINERGMIN para responder la pregunta del usuario.
Si no sabes la respuesta, simplemente di que no lo sabes. No inventes información ni intentes completar con supuestos.

### Contexto relevante:
{context}

### Pregunta del usuario:
{question}

**Reglas para responder:**
1 **Responde solo con información de la resolución específica mencionada por el usuario. Si la pregunta es ambigua o no menciona una resolución específica, solicita aclaración.
2 **No incluyas información de otras resoluciones.**
3 **Si la respuesta no está en el contexto proporcionado, responde: "No tengo información suficiente para responder tu pregunta."**
4 **No agregues explicaciones adicionales fuera del contenido proporcionado.**

✍ **Tu respuesta útil:**
"""

prompt = PromptTemplate(template=custom_prompt_template, input_variables=['context', 'question'])

def extract_title(query: str) -> str:
    match = re.search(r"\d{1,4}-\d{4}", query, re.IGNORECASE)
    return match.group() if match else ""


def getQA(question):

    query_text = extract_title(question)
    retriever = vector_store.as_retriever(
        search_kwargs={
            "k": 4,
            "filter": {"title": query_text}
        }
    )

    qa = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt}
    )
    return qa


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get('message')

    if not user_message:
        return jsonify({'error': 'No se recibió mensaje'}), 400

    try:
        qa = getQA(user_message)
        respuesta = qa.invoke({"query": user_message})
        metadata = [
            {
                "pagina": doc.metadata.get('page', 'N/A'),
                "archivo": doc.metadata.get('source', 'N/A'),
            }
            for doc in respuesta['source_documents']
        ]

        return jsonify({
            'respuesta': respuesta['result'],
            'fuentes': metadata
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)