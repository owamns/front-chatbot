from flask import Flask, render_template, request, jsonify
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain_community.vectorstores.supabase import SupabaseVectorStore
from supabase import create_client
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
TABLE_NAME = 'documents'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
embed_model = FastEmbedEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


def obtener_vectorstore():
    return SupabaseVectorStore(
        client=supabase,
        embedding=embed_model,
        table_name=TABLE_NAME,
        query_name="match_documents"
    )


llm = OllamaLLM(model="qwen2.5:7b")
vectorstore = obtener_vectorstore()
retriever = vectorstore.as_retriever(search_kwargs={'k': 4})

custom_prompt_template = """Usa la siguiente información para responder a la pregunta del usuario.
Si no sabes la respuesta, simplemente di que no lo sabes, no intentes inventar una respuesta.
Contexto: {context}
Pregunta: {question}
Solo devuelve la respuesta útil a continuación y nada más y responde siempre en español
Respuesta útil:
"""

prompt = PromptTemplate(template=custom_prompt_template, input_variables=['context', 'question'])

qa = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever,
    return_source_documents=True,
    chain_type_kwargs={"prompt": prompt}
)


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