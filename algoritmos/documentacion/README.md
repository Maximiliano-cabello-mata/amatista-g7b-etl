# Selección documental v3

Esta ficha describe la versión 3. Para el despliegue vigente de sitios, consulta [Site 4.1](site-4.md). El recorrido por inventario de `blender_docs` sigue usando este clasificador.

El identificador público de Zyte para sitios es **paginas**. **blender_docs** usa el inventario Sphinx del manual y el mismo clasificador de bloques. El cargador de Scrapy registra esos dos nombres. Los trabajos previos siguen identificados por su clave de Zyte. [Código histórico de paginas](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/blob/0f870b2fabab07ca29025230c7bdb864cc1505d5/motor_extraccion/spiders/paginas.py) · [Prototipo y ocho recorridos del PR 29](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/pull/29).

## Eventos y decisiones

Se reserva un intento antes de despachar cada URL de sitios. Respuestas, errores y redirecciones devuelven el control a una única frontera. Robots, alcance, presupuesto y profundidad se respetan antes de la siguiente descarga. El manual mantiene su recorrido por inventario. En modo de metadatos se conserva únicamente la salida de metadatos.

Un bloque pertenece a un apartado y a una versión. El modelo conserva la cita, posición, destino propuesto y señales observadas. El vocabulario español/inglés, los objetivos curriculares iniciales y las expresiones observables están versionados en el clasificador.

$$G=R\max(C,V),\qquad E=L A O$$

$R$ exige un término técnico y una expresión de efecto. $C$ identifica una condición y $V$ una versión numérica declarada. $L$ es la correspondencia con un objetivo configurado, $A$ una acción y $O$ una comprobación observable. Son aproximaciones léxicas: una negación, un sinónimo o una definición extensa pueden producir un error. Un bloque desconocido queda en revisión. La evidencia de foros identificados se etiqueta como hipótesis. Un índice puede aportar enlaces. La información general reconocida se descarta del texto destinado al corpus y permanece auditable en bronce.

La novedad exacta durante el trabajo compara la huella de fuente, programa, versión, jerarquía y estructura del bloque. Una nueva URL para la misma huella conserva la referencia. Para tablas de dos columnas se registran valores que discrepan bajo la misma clave y contexto. En plata continúa la deduplicación del sistema entre trabajos. Las paráfrasis y las contradicciones en prosa requieren revisión.

## Prioridad y gradiente discreto

Para el ancla $A$, ruta $P$, encabezado $H$ y temas $T$, $J(X,T)=|X\cap T|/|X\cup T|$ y vale cero si la unión está vacía. A profundidad $d$:

$$s=0.85^{\max(0,d-1)}(0.60J(A,T)+0.25J(P,T)+0.15J(H,T))$$

En cada página evaluable se observa $y_t$, la fracción de bloques nuevos evaluables clasificados como candidatos. Se usa la pérdida cuadrática $\ell=(m-y_t)^2/2$ y se actualiza $m$ con el gradiente descendente:

$$m_0=0.5,\quad g_t=y_t-m_{t-1},\quad m_t=m_{t-1}+0.25g_t,\quad S=0.85s+0.15m_t$$

Las páginas compuestas solo por referencias o navegación no actualizan $m$. La realimentación influye en los enlaces recién descubiertos. No certifica la corrección de las decisiones. Los mismos eventos, semillas y contenido en el mismo orden producen las mismas decisiones. Los resultados sintéticos del PR 29 orientan la elección de foco simple. La incorporación del gradiente requiere evaluación en sitios reales.

## Objetivo de utilidad del 80 %

La unidad etiquetada es un candidato con cita. El auditor verifica si responde una pregunta técnica o logra el objetivo educativo indicado, conservando condición y efecto correctos. Se selecciona un candidato por página antes de etiquetarlo. Para habilitar una fuente se necesita una muestra representativa de sus ámbitos, versiones y tipos de documento. Un piloto concentrado en un solo capítulo se informa por separado. También conviene muestrear descartes para estimar lo útil que se pierde.

Sea $n$ el total revisado y $k$ el útil, $\hat p=k/n$. Para autorizar la publicación automática se exige $L\geq0.80$ con el límite inferior unilateral de Wilson al 95 %, $z=1.64485$:

$$L=\frac{\hat p+z^2/(2n)-z\sqrt{\hat p(1-\hat p)/n+z^2/(4n^2)}}{1+z^2/n}$$

Con cero observaciones la puerta queda cerrada. Ejemplos de cálculo: 8 de 10 no alcanzan el criterio, 19 de 20 sí lo alcanzan para una muestra representativa. Una auditoría del modelo y fuente se registra en **auditoria.json**, una lista de filas con modelo, fuente, id del candidato, url, revisor y util (booleano). Se rechazan páginas repetidas. Desde la raíz se puede ejecutar **python -m g7b_ingesta.calidad_documental**. Solo las fuentes habilitadas pueden pasar de candidato a oro, y aún deben pasar el embudo. Los lotes afectados se reconsideran si cambia su habilitación. Los registros anteriores al modelo conservan su tratamiento histórico.

## Relevo y verificación

El despliegue comparte el candado de GitHub Actions con el radar, espera a que se vacíe la cola incompatible, despliega con shub y consulta las arañas de la misma versión remota. Ejecuta un único trabajo de verificación con datos reales del manual. El piloto del modelo tiene un máximo de 32 intentos documentales. La comprobación posterior usa una página cuando ya existe un piloto terminado con ítems. Se verifica la firma documental/3.0, que llegaron candidatos y el inventario de trabajos activos. La traza conserva la clave del trabajo, cantidades y muestras citables.

[API de trabajos de Zyte](https://docs.zyte.com/scrapy-cloud/usage/reference/http/jobs.html) · [Referencia del cliente de Zyte](https://python-scrapinghub.readthedocs.io/en/stable/ref/apidocs.html).
