# Horizonte: hasta dónde pueden llegar Amatista, G7B y Geoda

Fecha: 2026-11-01. Una lectura realista por etapas, con lo que hace falta para pasar de una a otra y dónde está el techo. Las definiciones de cada término están en [FICHAS_TECNICAS.md](../FICHAS_TECNICAS.md).

## 1. Las tres etapas

### H1 · Prueba de concepto (los próximos 3 meses)

**Meta:** demostrar que los datos medidos cambian la experiencia en un equipo modesto.

| Entregable | Se considera logrado cuando |
|---|---|
| Cubo con Blender Open Data y la sonda | Hay celdas confiables (5 muestras o más de 3 equipos o más) para N2, N3 y N4 |
| Sonda de operaciones en GitHub Actions | Curvas de costo de 3 o 4 operaciones en 4 arquitecturas |
| `perfiles.json` v1 en Amatista para Blender | El add-on detecta el nivel y aplica el perfil |
| **La prueba con personas** | En una PC N1 o N2, 5 personas terminan una práctica que sin el perfil no terminaban, o la terminan más rápido |
| Dataset v1 publicado con DOI (GitHub Releases + Zenodo) | Citable y descargable |

**Requiere:** el enlace de Blender Open Data, correr la sonda en tus equipos y cinco personas.

### H2 · Producto (de 6 a 12 meses)

**Meta:** que el planificador decida por operación y que haya una comunidad que mide.

| Entregable | Se considera logrado cuando |
|---|---|
| Modelo de costos | Error menor al 25 % en equipos que no vio al entrenar |
| Planificador por operación | Decide local, otra PC de la red (por ejemplo, la granja de la escuela con Flamenco) o la nube |
| Editor web adaptativo (N0) | Funciona en celulares reales probados con BrowserStack |
| Segundo programa en el Corazón | Una misma práctica validada en Blender y en Godot |
| Telemetría universitaria (T3) | Al menos un laboratorio con permiso y mediciones |
| Primeros ingresos | Certificación validada o una licencia para una escuela |

**Requiere:** H1 cumplido, acuerdos con la universidad (el programa Campus Experts ayuda) y usuarios en Amatista.

### H3 · Plataforma (de 1 a 3 años)

**Meta:** la distribución abierta del 3D.

| Entregable | Qué sería |
|---|---|
| Distribución Amatista 3D | Un Linux ligero con Blender en la versión adecuada, Godot, FreeCAD, Krita, Geoda y los cursos sin conexión |
| Cobertura de Maya y 3ds Max | Cobertura ponderada del 50 % o más del catálogo de tareas |
| Dataset de referencia | El conjunto de datos de usabilidad 3D en equipos modestos más citado de la región |
| Comunidad | Personas externas que contribuyen mediciones, prácticas y adaptadores |
| Sostenibilidad | Licencias institucionales, patrocinios (GitHub Sponsors) y fondos para software libre o educación |

## 2. El techo: lo que no va a pasar con estos recursos

| No | Por qué |
|---|---|
| Un programa que compita con Blender, Maya o 3ds Max | Son décadas de trabajo de equipos grandes; Geoda los usa, no los reemplaza |
| Blender completo dentro del navegador | Portarlo es trabajo de un equipo durante años; el editor web cubre N0 y N1 |
| Un motor de render propio | Cycles, EEVEE, Embree y Open Image Denoise ya existen y son libres |
| Entrenar una IA generativa propia | Cuesta miles de horas de GPU; se usan modelos existentes |
| Big data de millones de mediciones sin usuarios | La nube gratuita da miles al mes; los millones llegan con usuarios midiendo sus propios equipos |

## 3. Lo que hace único al conjunto

1. **Datos de usabilidad, no solo de render**, en equipos modestos y versiones viejas, abiertos y citables.
2. **Un planificador que decide con esos datos**, dentro de las herramientas libres.
3. **Enseñanza conectada:** las prácticas de Amatista se adaptan al equipo de cada persona.
4. **Libre, en español y sin depender de internet.**

Las piezas sueltas existen en otros lados. La combinación, no la encontramos (reporte de propuestas, sección 3).

## 4. Riesgos que pueden frenar el horizonte

| Riesgo | Respuesta |
|---|---|
| Una sola persona con muchos frentes | Una etapa a la vez; máximo 3 tareas en progreso |
| Los créditos vencen (Azure, Heroku, el estatus de estudiante) | Controladores intercambiables; activar cada crédito solo cuando una fase lo necesita |
| Blender cambia su API | El adaptador aísla los cambios; pruebas por versión |
| Pocos datos de N1 | Buscar equipos viejos a propósito (laboratorios, donaciones); no afirmar sin datos |
| Que no haya usuarios | H1 depende de 5 personas; sin ellas no hay prueba |

## 5. La señal para seguir o cambiar de rumbo

Al final de H1, una sola pregunta decide:

> ¿Los datos medidos cambiaron algo **medible** para una persona con un equipo modesto?

- **Sí:** se pasa a H2 con evidencia para universidades, patrocinadores y fondos.
- **No:** se revisan la sonda, los niveles y los perfiles antes de construir más.
