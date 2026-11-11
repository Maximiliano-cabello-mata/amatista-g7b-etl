# Consentimiento de telemetría de Amatista para Blender · BORRADOR

> **Borrador para revisión del responsable. No está en uso.** Ningún complemento publicado recoge estos datos todavía. Antes de activarlo hay que revisar este texto con alguien que conozca la ley de protección de datos aplicable, sobre todo porque muchos alumnos son menores de edad.

## Principios

1. **Voluntario y apagado por defecto.** Si el alumno no responde, no se envía nada.
2. **Amatista funciona igual** con o sin telemetría. Nada se bloquea ni se degrada por decir que no.
3. **Sin datos personales.** Se mide el equipo y Blender, no a la persona.
4. **Se puede cambiar de opinión** cuando se quiera, desde las preferencias del complemento.
5. **Lo que se envía se puede ver antes de enviarlo.**

## El texto que vería el alumno

> ### ¿Nos ayudas a mejorar Amatista?
>
> Amatista quiere que aprender 3D no dependa de tener una computadora cara. Para lograrlo necesitamos saber cómo corre Blender en equipos reales como el tuyo.
>
> **Si aceptas, tu Blender nos enviará:**
>
> - Cómo es tu equipo: sistema operativo, modelo del procesador y número de núcleos, memoria RAM (redondeada) y tarjeta gráfica.
> - Qué versión de Blender y de Amatista usas.
> - Qué tan rápido trabaja Blender en tu equipo: cuadros por segundo y tiempos de algunas operaciones.
> - En qué paso de una práctica hubo un error del programa, para poder corregirlo.
>
> **Nunca enviamos:**
>
> - Tu nombre, tu correo ni tu cuenta.
> - El nombre de tu computadora ni tu nombre de usuario.
> - Tus archivos, tus modelos ni lo que hay en tus escenas.
> - Tu ubicación.
>
> Los datos se guardan sin relacionarlos contigo y se usan solo para mejorar Amatista y Geoda, la parte que ajusta Blender a cada equipo. Los resultados agregados pueden publicarse (por ejemplo: «en equipos con 4 GB de RAM, este ajuste da 24 cuadros por segundo»).
>
> **Puedes usar Amatista exactamente igual si dices que no**, y puedes cambiar tu respuesta cuando quieras en *Preferencias › Amatista › Privacidad*.
>
> Si eres menor de edad, pregunta a tu mamá, papá o tutor, o a tu profesor, antes de aceptar.
>
> [ **Sí, quiero ayudar** ]   [ **No, gracias** ]   [ Ver exactamente qué se envía ]

## Qué se envía, campo por campo

Es lo mismo que ya mide la [sonda](../sonda/LEEME.md), más el contexto mínimo de la práctica.

| Dato | Ejemplo | Para qué |
|---|---|---|
| Sistema operativo y versión | `Windows 11` | Agrupar equipos comparables |
| Modelo de CPU y núcleos | `Intel Core i3-7100U`, 4 | Nivel del equipo (N0 a N4) |
| RAM redondeada | `4 GB` | Nivel del equipo |
| GPU que ve Blender | `Intel HD Graphics 620` | Qué motores de render sirven |
| Versión de Blender y del complemento | `4.2.3`, `7.1.0` | Compatibilidad |
| Mediciones de rendimiento | cuadros por segundo, segundos | Los perfiles de Geoda |
| Práctica y paso donde falló el programa, con el código del error | `blender.bp.m1.tren`, `motor.registrar_intento.error_interno` | Corregir fallas |
| Identificador de instalación | Un número al azar creado por el complemento | Contar equipos distintos y no medir dos veces el mismo. No sale de la cuenta ni del equipo, y se puede regenerar |

## Qué no se envía

Nombre, correo, identificador de cuenta, nombre del equipo, nombre de usuario del sistema, rutas de archivos, nombres de archivos, contenido de escenas, capturas de pantalla, dirección IP guardada, ubicación.

## Decisiones que tiene que tomar el responsable

| # | Decisión | Opciones | Recomendación |
|---|---|---|---|
| 1 | Identificador de instalación | Usar uno al azar, o no usar ninguno | Usarlo, regenerable. Sin él no se puede saber si 100 mediciones son de 100 equipos o de uno |
| 2 | Menores de edad | Bastar con el aviso, o exigir que lo active el profesor o un tutor | Revisarlo con asesoría legal. En escuelas, que la autorización la dé la escuela o el tutor |
| 3 | Datos de la práctica | Solo errores del programa, o también cuánto tarda y en qué se equivoca el alumno | Empezar solo con errores. Lo otro describe a la persona, no al equipo, y cambia la naturaleza del consentimiento |
| 4 | Dónde se reciben | En la API de Amatista, que los reenvía sin datos de cuenta, o directo al buzón de Azure | Por la API: un solo punto que controlar y la dirección IP nunca llega al lago |
| 5 | Cuánto tiempo se guardan | — | Definir un plazo para lo crudo y conservar solo los agregados |

## Cómo se construiría

No está construido. El orden propuesto, una vez aprobado el texto:

1. **Complemento** (`amatista-motor-`): la pregunta la primera vez, la preferencia en *Privacidad* y el botón «Ver exactamente qué se envía». Apagado por defecto. Las pruebas comprueban que sin un «sí» no sale ninguna petición.
2. **API** (`amatista-api-`): una ruta en la API de datos que recibe la medición, descarta todo lo que no esté en la tabla de arriba y no guarda la dirección IP.
3. **G7B** (este repositorio): la medición entra al lago por el mismo embudo que la sonda y llega al cubo.

Depende de que el flujo esté funcionando: ver el [estado del flujo](reportes/2026-11-11_estado_del_flujo.md).
