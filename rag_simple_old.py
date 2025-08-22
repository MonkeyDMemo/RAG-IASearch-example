"""
Sistema RAG Simple para procesar UN archivo PDF con Azure AI Search
"""

import os
import PyPDF2
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
)
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
import hashlib
from typing import List, Dict

# Cargar variables de entorno
load_dotenv()

class SimpleRAG:
    def __init__(self):
        """Inicializa todos los clientes necesarios"""
        # Cliente de OpenAI
        self.openai_client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2024-02-15-preview"
        )
        
        # Cliente de Azure Search
        self.search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        self.search_key = os.getenv("AZURE_SEARCH_KEY")
        self.index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
        
        # Cliente para crear índices
        self.index_client = SearchIndexClient(
            endpoint=self.search_endpoint,
            credential=AzureKeyCredential(self.search_key)
        )
        
        # Cliente para buscar documentos
        self.search_client = None  # Se inicializa después de crear el índice
        
    def crear_indice(self):
        """PASO 1: Crear el índice en Azure AI Search"""
        print("📝 Creando índice en Azure AI Search...")
        
        # Definir los campos del índice
        fields = [
            SearchField(
                name="id",
                type=SearchFieldDataType.String,
                key=True,
                filterable=True
            ),
            SearchField(
                name="content",
                type=SearchFieldDataType.String,
                searchable=True,
            ),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=1536,  # Dimensiones de ada-002
                vector_search_profile_name="vector-profile"
            ),
            SearchField(
                name="page",
                type=SearchFieldDataType.Int32,
                filterable=True,
            ),
            SearchField(
                name="chunk_number",
                type=SearchFieldDataType.Int32,
                filterable=True,
            )
        ]
        
        # Configuración de búsqueda vectorial
        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="hnsw-algo",
                    parameters={
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500,
                        "metric": "cosine"
                    }
                )
            ],
            profiles=[
                VectorSearchProfile(
                    name="vector-profile",
                    algorithm_configuration_name="hnsw-algo"
                )
            ]
        )
        
        # Crear el índice
        index = SearchIndex(
            name=self.index_name,
            fields=fields,
            vector_search=vector_search
        )
        
        # Crear o actualizar el índice
        result = self.index_client.create_or_update_index(index)
        print(f"✅ Índice '{result.name}' creado exitosamente\n")
        
        # Inicializar el cliente de búsqueda
        self.search_client = SearchClient(
            endpoint=self.search_endpoint,
            index_name=self.index_name,
            credential=AzureKeyCredential(self.search_key)
        )
        
    def procesar_pdf(self, pdf_path: str):
        """PASO 2: Extraer texto del PDF y dividirlo en chunks"""
        print(f"📄 Procesando PDF: {pdf_path}")
        
        chunks = []
        
        # Abrir y leer el PDF
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            print(f"   Total de páginas: {total_pages}")
            
            # Procesar cada página
            for page_num in range(total_pages):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                
                # Dividir el texto en chunks de ~500 caracteres
                chunk_size = 500
                text_length = len(text)
                
                for i in range(0, text_length, chunk_size):
                    chunk_text = text[i:i + chunk_size]
                    
                    # Solo procesar chunks con contenido significativo
                    if len(chunk_text.strip()) > 50:
                        chunk_id = hashlib.md5(
                            f"{page_num}_{i}_{chunk_text[:20]}".encode()
                        ).hexdigest()
                        
                        chunks.append({
                            "id": chunk_id,
                            "content": chunk_text,
                            "page": page_num + 1,
                            "chunk_number": i // chunk_size
                        })
        
        print(f"✅ {len(chunks)} chunks creados\n")
        return chunks
    
    def generar_embeddings(self, text: str) -> List[float]:
        """Genera embeddings usando Azure OpenAI"""
        response = self.openai_client.embeddings.create(
            input=text,
            model=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        )
        return response.data[0].embedding
    
    def indexar_documentos(self, chunks: List[Dict]):
        """PASO 3: Generar embeddings e indexar en Azure Search"""
        print("🔄 Generando embeddings e indexando...")
        
        # Generar embeddings para cada chunk
        for i, chunk in enumerate(chunks):
            if i % 10 == 0:
                print(f"   Procesando chunk {i+1}/{len(chunks)}")
            
            # Generar embedding
            chunk["content_vector"] = self.generar_embeddings(chunk["content"])
        
        # Subir todos los documentos a Azure Search
        result = self.search_client.upload_documents(documents=chunks)
        print(f"✅ {len(chunks)} chunks indexados exitosamente\n")
        
    def buscar(self, pregunta: str, top_k: int = 3) -> List[Dict]:
        """PASO 4: Buscar información relevante"""
        print(f"🔍 Buscando información sobre: '{pregunta}'")
        
        # Generar embedding de la pregunta
        pregunta_vector = self.generar_embeddings(pregunta)
        
        # Crear consulta vectorial
        vector_query = VectorizedQuery(
            vector=pregunta_vector,
            k_nearest_neighbors=top_k,
            fields="content_vector"
        )
        
        # Realizar búsqueda híbrida (texto + vector)
        results = self.search_client.search(
            search_text=pregunta,
            vector_queries=[vector_query],
            select=["content", "page"],
            top=top_k
        )
        
        # Recopilar resultados
        documentos = []
        for result in results:
            documentos.append({
                "content": result["content"],
                "page": result["page"]
            })
        
        print(f"✅ {len(documentos)} resultados encontrados\n")
        return documentos
    
    def generar_respuesta(self, pregunta: str, contextos: List[Dict]) -> str:
        """PASO 5: Generar respuesta usando GPT"""
        # Construir el contexto
        contexto_completo = "\n\n".join([
            f"[Página {doc['page']}]: {doc['content']}"
            for doc in contextos
        ])
        
        # Crear el prompt
        messages = [
            {
                "role": "system",
                "content": "Eres un asistente útil que responde preguntas basándote únicamente en el contexto proporcionado. Si la información no está en el contexto, di que no lo sabes."
            },
            {
                "role": "user",
                "content": f"""Contexto del documento:
{contexto_completo}

Pregunta: {pregunta}

Por favor, responde la pregunta basándote ÚNICAMENTE en el contexto proporcionado arriba."""
            }
        ]
        
        # Generar respuesta
        response = self.openai_client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
            messages=messages,
            temperature=0.3,
            max_tokens=500
        )
        
        return response.choices[0].message.content
    
    def preguntar(self, pregunta: str) -> str:
        """Método principal para hacer preguntas"""
        # Buscar información relevante
        documentos = self.buscar(pregunta)
        
        if not documentos:
            return "No encontré información relevante sobre tu pregunta en el documento."
        
        # Generar respuesta
        respuesta = self.generar_respuesta(pregunta, documentos)
        
        # Agregar las páginas consultadas
        paginas = list(set([doc["page"] for doc in documentos]))
        respuesta += f"\n\n📖 Información extraída de las páginas: {', '.join(map(str, sorted(paginas)))}"
        
        return respuesta

