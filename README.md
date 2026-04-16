# TaskHarvesterAI

Motor local de IA para ingesta, procesamiento y extracción automática de tareas desde emails y adjuntos, operado mediante CLI.

---

## Características

- Ingesta de emails vía IMAP
- Sincronización inicial y incremental
- Cola persistente con SQLite
- Procesamiento por lotes
- Extracción de texto desde:
  - PDFs
  - Imágenes (OCR)
  - DOCX
- Normalización de contenido
- Extracción de tareas mediante IA
- CLI para operación manual
- Procesamiento local con Ollama

---

## Documentación

- [Diagrama de flujo](./docs/flowchart.md)
- [Especificación de requerimientos](./docs/SRS.md)

---

## Instalación y ejecución

1. Instala dependencias:
  pip install -r requirements.txt
2. Ejecuta ingesta de correos no leídos:
  python -m scripts.fetch_emails
3. Procesa mensajes en cola:
  python scripts/process_messages.py
4. Clasifica mensajes con IA:
  poetry run taskh filter --spam --phishing --malware
5. Ingesta de correos con etiquetas AI:
  poetry run taskh fetch --filter --spam --phishing --malware

---

## Modelos soportados

- Principal: llama3
- Fallback: Qwen

---

## Flujo de procesamiento

1. Ingesta IMAP (lotes)
2. Filtros previos
3. Persistencia en SQLite
4. Worker procesa batch
5. Extracción de adjuntos (OCR si aplica)
6. Normalización
7. LLM → tareas
8. Persistencia final

## Principios de diseño

- Procesamiento desacoplado
- Control de concurrencia
- Backpressure
- LLM solo sobre texto limpio
- Privacidad local

## Limitaciones actuales

- No soporte directo para WhatsApp
- OCR limitado por calidad de imagen
- Dependencia de calidad del prompt

## Roadmap

- Soporte multi-cuenta
- Dataset para fine-tuning
- Mejora de detección de proyectos/clientes
- Integración con API externa
