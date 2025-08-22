"""
gestionar_indice.py - Utilidades para administrar el índice de Azure AI Search
"""

import os
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
from datetime import datetime
import json

load_dotenv()

class GestorIndice:
    def __init__(self):
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
    
    def info_indice(self):
        """Muestra información detallada del índice"""
        print("\n" + "="*60)
        print("📊 INFORMACIÓN DEL ÍNDICE")
        print("="*60)
        
        try:
            # Información básica
            index = self.index_client.get_index(self.index_name)
            print(f"\n📌 Nombre: {self.index_name}")
            print(f"📌 Endpoint: {self.search_endpoint}")
            
            # Campos
            print(f"\n📋 Campos del índice ({len(index.fields)} campos):")
            for field in index.fields:
                tipo = field.type.value if hasattr(field.type, 'value') else str(field.type)
                print(f"   • {field.name}: {tipo}")
            
            # Estadísticas
            results = self.search_client.search("*", include_total_count=True, top=0)
            total = results.get_count()
            print(f"\n📈 Total de chunks: {total}")
            
            # Documentos únicos
            facet_results = self.search_client.search(
                search_text="*",
                facets=["source"],
                top=0
            )
            
            if facet_results.get_facets():
                print("\n📚 Documentos indexados:")
                total_size = 0
                for source in facet_results.get_facets().get("source", []):
                    chunks = source['count']
                    size_est = chunks * 500 / 1024  # Estimación en KB
                    total_size += size_est
                    print(f"   • {source['value']}")
                    print(f"     - Chunks: {chunks}")
                    print(f"     - Tamaño estimado: {size_est:.1f} KB")
                
                print(f"\n💾 Tamaño total estimado: {total_size:.1f} KB ({total_size/1024:.2f} MB)")
            
        except Exception as e:
            print(f"❌ Error obteniendo información: {e}")
    
    def eliminar_documento(self, nombre_documento):
        """Elimina un documento específico del índice"""
        print(f"\n🗑️ Eliminando documento: {nombre_documento}")
        
        try:
            # Buscar todos los chunks del documento
            results = self.search_client.search(
                search_text="",
                filter=f"source eq '{nombre_documento}'",
                select=["id"],
                top=1000
            )
            
            # Recopilar IDs
            ids_to_delete = []
            for result in results:
                ids_to_delete.append({"id": result["id"]})
            
            if ids_to_delete:
                # Eliminar en lotes
                batch_size = 100
                total_deleted = 0
                
                for i in range(0, len(ids_to_delete), batch_size):
                    batch = ids_to_delete[i:i + batch_size]
                    self.search_client.delete_documents(documents=batch)
                    total_deleted += len(batch)
                    print(f"   Eliminados {total_deleted}/{len(ids_to_delete)} chunks...")
                
                print(f"✅ Documento eliminado: {len(ids_to_delete)} chunks")
            else:
                print("❌ No se encontró el documento")
                
        except Exception as e:
            print(f"❌ Error eliminando documento: {e}")
    
    def limpiar_indice_completo(self):
        """Elimina TODOS los documentos del índice"""
        respuesta = input("\n⚠️ ¿Estás SEGURO de eliminar TODOS los documentos? (escribir 'SI ELIMINAR'): ")
        
        if respuesta != "SI ELIMINAR":
            print("Operación cancelada")
            return
        
        print("\n🗑️ Eliminando todos los documentos...")
        
        try:
            # Obtener todos los IDs
            all_results = []
            skip = 0
            
            while True:
                results = self.search_client.search(
                    search_text="*",
                    select=["id"],
                    top=1000,
                    skip=skip
                )
                
                batch = list(results)
                if not batch:
                    break
                    
                all_results.extend(batch)
                skip += 1000
            
            if all_results:
                ids_to_delete = [{"id": doc["id"]} for doc in all_results]
                
                # Eliminar en lotes
                batch_size = 100
                for i in range(0, len(ids_to_delete), batch_size):
                    batch = ids_to_delete[i:i + batch_size]
                    self.search_client.delete_documents(documents=batch)
                
                print(f"✅ Eliminados {len(ids_to_delete)} documentos")
            else:
                print("El índice ya está vacío")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def exportar_estadisticas(self):
        """Exporta estadísticas del índice a un archivo JSON"""
        filename = f"estadisticas_indice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            # Recopilar estadísticas
            stats = {
                "fecha_exportacion": datetime.now().isoformat(),
                "index_name": self.index_name,
                "endpoint": self.search_endpoint,
                "documentos": []
            }
            
            # Obtener información de documentos
            facet_results = self.search_client.search(
                search_text="*",
                facets=["source"],
                top=0
            )
            
            if facet_results.get_facets():
                for source in facet_results.get_facets().get("source", []):
                    stats["documentos"].append({
                        "nombre": source['value'],
                        "chunks": source['count'],
                        "tamaño_estimado_kb": source['count'] * 500 / 1024
                    })
            
            # Total de chunks
            results = self.search_client.search("*", include_total_count=True, top=0)
            stats["total_chunks"] = results.get_count()
            
            # Guardar a archivo
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Estadísticas exportadas a: {filename}")
            
        except Exception as e:
            print(f"❌ Error exportando: {e}")
    
    def buscar_duplicados(self):
        """Busca posibles documentos duplicados"""
        print("\n🔍 Buscando posibles duplicados...")
        
        try:
            # Obtener todos los documentos
            facet_results = self.search_client.search(
                search_text="*",
                facets=["source"],
                top=0
            )
            
            if facet_results.get_facets():
                sources = facet_results.get_facets().get("source", [])
                
                # Buscar nombres similares
                nombres = [s['value'] for s in sources]
                duplicados = []
                
                for i, nombre1 in enumerate(nombres):
                    for nombre2 in nombres[i+1:]:
                        # Comparar nombres sin extensión
                        base1 = os.path.splitext(nombre1)[0].lower()
                        base2 = os.path.splitext(nombre2)[0].lower()
                        
                        if base1 == base2 or base1 in base2 or base2 in base1:
                            duplicados.append((nombre1, nombre2))
                
                if duplicados:
                    print("\n⚠️ Posibles duplicados encontrados:")
                    for dup in duplicados:
                        print(f"   • {dup[0]} <-> {dup[1]}")
                else:
                    print("✅ No se encontraron duplicados")
                    
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    gestor = GestorIndice()
    
    while True:
        print("\n" + "="*60)
        print("🛠️ GESTIÓN DEL ÍNDICE DE AZURE AI SEARCH")
        print("="*60)
        print("\n1. Ver información del índice")
        print("2. Listar documentos")
        print("3. Eliminar un documento específico")
        print("4. Limpiar TODO el índice")
        print("5. Exportar estadísticas")
        print("6. Buscar duplicados")
        print("7. Salir")
        
        opcion = input("\nSelecciona opción (1-7): ")
        
        if opcion == "1":
            gestor.info_indice()
            
        elif opcion == "2":
            gestor.info_indice()
            
        elif opcion == "3":
            nombre = input("\nNombre del documento a eliminar (con extensión): ")
            gestor.eliminar_documento(nombre)
            
        elif opcion == "4":
            gestor.limpiar_indice_completo()
            
        elif opcion == "5":
            gestor.exportar_estadisticas()
            
        elif opcion == "6":
            gestor.buscar_duplicados()
            
        elif opcion == "7":
            print("\n👋 ¡Hasta luego!")
            break
            
        else:
            print("❌ Opción no válida")

if __name__ == "__main__":
    main()