def main():
    """Función principal"""
    print("🚀 SISTEMA RAG PARA PDF CON AZURE\n")
    print("=" * 50)
    
    # Inicializar el sistema
    rag = SimpleRAG()
    
    # PASO 1: Crear el índice
    rag.crear_indice()
    
    # PASO 2: Procesar el PDF
    # CAMBIA ESTA RUTA A TU ARCHIVO PDF
    pdf_path = "Introducción a la IA generativa_v3 e la Industrial GenAI_VF.pdf"  # ← PON AQUÍ LA RUTA A TU PDF
    
    if not os.path.exists(pdf_path):
        print(f"❌ Error: No se encuentra el archivo '{pdf_path}'")
        print("Por favor, asegúrate de que el PDF está en la carpeta del proyecto")
        return
    
    chunks = rag.procesar_pdf(pdf_path)
    
    # PASO 3: Indexar los chunks
    rag.indexar_documentos(chunks)
    
    print("=" * 50)
    print("✅ SISTEMA LISTO PARA RECIBIR PREGUNTAS\n")
    
    # PASO 4: Hacer preguntas
    while True:
        pregunta = input("\n💬 Haz una pregunta sobre el documento (o 'salir'): ")
        
        if pregunta.lower() == 'salir':
            print("👋 ¡Hasta luego!")
            break
        
        # Obtener respuesta
        print("\n⏳ Procesando...")
        respuesta = rag.preguntar(pregunta)
        
        print("\n📝 RESPUESTA:")
        print("-" * 40)
        print(respuesta)
        print("-" * 40)

if __name__ == "__main__":
    main()