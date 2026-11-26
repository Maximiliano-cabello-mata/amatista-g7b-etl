# Coordinación de los repositorios de Amatista

Cada repositorio muestra en **Actions → Coordinación entre repositorios → seguimiento → Summary** la última integración de cada rama predeterminada, las propuestas abiertas y los archivos que cambian en más de una propuesta dirigida a la misma rama. La comprobación indica por separado los conflictos de fusión que GitHub confirma. Una coincidencia de archivos es un motivo para revisar ambos cambios juntos.

Los repositorios públicos muestran la actividad pública de G7B, el motor, la API y Amatista IA. El [informe de la web](https://github.com/Maximiliano-cabello-mata/amatista-recuperada-20261106/actions/workflows/coordinacion.yml) añade la plataforma privada. Para una propuesta, los valores del consumidor local provienen del checkout que GitHub está probando. El resto corresponde a las revisiones oficiales que identifica el resumen.

La comprobación falla si una revisión fijada es ilegible, si queda fuera de la rama oficial del productor, si web y API divergen o si GitHub devuelve datos incompletos. Los conflictos de otras propuestas se muestran como avisos. En la web se prueba además el archivo de agregados publicado por G7B con los lectores de la API y del frontend. Las pruebas de cada repositorio siguen evaluando su propio código.

Al preparar un cambio de contrato, enlazar el PR del productor y el de cada consumidor, declarar las versiones de entrada y salida y adjuntar una ejecución con ambos lectores. Mantener compatibilidad con la revisión desplegada durante la transición. Una revisión nueva de la acción compartida se incorpora en los consumidores por SHA completo después de verificarla.

## Propuestas del cubo

[#26](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/pull/26) y [#27](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/pull/27) modifican el constructor, el descargador, el publicador de estado, sus pruebas y el contrato documentado. La segunda propone una tabla canónica y retira dos archivos Parquet. La primera añade clases de hardware, comparaciones relativas y un paquete para Geoda. El número de versión por sí solo no acredita compatibilidad entre esas ramas.

Mantener el contrato vigente mientras se decide. Comparar las dos propuestas con una misma muestra congelada. Verificar filas y unidades, vistas y Parquet, apertura por los lectores actuales y anteriores, y conservación de la última publicación válida al revertir. Si Geoda necesita una vista de la propuesta, llevarla en un cambio acotado sobre la base aprobada con esta misma prueba. La base oficial reserva al responsable la elección del cambio de estándar.
