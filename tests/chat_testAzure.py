import os
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2024-02-15-preview"
)

print("🔄 Probando conexión con GPT-4o...")
print(f"Deployment name: {os.getenv('AZURE_OPENAI_CHAT_DEPLOYMENT')}")

try:
    # Probar el modelo de chat
    response = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        messages=[
            {"role": "system", "content": "Eres un asistente útil."},
            {"role": "user", "content": "¿Qué modelo eres y cuáles son tus capacidades principales?"}
        ],
        max_tokens=150,
        temperature=0.7
    )
    
    print("✅ GPT-4o funcionando correctamente!")
    print(f"\nRespuesta del modelo:\n{response.choices[0].message.content}")
    
    # Mostrar información adicional
    print(f"\n📊 Tokens usados: {response.usage.total_tokens}")
    print(f"📊 Modelo: {response.model}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nVerifica:")
    print("1. El nombre del deployment en Azure AI Foundry")
    print("2. Que el deployment esté activo")
    print("3. Que el nombre en .env coincida exactamente")