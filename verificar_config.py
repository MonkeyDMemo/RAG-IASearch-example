"""
verificar_config.py - Verifica que todo esté configurado correctamente
"""

import os
from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential

load_dotenv()

print("🔍 VERIFICACIÓN DE CONFIGURACIÓN")
print("="*50)

# 1. Verificar variables de entorno
print("\n📋 Variables de entorno:")
variables = [
    "AZURE_SEARCH_ENDPOINT",
    "AZURE_SEARCH_KEY", 
    "AZURE_SEARCH_INDEX_NAME",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_KEY",
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
    "AZURE_OPENAI_CHAT_DEPLOYMENT"
]

todas_ok = True
for var in variables:
    valor = os.getenv(var)
    if valor:
        if "KEY" in var:
            print(f"✅ {var}: ****** (oculto)")
        else:
            print(f"✅ {var}: {valor}")
    else:
        print(f"❌ {var}: NO CONFIGURADO")
        todas_ok = False

if not todas_ok:
    print("\n❌ Faltan variables de configuración en .env")
    exit(1)

# 2. Verificar conexión a Azure OpenAI
print("\n📡 Probando Azure OpenAI...")
try:
    client = AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        api_version="2024-02-15-preview"
    )
    
    # Probar embeddings
    response = client.embeddings.create(
        input="test",
        model=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
    )
    print(f"✅ Embeddings funcionando ({len(response.data[0].embedding)} dimensiones)")
    
    # Probar chat
    response = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        messages=[{"role": "user", "content": "Di 'OK'"}],
        max_tokens=10
    )
    print(f"✅ Chat funcionando (modelo: {os.getenv('AZURE_OPENAI_CHAT_DEPLOYMENT')})")
    
except Exception as e:
    print(f"❌ Error con Azure OpenAI: {e}")
    exit(1)

# 3. Verificar Azure Search
print("\n📡 Probando Azure AI Search...")
try:
    index_client = SearchIndexClient(
        endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))
    )
    
    # Listar índices existentes
    indices = list(index_client.list_indexes())
    print(f"✅ Conexión exitosa - {len(indices)} índices existentes")

    nuevo_indice = os.getenv("AZURE_SEARCH_INDEX_NAME_V2")
    existe = any(idx.name == nuevo_indice for idx in indices)
    
    if existe:
        print(f"⚠️ El índice '{nuevo_indice}' YA EXISTE")
    else:
        print(f"✅ El índice '{nuevo_indice}' será creado al cargar el primer PDF")
    
except Exception as e:
    print(f"❌ Error con Azure Search: {e}")
    exit(1)

print("\n" + "="*50)
print("✅ TODO LISTO PARA COMENZAR")
print("="*50)
print("\nAhora puedes ejecutar:")
print("1. python cargar_pdf.py - Para cargar PDFs")
print("2. python consultar.py - Para hacer preguntas")