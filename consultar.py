"""
consultar.py - Script para hacer preguntas al sistema RAG
No carga documentos, solo consulta lo que ya está indexado
"""

import os
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
from datetime import datetime
import json

# Cargar variables de entorno
load_dotenv()

class ConsultorRAG:
    def __init__(self):
        """Inicializa conexiones con Azure"""
        print("🔌 Conectando al sistema RAG...")
        
        # Cliente de OpenAI
        self.openai_client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2024-02-15-preview"
        )
        
        # Cliente de búsqueda
        self.search_client = SearchClient(
            endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
            index_name=os.getenv("AZURE_SEARCH_INDEX_NAME_V2"),
            credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))
        )
        
        # Archivo para guardar historial
        self.historial_file = f"historial_consultas_{datetime.now().strftime('%Y%m%d')}.txt"
        
        # Verificar conexión
        self.verificar_conexion()
        
    def verificar_conexion(self):
        """Verifica que hay documentos en el índice"""
        try:
            results = self.search_client.search("*", include_total_count=True, top=0)
            total = results.get_count()
            
            if total == 0:
                print("⚠️ ADVERTENCIA: No hay documentos en el índice")
                print("   Ejecuta primero 'cargar_pdf.py' para agregar documentos")
            else:
                print(f"✅ Conectado exitosamente - {total} chunks disponibles")
                
                # Mostrar documentos disponibles
                self.mostrar_documentos_disponibles()
                
        except Exception as e:
            print(f"❌ Error conectando al índice: {e}")
            exit(1)
    
    def mostrar_documentos_disponibles(self):
        """Muestra qué documentos están disponibles para consultar"""
        try:
            results = self.search_client.search(
                search_text="*",
                facets=["source"],
                top=0
            )
            
            if results.get_facets():
                print("\n📚 Documentos disponibles para consultar:")
                for source in results.get_facets().get("source", []):
                    print(f"   • {source['value']}")
                print()
        except:
            pass
    
    def guardar_historial(self, pregunta, respuesta, fuentes):
        """Guarda la pregunta y respuesta en el historial"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(self.historial_file, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"Fecha: {timestamp}\n")
            f.write(f"Pregunta: {pregunta}\n")
            f.write(f"Respuesta: {respuesta}\n")
            f.write(f"Fuentes: {', '.join(fuentes)}\n")
            f.write(f"{'='*60}\n")
    
    def buscar_contexto(self, pregunta, top_k=5, filtro_documento=None):
        """Busca información relevante en el índice"""
        try:
            # Generar embedding de la pregunta
            embedding_response = self.openai_client.embeddings.create(
                input=pregunta,
                model=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
            )
            pregunta_vector = embedding_response.data[0].embedding
            
            # Crear consulta vectorial
            vector_query = VectorizedQuery(
                vector=pregunta_vector,
                k_nearest_neighbors=top_k,
                fields="content_vector"
            )
            
            # Configurar filtro si se especifica un documento
            filter_str = None
            if filtro_documento:
                filter_str = f"source eq '{filtro_documento}'"
            
            # Realizar búsqueda híbrida
            results = self.search_client.search(
                search_text=pregunta,
                vector_queries=[vector_query],
                filter=filter_str,
                select=["content", "page", "source"],
                top=top_k
            )
            
            # Recopilar resultados
            contextos = []
            for result in results:
                contextos.append({
                    "content": result["content"],
                    "page": result["page"],
                    "source": result.get("source", "documento")
                })
            
            return contextos
            
        except Exception as e:
            print(f"❌ Error en la búsqueda: {e}")
            return []
    
    def generar_respuesta(self, pregunta, contextos):
        """Genera una respuesta usando GPT-4o"""
        if not contextos:
            return "No encontré información relevante para responder tu pregunta.", []
        
        # Construir el contexto
        contexto_texto = "\n\n".join([
            f"[Fuente: {ctx['source']}, Página {ctx['page']}]\n{ctx['content']}"
            for ctx in contextos
        ])
        
        # Preparar mensajes
        messages = [
            {
                "role": "system",
                "content": """Eres un asistente experto que responde preguntas basándote ÚNICAMENTE 
                en el contexto proporcionado. Si la información no está en el contexto, 
                indica claramente que no tienes esa información. 
                Cita las fuentes cuando sea relevante."""
            },
            {
                "role": "user",
                "content": f"""Contexto de los documentos:
{contexto_texto}

Pregunta: {pregunta}

