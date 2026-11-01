# Reporte: qué propuestas son realistas y hacia dónde va el proyecto

Fecha: 2026-11-01. Revisa todas las propuestas que salieron en la conversación del día (incluido el documento externo "Arquitectura Autónoma y Refactorización"), con un veredicto para cada una. Es una opinión técnica para decidir; lo que se decida se anota en `docs/PLAN.md`.

**Escala:**
- **Realista:** se puede con lo que hay (una persona, capas gratuitas, créditos de estudiante).
- **Realista con condición:** depende de algo que todavía no existe (usuarios, acuerdos, datos).
- **Reformulada:** la idea original no es viable, pero una versión más acotada sí.
- **No realista:** ni acotándola, con los recursos actuales.

## 1. Resumen en una tabla

| # | Propuesta | Veredicto | En una línea |
|---|---|---|---|
| 1 | Una aplicación 3D propia, "el Linux del 3D", como programa nuevo o fork de Blender | **No realista** | Blender son ~30 años de trabajo de una fundación; un fork se queda atrás en meses |
| 2 | Una distribución abierta del 3D: herramientas libres + capa propia (Corazón) + conocimiento (G7B) | **Realista a largo plazo** | Ya tiene base: plantilla Blender Amatista, add-on y Corazón |
| 3 | Un motor propio súper optimizado que haga el 60-70 % de Blender en hardware débil | **Reformulada** | Lo pesado (render, simulación) lo es por naturaleza. Sí: perfiles medidos que adaptan Blender al equipo |
| 4 | Dejar extracción de "big data" corriendo 3 meses sola | **No realista** (y mala idea) | Da basura y gasta créditos. Sí: trabajos programados con embudo y revisión (ya hecho) |
| 5 | Data warehouse | **Realista en parte** | Sí para mediciones y telemetría (Parquet y DuckDB); no para texto, que va al lago y a la búsqueda |
| 6 | Centralizar todo el conocimiento del 3D (diseño, animación, videojuegos) | **Reformulada** | "Todo" no. Sí: un recorrido vertical "del modelo al videojuego" (Blender → glTF → Godot), y después animación |
| 7 | Aprender de las técnicas de las grandes empresas (Rockstar y otros) | **Realista con límites** | Solo lo que publican (SIGGRAPH, GDC, laboratorios); nunca código filtrado ni bajo contrato |
| 8 | Emular el 50 % de Maya y 3ds Max "sin que se vea obvio" | **Reformulada y realista** | No es un clon: cobertura ponderada de tareas reales, con equivalencias, add-ons libres y presets |
| 9 | Telemetría de computadoras viejas y potentes | **Realista con condición** | Hoy: internet, tus PCs y la nube. Universidades y granjas de render: cuando haya acuerdos |
| 10 | Telemetría generada por una IA a partir de prompts | **No es telemetría** | Sirve como dato sintético para probar código; nunca se mezcla con mediciones |
| 11 | Entrenar una IA de modelado con los créditos de Colab | **No realista** | Entrenar cuesta miles de horas de GPU. Sí: un modelo existente con MCP (BlenderMCP ya existe) y el conocimiento de G7B |
| 12 | Un motor de IA que arme prácticas conectado a un programa potente | **Realista después** | Solo si G7B mejora las respuestas (prueba de F2); las prácticas que genere, una persona las revisa |
| 13 | Varias nubes gratuitas al mismo tiempo | **Realista** | Con un controlador por servicio, para cambiar de proveedor cuando venzan créditos |
| 14 | Plan original de Azure: App Service para FastAPI, VMs para IA, Blob para `.glb` | **Descartado** | Duplicaba Oracle y mezclaba Amatista con G7B; Azure quedó como lago (ya funciona) |
| 15 | Propuesta externa: limpieza, araña estructurada, Mongo idempotente, despliegue a Zyte | **Adoptada en parte** | 6 puntos adoptados y 4 errores corregidos; Clerk, Heroku para Amatista y Azure para `.glb`, no |
| 16 | G7B como servidor MCP para que Claude y otras IA lo consulten | **Realista, prioridad alta** | Convierte los datos en ayuda concreta para programar add-ons y adaptadores |
| 17 | Sonda de rendimiento propia | **Realista: v0 hecha** | Falta probarla con ventana y con GPU en una computadora real |
| 18 | Perfiles de equipo que el add-on aplica solo | **Realista: la apuesta principal** | Es la pieza que no encontramos en ningún otro proyecto (sección 3) |
| 19 | Ganar dinero sin dejar de aportar a la comunidad | **Realista con condición** | Conocimiento abierto y servicios de pago (certificación validada, licencias para escuelas). Requiere usuarios |
| 20 | Proteger el proyecto de que un "Red Hat" crezca a costa tuya | **Realista** | GPL/AGPL para el código, registro de la marca "Amatista" y ser la fuente oficial |

## 2. Detalle de las propuestas más importantes

### 1 y 2. El "Linux del 3D"

- **No realista:** un programa 3D nuevo, o un fork de Blender mantenido por una persona. Blender cambia cada pocos meses; un fork se queda atrás y consume todo el tiempo.
- **Realista:** lo que Linux fue de verdad. Integrar piezas libres sin modificarlas y ponerles una capa propia encima. Esa capa ya existe en partes: la plantilla Blender Amatista (sin recompilar), el add-on GPL y el Corazón (`amatista.corazon/1`), con adaptadores y ramas. Lo que falta es probar que el contrato sirve para un **segundo programa real** (Godot o FreeCAD).
- **Señal de éxito:** una misma práctica validada en Blender y en Godot con el mismo contrato.

### 3 y 18. Hardware modesto

