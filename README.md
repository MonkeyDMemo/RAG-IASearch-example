# Sistema RAG (Retrieval-Augmented Generation) con Azure AI Search

## 📋 Tabla de Contenidos

- [Introducción](#introducción)
- [¿Qué es RAG?](#qué-es-rag)
- [Arquitectura del Sistema](#arquitectura-del-sistema)
- [Componentes de Azure](#componentes-de-azure)
- [Instalación y Configuración](#instalación-y-configuración)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Flujo de Trabajo](#flujo-de-trabajo)
- [Guía de Uso](#guía-de-uso)
- [Estructura de Datos](#estructura-de-datos)
- [Optimización y Mejores Prácticas](#optimización-y-mejores-prácticas)
- [Costos y Escalabilidad](#costos-y-escalabilidad)
- [Troubleshooting](#troubleshooting)
- [Glosario](#glosario)

---

## 📖 Introducción

Este documento describe la implementación de un sistema RAG (Retrieval-Augmented Generation) utilizando Azure AI Search y Azure OpenAI. El sistema permite procesar documentos PDF, indexar su contenido y realizar consultas inteligentes utilizando modelos de lenguaje avanzados.

### Objetivo del Sistema

Crear una base de conocimiento consultable que:
- Procese documentos PDF automáticamente
- Permita búsquedas semánticas avanzadas
- Genere respuestas precisas basadas en el contenido indexado
- Mantenga trazabilidad de las fuentes de información

### Casos de Uso

- **Documentación técnica**: Consultar manuales y guías técnicas
- **Base de conocimiento empresarial**: Centralizar información corporativa
- **Investigación**: Analizar múltiples documentos académicos
- **Soporte al cliente**: Responder preguntas basadas en documentación

---

## 🤖 ¿Qué es RAG?

### Definición

RAG (Retrieval-Augmented Generation) es una arquitectura que combina:
- **Retrieval (Recuperación)**: Búsqueda de información relevante
- **Augmented (Aumentado)**: Enriquecimiento del contexto
- **Generation (Generación)**: Creación de respuestas usando LLMs

### ¿Por qué RAG?

#### Problemas de los LLMs tradicionales:
1. **Conocimiento estático**: Limitado a datos de entrenamiento
2. **Alucinaciones**: Pueden inventar información
3. **Sin fuentes**: No pueden citar de dónde viene la información
4. **Desactualización**: No tienen información reciente

#### Solución con RAG:
1. **Conocimiento dinámico**: Actualizable en tiempo real
2. **Información verificable**: Basada en documentos reales
3. **Citas precisas**: Referencias a fuentes específicas
4. **Actualización continua**: Agregar nuevos documentos cuando sea necesario

### Flujo RAG Conceptual

```
1. PREGUNTA DEL USUARIO
        ↓
2. CONVERSIÓN A EMBEDDING
        ↓
3. BÚSQUEDA SEMÁNTICA
        ↓
4. RECUPERACIÓN DE CONTEXTO
        ↓
5. GENERACIÓN DE RESPUESTA
        ↓
6. RESPUESTA CON FUENTES
```

---

## 🏗️ Arquitectura del Sistema

### Arquitectura General

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│                 │     │                  │     │                 │
│   Documentos    │────▶│   Procesamiento  │────▶│  Azure Search   │
│     (PDFs)      │     │   & Embeddings   │     │     Index       │
│                 │     │                  │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │                           │
                               │                           │
                        ┌──────▼──────────┐               │
                        │                 │               │
                        │  Azure OpenAI   │               │
                        │   Embeddings    │               │
                        │                 │               │
                        └─────────────────┘               │
                                                          │
┌─────────────────┐     ┌──────────────────┐            │
│                 │     │                  │            │
│     Usuario     │────▶│    Consulta      │◀───────────┘
│                 │     │                  │
└─────────────────┘     └──────────────────┘
        ▲                        │
        │                        │
        │               ┌────────▼─────────┐
        │               │                  │
        └───────────────│   Azure OpenAI   │
                       │      GPT-4o       │
                       │                  │
                       └──────────────────┘
```

### Componentes Principales

#### 1. **Capa de Ingesta**
- Lectura de PDFs
- Extracción de texto
- División en chunks
- Generación de metadatos

#### 2. **Capa de Procesamiento**
- Generación de embeddings
- Validación de datos
- Gestión de errores
- Logging

#### 3. **Capa de Almacenamiento**
- Azure AI Search Index
- Vectores de embeddings
- Metadatos estructurados
- Índices de búsqueda

#### 4. **Capa de Búsqueda**
- Búsqueda híbrida (texto + vectorial)
- Ranking de relevancia
- Filtros y facetas
- Recuperación de contexto

#### 5. **Capa de Generación**
- Construcción de prompts
- Llamadas a GPT-4o
- Post-procesamiento
- Formateo de respuestas

---

## ☁️ Componentes de Azure

### Azure AI Search

#### ¿Qué es?
Servicio de búsqueda como servicio (SaaS) que proporciona:
- Indexación de documentos
- Búsqueda de texto completo
- Búsqueda vectorial/semántica
- Búsqueda híbrida

#### Configuración utilizada:
- **Tier**: Basic o Standard
- **Replicas**: 1 (mínimo)
- **Particiones**: 1 (mínimo)
- **Índice**: `pdf-index-v2`

#### Campos del índice:
```json
{
  "fields": [
    {"name": "id", "type": "Edm.String", "key": true},
    {"name": "content", "type": "Edm.String", "searchable": true},
    {"name": "content_vector", "type": "Collection(Edm.Single)", "dimensions": 1536},
    {"name": "source", "type": "Edm.String", "filterable": true},
    {"name": "page", "type": "Edm.Int32", "filterable": true},
    {"name": "fecha_carga", "type": "Edm.DateTimeOffset", "filterable": true}
  ]
}
```

### Azure OpenAI

#### Modelos desplegados:

1. **text-embedding-ada-002**
   - Uso: Generación de embeddings
   - Dimensiones: 1536
   - Costo: ~$0.0001 por 1K tokens

2. **GPT-4o**
   - Uso: Generación de respuestas
   - Contexto: 128K tokens
   - Costo: ~$0.005 por 1K tokens input, ~$0.015 por 1K tokens output

#### Configuración de deployments:
- **Rate limit**: 50,000 TPM (Tokens por minuto)
- **Región**: Seleccionar la más cercana
- **Versión API**: 2024-02-15-preview

---

## 🛠️ Instalación y Configuración

### Prerrequisitos

#### Software necesario:
- Python 3.8 o superior
- pip (gestor de paquetes de Python)
- Git (opcional)

#### Cuentas necesarias:
- Suscripción de Azure activa
- Acceso a Azure OpenAI (requiere aprobación)

### Paso 1: Crear recursos en Azure

#### 1.1 Azure AI Search
```bash
# Azure CLI
az search service create \
  --name mi-search-rag \
  --resource-group mi-grupo \
  --sku basic \
  --location eastus
```

#### 1.2 Azure OpenAI
```bash
# Azure CLI
az cognitiveservices account create \
  --name mi-openai-rag \
  --resource-group mi-grupo \
  --kind OpenAI \
  --sku S0 \
  --location eastus
```

### Paso 2: Configurar el entorno local

#### 2.1 Clonar o crear el proyecto
```bash
mkdir rag-azure-system
cd rag-azure-system
```

#### 2.2 Instalar dependencias
```bash
pip install -r requirements.txt
```

**requirements.txt:**
```
azure-search-documents==11.4.0
openai==1.3.0
PyPDF2==3.0.1
python-dotenv==1.0.0
azure-core==1.29.0
```

#### 2.3 Configurar variables de entorno

Crear archivo `.env`:
```env
# Azure Search
AZURE_SEARCH_ENDPOINT=https://mi-search-rag.search.windows.net
AZURE_SEARCH_KEY=tu-admin-key
AZURE_SEARCH_INDEX_NAME=pdf-index-v2

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://mi-openai-rag.openai.azure.com/
AZURE_OPENAI_KEY=tu-openai-key
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=embeddings
AZURE_OPENAI_CHAT_DEPLOYMENT=chat
```

### Paso 3: Desplegar modelos en Azure AI Foundry

1. Acceder a [ai.azure.com](https://ai.azure.com)
2. Crear/seleccionar proyecto
3. Ir a "Deployments"
4. Desplegar:
   - `text-embedding-ada-002` como "embeddings"
   - `gpt-4o` como "chat"

---

## 📁 Estructura del Proyecto

### Organización de archivos

```
rag-azure-system/
│
├── 📄 Scripts principales
│   ├── cargar_pdf.py          # Carga documentos al índice
│   ├── consultar.py           # Realiza consultas
│   └── gestionar_indice.py    # Administración del índice
│
├── 📄 Scripts auxiliares
│   ├── verificar_config.py    # Verifica configuración
│   └── migrar_indice.py       # Migración de índices
│
├── 📁 Documentos
│   └── pdfs/                  # Carpeta para PDFs
│       ├── documento1.pdf
│       └── documento2.pdf
│
├── 📄 Configuración
│   ├── .env                   # Variables de entorno
│   └── requirements.txt       # Dependencias Python
│
├── 📄 Logs y salidas
│   ├── carga_documentos_log.txt
│   ├── historial_consultas_*.txt
│   └── estadisticas_indice_*.json
│
└── 📄 Documentación
    └── README.md
```

### Descripción de scripts

#### **cargar_pdf.py**
- **Función**: Procesar y cargar PDFs al índice
- **Características**:
  - Verificación de duplicados
  - Procesamiento por lotes
  - Generación de embeddings
  - Logging detallado

#### **consultar.py**
- **Función**: Realizar consultas al sistema
- **Características**:
  - Búsqueda híbrida
  - Filtros por documento
  - Historial de consultas
  - Modo interactivo y batch

#### **gestionar_indice.py**
- **Función**: Administrar el índice
- **Características**:
  - Ver estadísticas
  - Eliminar documentos
  - Exportar información
  - Detectar duplicados

---

## 🔄 Flujo de Trabajo

### 1. Carga de Documentos

#### Proceso detallado:

1. **Lectura del PDF**
   ```python
   pdf_reader = PyPDF2.PdfReader(file)
   ```

2. **Extracción por páginas**
   ```python
   for page_num in range(total_pages):
       text = page.extract_text()
   ```

3. **División en chunks**
   - Tamaño: 500 caracteres
   - Overlap: 100 caracteres
   - Validación: mínimo 50 caracteres

4. **Generación de embeddings**
   ```python
   embedding = openai_client.embeddings.create(
       input=chunk_text,
       model="embeddings"
   )
   ```

5. **Carga al índice**
   ```python
   search_client.upload_documents(documents=chunks)
   ```

### 2. Proceso de Consulta

#### Proceso detallado:

1. **Recepción de pregunta**
   ```python
   pregunta = input("Tu pregunta: ")
   ```

2. **Generación de embedding**
   ```python
   pregunta_vector = generar_embedding(pregunta)
   ```

3. **Búsqueda híbrida**
   ```python
   results = search_client.search(
       search_text=pregunta,
       vector_queries=[vector_query],
       top=5
   )
   ```

4. **Construcción de prompt**
   ```python
   contexto = "\n".join([chunk["content"] for chunk in results])
   prompt = f"Contexto: {contexto}\nPregunta: {pregunta}"
   ```

5. **Generación de respuesta**
   ```python
   response = openai_client.chat.completions.create(
       model="chat",
       messages=[{"role": "user", "content": prompt}]
   )
   ```

---

## 📖 Guía de Uso

### Caso de Uso 1: Primera carga de documentos

```bash
# 1. Verificar configuración
python verificar_config.py

# 2. Cargar un PDF individual
python cargar_pdf.py
> Opción: 1
> Ruta: documento.pdf

# 3. Verificar carga
python gestionar_indice.py
> Opción: 1 (Ver información)
```

### Caso de Uso 2: Consultas sobre documentos

```bash
# Modo interactivo
python consultar.py

# Ejemplos de consultas:
> ¿Qué es la IA generativa?
> ¿Cuáles son los componentes principales de MCP?
> filtrar:MCP_explained.pdf
> ¿Qué dice sobre arquitectura?
```

### Caso de Uso 3: Procesamiento batch

```bash
# Crear archivo preguntas.txt
echo "¿Qué es RAG?" > preguntas.txt
echo "¿Cómo funciona Azure Search?" >> preguntas.txt

# Procesar
python consultar.py preguntas.txt

# Resultados en: respuestas_[timestamp].txt
```

### Caso de Uso 4: Gestión del índice

```bash
python gestionar_indice.py

# Opciones disponibles:
# 1. Ver información del índice
# 2. Listar documentos
# 3. Eliminar documento específico
# 4. Limpiar todo el índice
# 5. Exportar estadísticas
# 6. Buscar duplicados
```

---

## 🗂️ Estructura de Datos

### Esquema del Chunk

```json
{
  "id": "d3f4a8b2c9e1f6a8b3d2e1f9",
  "content": "La inteligencia artificial generativa es una rama...",
  "content_vector": [0.023, -0.045, 0.127, ...],
  "source": "introduccion_ia.pdf",
  "page": 5,
  "fecha_carga": "2024-08-22T10:30:00Z"
}
```

### Campos explicados:

| Campo | Tipo | Descripción | Uso |
|-------|------|-------------|-----|
| **id** | String | Identificador único hash MD5 | Clave primaria |
| **content** | String | Texto del chunk | Búsqueda textual |
| **content_vector** | Float[] | Embedding de 1536 dimensiones | Búsqueda semántica |
| **source** | String | Nombre del documento origen | Filtrado y citación |
| **page** | Int32 | Número de página | Referencias precisas |
| **fecha_carga** | DateTime | Timestamp de carga | Auditoría |

### Configuración de búsqueda

#### Búsqueda híbrida:
```python
VectorizedQuery(
    vector=embedding,
    k_nearest_neighbors=5,
    fields="content_vector"
)
```

#### Algoritmo HNSW:
```python
HnswAlgorithmConfiguration(
    m=4,                    # Conexiones por nodo
    efConstruction=400,     # Calidad de construcción
    efSearch=500,          # Calidad de búsqueda
    metric="cosine"        # Métrica de distancia
)
```

---

## ⚡ Optimización y Mejores Prácticas

### 1. Tamaño de Chunks

#### Recomendaciones:
- **Pequeños (300-500 chars)**: Mayor precisión, más tokens
- **Medianos (500-1000 chars)**: Balance óptimo
- **Grandes (1000-2000 chars)**: Más contexto, menos precisión

```python
# Configuración recomendada
CHUNK_SIZE = 500
OVERLAP = 100
MIN_CHUNK_LENGTH = 50
```

### 2. Número de resultados (top_k)

```python
# Configuración según caso de uso
TOP_K_SIMPLE = 3      # Preguntas simples
TOP_K_COMPLEX = 5     # Preguntas complejas
TOP_K_RESEARCH = 10   # Investigación profunda
```

### 3. Temperatura del modelo

```python
# Configuración según tipo de respuesta
TEMPERATURE_FACTUAL = 0.3    # Respuestas precisas
TEMPERATURE_BALANCED = 0.5   # Balance
TEMPERATURE_CREATIVE = 0.7   # Respuestas creativas
```

### 4. Procesamiento por lotes

```python
# Para grandes volúmenes
BATCH_SIZE = 100  # Documentos por lote
RETRY_ATTEMPTS = 3
RETRY_DELAY = 5  # segundos
```

### 5. Caché de embeddings

```python
# Evitar regenerar embeddings
embedding_cache = {}

def get_embedding_cached(text):
    if text not in embedding_cache:
        embedding_cache[text] = generate_embedding(text)
    return embedding_cache[text]
```

### 6. Validación de calidad

```python
# Verificar calidad de chunks
def validate_chunk(chunk):
    # Longitud mínima
    if len(chunk) < MIN_CHUNK_LENGTH:
        return False
    
    # Contenido significativo
    if chunk.count(' ') < 5:  # Muy pocas palabras
        return False
    
    # No solo números o símbolos
    if not any(c.isalpha() for c in chunk):
        return False
    
    return True
```

---

## 💰 Costos y Escalabilidad

### Estructura de costos

#### Azure AI Search
| Tier | Costo/mes | Documentos | Índices | Uso recomendado |
|------|-----------|------------|---------|-----------------|
| Free | $0 | 10,000 | 3 | Desarrollo |
| Basic | ~$75 | 15M | 15 | Producción pequeña |
| Standard S1 | ~$250 | 1M/partición | 50 | Producción media |
| Standard S2 | ~$1,000 | 1M/partición | 200 | Producción grande |

#### Azure OpenAI
| Operación | Modelo | Costo aproximado |
|-----------|--------|------------------|
| Embeddings | ada-002 | $0.0001/1K tokens |
| Consulta | GPT-4o | $0.005/1K input + $0.015/1K output |

### Ejemplo de costos mensuales

Para un sistema con:
- 100 PDFs (≈5,000 chunks)
- 1,000 consultas/mes
- Azure Search Basic

```
Azure Search Basic:        $75.00
Embeddings iniciales:      $5.00
Consultas (1,000):         $20.00
--------------------------------
Total mensual:             ~$100.00
```

### Estrategias de optimización de costos

1. **Usar Free Tier para desarrollo**
2. **Implementar caché de respuestas frecuentes**
3. **Optimizar tamaño de chunks**
4. **Usar GPT-3.5-turbo para consultas simples**
5. **Implementar rate limiting**

### Escalabilidad

#### Límites del sistema:
- **Documentos**: Ilimitado (depende del tier)
- **Consultas concurrentes**: 50-100 (depende del tier)
- **Tamaño máximo de índice**: 50GB (Basic)
- **Tokens por minuto**: 50,000 (configurable)

#### Estrategias de escalado:
1. **Vertical**: Aumentar tier de Azure Search
2. **Horizontal**: Múltiples índices por categoría
3. **Caché**: Redis para respuestas frecuentes
4. **CDN**: Para documentos estáticos

---

## 🔧 Troubleshooting

### Errores comunes y soluciones

#### Error: "DeploymentNotFound"
```python
# Problema: Nombre incorrecto del deployment
# Solución: Verificar en Azure AI Foundry el nombre exacto
AZURE_OPENAI_CHAT_DEPLOYMENT=nombre-correcto
```

#### Error: "Index not found"
```python
# Problema: El índice no existe
# Solución: Ejecutar cargar_pdf.py para crear el índice
python cargar_pdf.py
```

#### Error: "Rate limit exceeded"
```python
# Problema: Demasiadas solicitudes
# Solución: Implementar retry con backoff
import time

def retry_with_backoff(func, max_retries=3):
    for i in range(max_retries):
        try:
            return func()
        except RateLimitError:
            time.sleep(2 ** i)
    raise Exception("Max retries exceeded")
```

#### Error: "PDF extraction failed"
```python
# Problema: PDF protegido o corrupto
# Solución: Usar alternativas como pdfplumber
import pdfplumber

with pdfplumber.open(pdf_path) as pdf:
    text = pdf.pages[0].extract_text()
```

#### Error: "Embedding dimension mismatch"
```python
# Problema: Cambio de modelo de embeddings
# Solución: Recrear el índice con las dimensiones correctas
# ada-002: 1536 dimensiones
# text-embedding-3-small: 1536 dimensiones
# text-embedding-3-large: 3072 dimensiones
```

### Logs y debugging

#### Habilitar logging detallado:
```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)
```

#### Verificar conexiones:
```python
# Test Azure Search
def test_search_connection():
    try:
        search_client.get_document_count()
        print("✅ Azure Search conectado")
    except Exception as e:
        print(f"❌ Error: {e}")

# Test Azure OpenAI
def test_openai_connection():
    try:
        response = openai_client.embeddings.create(
            input="test",
            model="embeddings"
        )
        print("✅ Azure OpenAI conectado")
    except Exception as e:
        print(f"❌ Error: {e}")
```

---

## 📚 Glosario

### Términos técnicos

**Chunk**
: Fragmento de texto de tamaño fijo extraído de un documento mayor. Unidad básica de indexación.

**Embedding**
: Representación vectorial numérica de texto que captura su significado semántico. Vector de 1536 dimensiones en nuestro caso.

**Búsqueda vectorial**
: Búsqueda basada en similitud coseno entre vectores de embeddings, encuentra contenido semánticamente similar.

**Búsqueda híbrida**
: Combinación de búsqueda textual tradicional (BM25) con búsqueda vectorial para mejores resultados.

**HNSW (Hierarchical Navigable Small World)**
: Algoritmo de búsqueda aproximada de vecinos más cercanos usado para búsqueda vectorial eficiente.

**Facetas**
: Categorías o filtros que permiten refinar resultados de búsqueda (ej: por documento fuente).

**Token**
: Unidad básica de texto procesada por modelos de lenguaje. Aproximadamente 4 caracteres en inglés.

**Temperature**
: Parámetro que controla la aleatoriedad en la generación de texto. 0=determinista, 1=muy creativo.

**Top-k**
: Número de resultados más relevantes a recuperar en una búsqueda.

**TPM (Tokens Per Minute)**
: Límite de procesamiento de tokens por minuto en Azure OpenAI.

**Overlap**
: Superposición entre chunks consecutivos para mantener contexto.

**Prompt**
: Instrucciones y contexto proporcionados al modelo de lenguaje para generar una respuesta.

**LLM (Large Language Model)**
: Modelo de lenguaje grande como GPT-4o usado para generación de texto.

**Hallucination**
: Cuando un LLM genera información falsa o inventada no presente en sus datos de entrenamiento.

**Fine-tuning**
: Proceso de ajustar un modelo preentrenado para una tarea específica (no usado en este sistema).

---

## 📈 Métricas y KPIs

### Métricas de rendimiento

```python
# Métricas a monitorear
metrics = {
    "response_time": "< 3 segundos",
    "accuracy": "> 90% respuestas correctas",
    "coverage": "> 80% preguntas respondidas",
    "cost_per_query": "< $0.02",
    "uptime": "> 99.9%"
}
```

### Dashboard de monitoreo

```python
def generate_metrics_report():
    return {
        "total_documents": get_document_count(),
        "total_chunks": get_chunk_count(),
        "queries_today": get_daily_queries(),
        "avg_response_time": calculate_avg_response(),
        "top_queries": get_top_queries(),
        "error_rate": calculate_error_rate()
    }
```

---

## 🚀 Próximos pasos y mejoras

### Mejoras a corto plazo
1. Implementar caché de respuestas
2. Agregar soporte para más formatos (DOCX, TXT)
3. Interfaz web con Streamlit
4. Exportación de respuestas a PDF

### Mejoras a mediano plazo
1. OCR para PDFs escaneados
2. Soporte multiidioma
3. Sistema de feedback de usuarios
4. Analytics dashboard

### Mejoras a largo plazo
1. Fine-tuning de modelos
2. Integración con Microsoft Teams
3. API REST para integración
4. Procesamiento de imágenes y tablas

---

## 📞 Soporte y recursos

### Recursos oficiales
- [Azure AI Search Documentation](https://docs.microsoft.com/azure/search/)
- [Azure OpenAI Documentation](https://docs.microsoft.com/azure/cognitive-services/openai/)
- [Python SDK Documentation](https://docs.microsoft.com/python/api/azure-search-documents/)

### Comunidad
- [Stack Overflow - Azure Search](https://stackoverflow.com/questions/tagged/azure-cognitive-search)
- [GitHub - Azure SDK for Python](https://github.com/Azure/azure-sdk-for-python)
- [Microsoft Q&A](https://docs.microsoft.com/answers/topics/azure-cognitive-search.html)

### Contacto del proyecto
- **Desarrollador**: [Tu nombre]
- **Email**: [Tu email]
- **Repositorio**: [URL del repositorio]
- **Última actualización**: Agosto 2024

---

## 📄 Licencia y créditos

Este proyecto está desarrollado para uso empresarial/educativo.

### Tecnologías utilizadas:
- Azure AI Search
- Azure OpenAI
- Python 3.x
- PyPDF2
- python-dotenv

### Agradecimientos:
- Equipo de Azure
- Comunidad de Python
- OpenAI

---

*Documento generado el 22 de Agosto de 2024*
*Versión 1.0*