Por favor, proporciona una respuesta completa y precisa basándote en el contexto anterior."""
            }
        ]
        
        try:
            # Generar respuesta
            response = self.openai_client.chat.completions.create(
                model=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
                messages=messages,
                temperature=0.3,
                max_tokens=800
            )
            
            respuesta = response.choices[0].message.content
            
            # Obtener fuentes únicas
            fuentes = []
            for ctx in contextos:
                fuente_info = f"{ctx['source']} (pág. {ctx['page']})"
                if fuente_info not in fuentes:
                    fuentes.append(fuente_info)
            
            return respuesta, fuentes
            
        except Exception as e:
            print(f"❌ Error generando respuesta: {e}")
            return "Error al generar la respuesta.", []
    
    def consultar(self, pregunta, filtro_documento=None):
        """Proceso completo de consulta"""
        print("\n🔍 Buscando información relevante...")
        
        # Buscar contexto
        contextos = self.buscar_contexto(pregunta, filtro_documento=filtro_documento)
        
        if not contextos:
            print("❌ No se encontró información relevante")
            return None
        
        print(f"✅ Encontrados {len(contextos)} fragmentos relevantes")
        print("🤖 Generando respuesta...")
        
        # Generar respuesta
        respuesta, fuentes = self.generar_respuesta(pregunta, contextos)
        
        # Guardar en historial
        self.guardar_historial(pregunta, respuesta, fuentes)
        
        return {
            "respuesta": respuesta,
            "fuentes": fuentes
        }

def modo_interactivo():
    """Modo interactivo de consultas"""
    consultor = ConsultorRAG()
    
    print("\n" + "="*60)
    print("💬 MODO DE CONSULTA INTERACTIVO")
    print("="*60)
    print("\nComandos especiales:")
    print("  • 'salir' - Terminar el programa")
    print("  • 'historial' - Ver preguntas anteriores")
    print("  • 'documentos' - Ver documentos disponibles")
    print("  • 'filtrar:nombre.pdf' - Buscar solo en un documento específico")
    print("\n")
    
    filtro_activo = None
    
    while True:
        if filtro_activo:
            prompt = f"\n❓ Tu pregunta (filtro: {filtro_activo}): "
        else:
            prompt = "\n❓ Tu pregunta: "
            
        pregunta = input(prompt)
        
        if pregunta.lower() == 'salir':
            print("\n👋 ¡Hasta luego!")
            print(f"📝 Historial guardado en: {consultor.historial_file}")
            break
            
        elif pregunta.lower() == 'historial':
            if os.path.exists(consultor.historial_file):
                print(f"\n📜 Historial en: {consultor.historial_file}")
                with open(consultor.historial_file, "r", encoding="utf-8") as f:
                    print(f.read())
            else:
                print("📭 No hay historial aún")
            continue
            
        elif pregunta.lower() == 'documentos':
            consultor.mostrar_documentos_disponibles()
            continue
            
        elif pregunta.lower().startswith('filtrar:'):
            filtro_activo = pregunta.split(':', 1)[1].strip()
            print(f"✅ Filtro activado para: {filtro_activo}")
            continue
            
        elif pregunta.lower() == 'quitar filtro':
            filtro_activo = None
            print("✅ Filtro desactivado")
            continue
        
        # Realizar consulta
        resultado = consultor.consultar(pregunta, filtro_documento=filtro_activo)
        
        if resultado:
            print("\n" + "-"*60)
            print("📝 RESPUESTA:")
            print("-"*60)
            print(resultado["respuesta"])
            print("\n📚 Fuentes consultadas:")
            for fuente in resultado["fuentes"]:
                print(f"   • {fuente}")
            print("-"*60)

def modo_batch(preguntas_file):
    """Procesa un archivo con múltiples preguntas"""
    consultor = ConsultorRAG()
    
    if not os.path.exists(preguntas_file):
        print(f"❌ No se encuentra el archivo: {preguntas_file}")
        return
    
    print(f"\n📋 Procesando preguntas desde: {preguntas_file}")
    
    with open(preguntas_file, "r", encoding="utf-8") as f:
        preguntas = f.readlines()
    
    resultados_file = f"respuestas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(resultados_file, "w", encoding="utf-8") as f:
        for i, pregunta in enumerate(preguntas, 1):
            pregunta = pregunta.strip()
            if not pregunta:
                continue
                
            print(f"\n[{i}/{len(preguntas)}] Procesando: {pregunta[:50]}...")
            resultado = consultor.consultar(pregunta)
            
            if resultado:
                f.write(f"\n{'='*60}\n")
                f.write(f"PREGUNTA {i}: {pregunta}\n")
                f.write(f"RESPUESTA: {resultado['respuesta']}\n")
                f.write(f"FUENTES: {', '.join(resultado['fuentes'])}\n")
    
    print(f"\n✅ Respuestas guardadas en: {resultados_file}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Modo batch: procesar archivo de preguntas
        modo_batch(sys.argv[1])
    else:
        # Modo interactivo
        modo_interactivo()