- **No realista:** un motor que haga barato lo que es caro por naturaleza (render con trazado de rayos, simulaciones).
- **Realista y nuevo:** medir qué tan usable es Blender en computadoras modestas y aplicar solo el perfil que funciona. La búsqueda del día no encontró ningún conjunto de datos de la vista 3D y la edición en gráficas integradas y versiones viejas de Blender. Blender Open Data y las reseñas de hardware miden el render con tarjetas dedicadas.
- **Condición:** sin mediciones reales, la idea no existe. Hoy hay **una** medición (un servidor sin GPU).

### 4 y 5. Big data y warehouse

- La escala real del conocimiento útil es de **gigabytes**. Solo los modelos 3D llegarían a terabytes, y no se necesitan para el objetivo.
- Lo construido hoy es el enfoque correcto: trabajos programados, un lago crudo, un embudo con motivos y revisión humana. El warehouse aplica a las mediciones (modelo en estrella del plan, sección 7.4) y todavía no tiene datos.

### 7 y 8. La industria, Maya y 3ds Max

- **Legal y realista:** estudiar técnicas publicadas e implementarlas con código propio, y documentar equivalencias. Las ideas no tienen derechos de autor; el código, los textos, las marcas y algunas patentes sí.
- **El 50 %** se mide como **cobertura ponderada por uso** de un catálogo de unas 100 tareas reales. Hasta que exista ese catálogo (F3), "50 %" no es un número, es un deseo.

### 9 a 12. Telemetría e IA

- La telemetría de personas es lo más valioso a largo plazo, pero **depende de pláticas** con profesores y laboratorios (plan, sección 5.5). La telemetría por prompts no cuenta.
- Para la IA, lo realista es este orden: primero el servidor MCP con el conocimiento de G7B, después la prueba de las 20 preguntas, y solo entonces un tutor o un motor que arme prácticas. Entrenar un modelo propio no está a nuestro alcance.

### 19 y 20. Dinero y protección

- **Modelo realista:** conocimiento abierto (lecciones básicas, G7B, el formato de prácticas) y servicios de pago. Los servicios: certificación validada (el motor comprueba que la persona sí lo hizo en Blender), licencias para escuelas y universidades, y patrocinios. **Nada de esto funciona sin usuarios.**
- **Protección:** con GPL o AGPL nadie puede cerrar el código; con la marca registrada nadie puede usar el nombre "Amatista". No se puede impedir que otros ganen dinero con software libre, y no hace falta.

## 3. Lo que de verdad es nuevo

Una revisión rápida de lo que ya existe (anuncios y repositorios públicos; no se revisó código cerrado):

| Ya existe | Lo que lo hace |
|---|---|
| Prácticas guiadas que revisan la escena dentro de Blender | Add-ons comerciales como Blender SkillUp, Blender Coach y Blender Training Kit |
| Una IA que maneja Blender | BlenderMCP y servidores parecidos |
| Búsqueda sobre documentación | Muchos proyectos |
| Benchmarks de render | Blender Open Data, reseñas con tarjetas dedicadas |

| No encontrado: lo propio del proyecto |
|---|
| Mediciones de **usabilidad** (vista 3D, edición) en hardware modesto y en versiones viejas de Blender |
| El ciclo **medir → perfil → aplicar → volver a medir**, dentro del add-on |
| Todo esto **libre, en español, sin conexión y gratuito**, con un contrato pensado para varios programas |

**Conclusión:** la tecnología no es nueva; la combinación sí, y tiene una pieza original. Esa pieza todavía no tiene datos.

## 4. Hacia dónde apunta el proyecto

> **Que cualquier persona pueda aprender y trabajar 3D con herramientas libres, con una experiencia que se adapta a la computadora que tiene, en español y sin depender de internet.**

- **Amatista enseña:** cursos, prácticas validadas y progreso.
- **Blender Amatista y el Corazón son el puente** con las herramientas: guían, validan y ajustan.
- **G7B sabe y mide:** conocimiento con fuente y licencia, y mediciones por equipo.

## 5. Recomendación de rumbo

1. **Frenar el crecimiento a lo ancho.** No hay proveedores nuevos, fuentes nuevas ni versiones nuevas del motor hasta cumplir el punto 2. La infraestructura de hoy alcanza para meses.
2. **La prueba que define el proyecto,** en 2 a 3 semanas:
   > Una PC modesta, una práctica de Amatista y cinco personas. Con el perfil que eligen los datos medidos, ¿terminan la práctica que sin el perfil no podían, o la terminan más rápido?

   Para llegar ahí:
   - correr la sonda en 2 o 3 equipos;
   - hacer `perfiles.json` v0;
   - agregar al add-on el botón "Ajustar a mi equipo" (I0 de la [investigación de integración](../investigacion/2026-11-01_integracion_amatista_g7b.md));
   - conseguir cinco personas.
3. **En paralelo y con fecha:** la prueba de las 20 preguntas con el servidor MCP (F2). Si no mejora las respuestas, se deja de extraer documentos.
4. **Lo demás espera a esos dos resultados:** la distribución, Maya y 3ds Max, el tutor con modelo y el segundo programa.

## 6. Decisiones que te tocan

| Decisión | Recomendación |
|---|---|
| Licencia del código de G7B | AGPL-3.0 |
| Licencia de los datos publicados | CC BY 4.0, o CC0 para los perfiles, así Amatista los incluye sin trámite |
| Versiones de referencia de Blender | 5.2 LTS, 4.5 LTS y 3.6 LTS, más 2.93 para equipos viejos |
| ¿El add-on cambia ajustes solo? | La primera vez pregunta y muestra qué cambia |
| ¿Quién paga primero: alumnos o escuelas? | Pendiente: define qué se construye después de la prueba |
| Registro de la marca "Amatista" | Antes de buscar socios o patrocinios |
