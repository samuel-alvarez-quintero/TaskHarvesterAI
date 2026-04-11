# TaskHarvester - Requerimientos del Sistema

## 1. Requerimientos Funcionales

### 1.1 Ingesta de Emails

- RF-01: El sistema debe permitir configurar una o múltiples cuentas IMAP.
- RF-02: El sistema debe realizar una sincronización inicial de correos en lotes.
- RF-03: El sistema debe evitar duplicados mediante identificación única (UID).
- RF-04: El sistema debe ejecutar sincronización incremental periódica.
- RF-05: El sistema debe permitir configurar el intervalo de polling.

---

### 1.2 Filtros Previos a Persistencia (CRÍTICO)

- RF-06: El sistema debe aplicar filtros antes de guardar emails en base de datos.
- RF-07: El sistema debe descartar correos según reglas configurables:
  - remitentes ignorados
  - palabras clave (spam/noise)
  - dominios no relevantes
- RF-08: El sistema debe filtrar correos vacíos o sin contenido útil.
- RF-09: El sistema debe permitir listas blancas (whitelist).
- RF-10: El sistema debe permitir listas negras (blacklist).
- RF-11: El sistema debe limitar tamaño máximo del email a procesar.

---

### 1.3 Persistencia de Emails

- RF-12: El sistema debe almacenar emails en base de datos con estado inicial `pending`.
- RF-13: El sistema debe registrar:
  - contenido
  - origen
  - fecha
  - identificador externo (UID)
- RF-14: El sistema debe manejar estados:
  - pending
  - processing
  - done
  - error

---

### 1.4 Gestión de Cola

- RF-15: El sistema debe procesar emails en lotes configurables.
- RF-16: El sistema debe priorizar emails recientes.
- RF-17: El sistema debe permitir reintentos en caso de error.
- RF-18: El sistema debe marcar errores definitivos tras múltiples fallos.

---

### 1.5 Procesamiento de Adjuntos

- RF-19: El sistema debe detectar el tipo de adjunto por MIME.
- RF-20: El sistema debe extraer texto de:
  - PDF
  - imágenes (OCR con Ollama)
  - DOCX
- RF-21: El sistema debe aplicar OCR a PDFs escaneados.
- RF-22: El sistema debe ignorar adjuntos no relevantes.
- RF-23: El sistema debe evitar reprocesar adjuntos repetidos (hash).

---

### 1.6 Normalización

- RF-24: El sistema debe limpiar el contenido:
  - eliminar firmas
  - eliminar respuestas encadenadas
- RF-25: El sistema debe truncar textos largos.
- RF-26: El sistema debe unificar el contenido en formato estándar.

---

### 1.7 Procesamiento con IA

- RF-27: El sistema debe enviar texto limpio al modelo de IA.
- RF-28: El sistema debe extraer tareas accionables.
- RF-29: El sistema debe asignar prioridad:
  - low
  - medium
  - high
- RF-30: El sistema debe generar salida en JSON válido.
- RF-31: El sistema debe validar el JSON generado.
- RF-32: El sistema debe reintentar en caso de error.
- RF-33: El sistema debe usar fallback entre modelos:
  - principal: llama3
  - secundario: Qwen

---

### 1.8 Persistencia de Tareas

- RF-34: El sistema debe almacenar tareas generadas.
- RF-35: El sistema debe relacionar tareas con su email origen.
- RF-36: El sistema debe mantener historial de procesamiento.

---

### 1.9 CLI (TaskHarvesterAI)

- RF-37: El sistema debe permitir ejecutar sincronización manual.
- RF-38: El sistema debe permitir procesar la cola manualmente.
- RF-39: El sistema debe mostrar estado del sistema.
- RF-40: El sistema debe permitir listar tareas.
- RF-41: El sistema debe permitir marcar tareas como completadas.

---

### 1.10 API + APP (TaskHarvesterAPP)

- RF-42: El sistema debe exponer API para gestión de tareas.
- RF-43: El sistema debe permitir visualizar tareas.
- RF-44: El sistema debe permitir editar tareas.
- RF-45: El sistema debe permitir marcar tareas como completadas.
- RF-46: El sistema debe soportar gestión futura de clientes y proyectos.

---

## 2. Requerimientos No Funcionales

### 2.1 Rendimiento

- RNF-01: El sistema debe procesar emails en lotes para evitar sobrecarga.
- RNF-02: El sistema debe limitar concurrencia de procesamiento.
- RNF-03: El sistema debe limitar ejecución concurrente de modelos de IA.

---

### 2.2 Escalabilidad

- RNF-04: El sistema debe soportar miles de emails iniciales sin bloqueo.
- RNF-05: El sistema debe permitir crecimiento progresivo del volumen de datos.
- RNF-06: El sistema debe permitir añadir nuevos workers.

---

### 2.3 Disponibilidad

- RNF-07: El sistema debe tolerar fallos en procesamiento.
- RNF-08: El sistema debe permitir reanudar procesos interrumpidos.

---

### 2.4 Seguridad

- RNF-09: El sistema debe proteger credenciales mediante variables de entorno.
- RNF-10: El sistema no debe exponer datos sensibles en logs.
- RNF-11: El sistema debe permitir autenticación en la API.

---

### 2.5 Mantenibilidad

- RNF-12: El sistema debe estar modularizado (ingesta, procesamiento, API).
- RNF-13: El sistema debe permitir configuración sin modificar código.
- RNF-14: El sistema debe ser reproducible en entorno local.

---

### 2.6 Observabilidad

- RNF-15: El sistema debe generar logs de:
  - ingesta
  - procesamiento
  - errores
- RNF-16: El sistema debe permitir monitorear:
  - tamaño de cola
  - tiempos de procesamiento

---

### 2.7 Privacidad

- RNF-17: El sistema debe permitir procesamiento local usando Ollama.
- RNF-18: El sistema debe evitar enviar datos sensibles a servicios externos.

---

## 3. Notas de Diseño

- El sistema debe priorizar simplicidad y control sobre automatización compleja.
- El procesamiento debe ser desacoplado de la ingesta.
- El LLM debe operar únicamente sobre texto limpio.
- Los filtros previos son obligatorios para evitar ruido y reducir costos de procesamiento.
