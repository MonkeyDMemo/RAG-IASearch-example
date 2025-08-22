"""
cargar_pdf.py - Script para cargar PDFs al índice de Azure AI Search
Solo ejecutar cuando necesites agregar nuevos documentos
"""

import os
import sys
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
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceNotFoundError
from dotenv import load_dotenv
import hashlib
from datetime import datetime
import json

# Cargar variables de entorno
load_dotenv()

class CargadorPDF:
    def __init__(self):
        """Inicializa clientes de Azure"""
        print("🔧 Inicializando conexiones...")
        
        # Cliente de OpenAI para embeddings
        self.openai_client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2024-02-15-preview"
        )
        
        # Clientes de Azure Search
        self.search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        self.search_key = os.getenv("AZURE_SEARCH_KEY")
        self.index_name = os.getenv("AZURE_SEARCH_INDEX_NAME_V2")

        self.index_client = SearchIndexClient(
            endpoint=self.search_endpoint,
            credential=AzureKeyCredential(self.search_key)
        )
        
        self.search_client = SearchClient(
            endpoint=self.search_endpoint,
            index_name=self.index_name,
            credential=AzureKeyCredential(self.search_key)
        )
        
        # Archivo de registro
        self.log_file = "carga_documentos_log.txt"
        
    def log_actividad(self, mensaje):
        """Guarda un registro de las actividades"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {mensaje}\n"
        
        print(log_entry.strip())
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
    
    def verificar_crear_indice(self):
        """Verifica si el índice existe, si no lo crea"""
        try:
            index = self.index_client.get_index(self.index_name)
            doc_count = self.obtener_conteo_documentos()
            self.log_actividad(f"✅ Índice '{self.index_name}' existe con {doc_count} documentos")
            return True
        except ResourceNotFoundError:
            self.log_actividad(f"📝 Creando nuevo índice '{self.index_name}'...")
            self.crear_indice()
            return False
    
    def crear_indice(self):
        """Crea el índice con la configuración necesaria"""
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
                vector_search_dimensions=1536,
                vector_search_profile_name="vector-profile"
            ),
            SearchField(
                name="source",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True
            ),
            SearchField(
                name="page",
                type=SearchFieldDataType.Int32,
                filterable=True,
            ),
            SearchField(
                name="fecha_carga",
                type=SearchFieldDataType.DateTimeOffset,
                filterable=True,
                sortable=True
            )
        ]
        
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
        
        index = SearchIndex(
            name=self.index_name,
            fields=fields,
            vector_search=vector_search
        )
        
        self.index_client.create_or_update_index(index)
        self.log_actividad(f"✅ Índice '{self.index_name}' creado exitosamente")
    
    def obtener_conteo_documentos(self):
        """Obtiene el número de documentos en el índice"""
        try:
            results = self.search_client.search(
                search_text="*",
                include_total_count=True,
                top=0
            )
            return results.get_count()
        except:
            return 0
    
    def verificar_pdf_existe(self, pdf_path):
        """Verifica si un PDF ya fue cargado"""
        pdf_name = os.path.basename(pdf_path)
        try:
            results = self.search_client.search(
                search_text="",
                filter=f"source eq '{pdf_name}'",
                top=1
            )
            for _ in results:
                return True
            return False
        except:
            return False
    
    def procesar_pdf(self, pdf_path, chunk_size=500):
        """Extrae texto del PDF y lo divide en chunks"""
        chunks = []
        pdf_name = os.path.basename(pdf_path)
        fecha_actual = datetime.now()
        
        self.log_actividad(f"📄 Procesando: {pdf_name}")
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)
                self.log_actividad(f"   Total de páginas: {total_pages}")
                
                for page_num in range(total_pages):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    
                    # Dividir en chunks con overlap
                    overlap = 100
                    text_length = len(text)
                    
                    for i in range(0, text_length, chunk_size - overlap):
                        chunk_text = text[i:i + chunk_size]
                        
                        if len(chunk_text.strip()) > 50:
                            chunk_id = hashlib.md5(
                                f"{pdf_name}_{page_num}_{i}_{chunk_text[:20]}".encode()
                            ).hexdigest()
                            
                            chunks.append({
                                "id": chunk_id,
                                "content": chunk_text,
                                "source": pdf_name,
                                "page": page_num + 1,
                                "fecha_carga": fecha_actual
                            })
                
                self.log_actividad(f"   ✅ {len(chunks)} chunks creados")
                return chunks
                
        except Exception as e:
            self.log_actividad(f"   ❌ Error procesando PDF: {str(e)}")
            return []
    
    def generar_embeddings(self, text):
        """Genera embeddings usando Azure OpenAI"""
        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
            )
            return response.data[0].embedding
        except Exception as e:
            self.log_actividad(f"   ❌ Error generando embedding: {str(e)}")
            return None
    
    def cargar_chunks(self, chunks):
        """Genera embeddings y carga chunks al índice"""
        self.log_actividad(f"🔄 Generando embeddings para {len(chunks)} chunks...")
        
        chunks_con_embeddings = []
        errores = 0
        
        for i, chunk in enumerate(chunks):
            if i % 10 == 0:
                self.log_actividad(f"   Procesando chunk {i+1}/{len(chunks)}")
            
            embedding = self.generar_embeddings(chunk["content"])
            if embedding:
                chunk["content_vector"] = embedding
                chunks_con_embeddings.append(chunk)
            else:
                errores += 1
        
        if chunks_con_embeddings:
            # Cargar en lotes de 100
            batch_size = 100
            total_cargados = 0
            
            for i in range(0, len(chunks_con_embeddings), batch_size):
                batch = chunks_con_embeddings[i:i + batch_size]
                try:
                    result = self.search_client.upload_documents(documents=batch)
                    total_cargados += len(batch)
                    self.log_actividad(f"   ✅ Lote {i//batch_size + 1}: {len(batch)} documentos cargados")
                except Exception as e:
                    self.log_actividad(f"   ❌ Error cargando lote: {str(e)}")
            
            self.log_actividad(f"✅ Total cargados: {total_cargados} chunks")
            if errores > 0:
                self.log_actividad(f"⚠️ Chunks con errores: {errores}")
        else:
            self.log_actividad("❌ No se pudieron procesar chunks")
    
    def cargar_pdf(self, pdf_path, forzar=False):
        """Proceso principal para cargar un PDF"""
        if not os.path.exists(pdf_path):
            self.log_actividad(f"❌ No se encuentra el archivo: {pdf_path}")
            return False
        
        # Verificar/crear índice
        self.verificar_crear_indice()
        
        # Verificar si ya existe
        if not forzar and self.verificar_pdf_existe(pdf_path):
            self.log_actividad(f"⚠️ El PDF '{os.path.basename(pdf_path)}' ya está cargado")
            respuesta = input("¿Deseas cargarlo de nuevo? (s/n): ")
            if respuesta.lower() != 's':
                return False
        
        # Procesar y cargar
        chunks = self.procesar_pdf(pdf_path)
        if chunks:
            self.cargar_chunks(chunks)
            return True
        return False
    
    def listar_documentos(self):
        """Lista todos los documentos cargados"""
        try:
            results = self.search_client.search(
                search_text="*",
                facets=["source"],
                top=0
            )
            
            print("\n📚 DOCUMENTOS EN EL ÍNDICE:")
            print("-" * 40)
            
            if results.get_facets():
                total_docs = 0
                for source in results.get_facets().get("source", []):
                    print(f"   • {source['value']}: {source['count']} chunks")
                    total_docs += 1
                print(f"\n   Total: {total_docs} documentos")
            else:
                print("   No hay documentos cargados")
                
        except Exception as e:
            print(f"Error listando documentos: {e}")

def main():
    """Función principal con menú"""
    cargador = CargadorPDF()
    
    print("\n" + "="*50)
    print("📥 SISTEMA DE CARGA DE PDFs A AZURE AI SEARCH")
    print("="*50)
    
    while True:
        print("\nOpciones:")
        print("1. Cargar un PDF")
        print("2. Cargar múltiples PDFs de una carpeta")
        print("3. Ver documentos cargados")
        print("4. Salir")
        
        opcion = input("\nSelecciona opción (1-4): ")
        
        if opcion == "1":
            pdf_path = input("\nRuta del archivo PDF: ")
            cargador.cargar_pdf(pdf_path)
            
        elif opcion == "2":
            carpeta = input("\nRuta de la carpeta con PDFs: ")
            if os.path.exists(carpeta):
                pdfs = [f for f in os.listdir(carpeta) if f.endswith('.pdf')]
                print(f"\nEncontrados {len(pdfs)} PDFs")
                for pdf in pdfs:
                    pdf_path = os.path.join(carpeta, pdf)
                    cargador.cargar_pdf(pdf_path)
            else:
                print("❌ Carpeta no encontrada")
                
        elif opcion == "3":
            cargador.listar_documentos()
            
        elif opcion == "4":
            print("\n👋 ¡Hasta luego!")
            break
            
        else:
            print("❌ Opción no válida")

if __name__ == "__main__":
    # Si se pasa un archivo como argumento, cargarlo directamente
    if len(sys.argv) > 1:
        cargador = CargadorPDF()
        for pdf_file in sys.argv[1:]:
            cargador.cargar_pdf(pdf_file)
    else:
        main()