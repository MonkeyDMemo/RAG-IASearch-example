import os
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2024-02-15-preview"
)

# Probar embeddings
response = client.embeddings.create(
    input="Hola mundo",
    model="embeddings"  # El nombre de tu deployment
)
print("✅ Embeddings funcionando:", len(response.data[0].embedding), "dimensiones")

# Probar chat
response = client.chat.completions.create(
    model="chat",  # El nombre de tu deployment
    messages=[{"role": "user", "content": "Di 'hola'"}],
    max_tokens=10
)
print("✅ Chat funcionando:", response.choices[0].message.content)