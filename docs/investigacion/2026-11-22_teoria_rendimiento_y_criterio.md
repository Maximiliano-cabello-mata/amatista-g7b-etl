# Teoría de rendimiento y criterio automático de mediciones (22 de noviembre de 2026)

Dos herramientas construidas sobre los datos que alimentan el cubo:
- la **teoría de rendimiento** predice cuántas samples/min logra cualquier combinación de dispositivo, versión de Blender y escena, aunque nadie la haya medido;
- el **criterio automático** juzga cada medición contra sus pares y contra la teoría.

Las dos se validaron antes de usarlas.

**Estado: investigación.** El código está en [`analisis/teoria_rendimiento/`](../../analisis/teoria_rendimiento/). **No forma parte del flujo de G7B** ni escribe en el lago o en el cubo. Según la [base oficial de Amatista](https://github.com/Maximiliano-cabello-mata/amatista-recuperada-20261106/blob/recuperacion/BASE.md):
- la teoría entra al cubo (`v_teoria`) solo si Geoda la necesita en la prioridad 3;
- el criterio de mediciones es parte de Amatista IA, el auditor, y usarlo en el cubo depende de la decisión pendiente del estado «corroborado».

## 1. Datos

- **Fuente:** el snapshot público de Blender Open Data (CC0) del 22 de noviembre de 2026, convertido con el **mismo código que alimenta el lago**: `g7b_telemetria.capturar.opendata` y el estándar `g7b.hardware/1`.
- **1,050,137 mediciones válidas** de 3,421 dispositivos (dispositivo + backend), 17 versiones (3.0–5.3) y 3 escenas (classroom, junkshop, monster).
  - Otras 87,848 tienen un esquema anterior a v4 y se descartan, igual que en el lago.
  - Se excluyen las corridas con varias GPU y las versiones alfa, beta o rc.
- **56,458 combinaciones medidas** de unas 174,000 posibles: **el 68 % nunca se midió**.

## 2. La teoría de rendimiento

### Modelo

Aditivo en escala logarítmica, porque los rendimientos se multiplican:

```
log(samples/min) = base + dispositivo + versión + escena + (backend × versión) + (backend × escena)
```

- **Se ajusta por retroajuste** sobre la mediana de cada combinación medida. El peso de una combinación es `log(1 + n)`: más mediciones pesan más, sin que una combinación domine.
- **Encogimiento** (`λ = 2`): un efecto con poca evidencia se acerca a 0, es decir, a la media.
- **Dispositivo nunca medido:** su efecto es el promedio ponderado de los **5 dispositivos medidos de nombre más parecido** con el mismo backend. El parecido suma palabras en común, número de modelo cercano (4070 frente a 4060) y núcleos cercanos en CPU.
- **Rango del 80 %:** sale de los cuantiles 10 y 90 del error de validación, según la evidencia del dispositivo.

### Validación

Se escondieron combinaciones que sí se habían medido, se predijeron y se compararon. Desde el 22 de noviembre, `teoria.py` ordena las combinaciones antes de partirlas, así que la validación es reproducible: dos corridas seguidas dan las mismas cifras. Antes de ese orden fijo, la prueba A varió entre 12.9 % y 13.4 %.

| Prueba | Error mediano | Dentro de ±25 % | n |
|---|---:|---:|---:|
| A. Combinaciones al azar (20 %) | **13.0 %** | 71 % | 11,210 |
| Referencia ingenua: promedio del dispositivo | 31.8 % | 38 % | 11,210 |
| B. Dispositivo en una versión donde nunca se midió | **13.3 %** | 71 % | 10,791 |
| C. Dispositivo nunca medido, por nombre parecido | **28.5 %** | 45 % | 11,041 |
| C2. Dispositivo nunca medido, por backend, clase, fabricante y memoria | 64.0 % | 19 % | 11,041 |

| Evidencia del dispositivo | Rango del 80 % (factor) |
|---|---|
| Mucha (>20 combinaciones) | 0.81–1.25 |
| Media (6–20) | 0.60–1.60 |
| Poca (1–5) | 0.25–3.12 |
| Hipotético (por nombre) | 0.41–1.69 |

Es la **primera versión validada del modelo de costos** de `FICHAS_TECNICAS.md` §2.4. Su meta era un error menor a 25 % en equipos no vistos: se cumple con dispositivos conocidos y queda cerca (28.5 %) con dispositivos nuevos.

### Hallazgos

1. **Combinaciones lejos de la teoría:** 5,766 combinaciones (10.2 %) se alejan más de 50 %, y 2,594 (4.6 %) más del doble. Son candidatas naturales a revisión.
2. **Los niveles N0–N4 no separan bien el render:**

   | Nivel | GPUs | Factor mediano | p10–p90 |
   |---|---:|---:|---|
   | N1 | 20 | 0.19 | 0.08–0.61 |
   | N2 | 97 | 0.91 | 0.21–5.31 |
   | N3 | 745 | 1.22 | 0.20–4.17 |
   | N4 | 51 | 5.71 | 2.49–9.13 |

   N2 (todas integradas) y N3 se solapan; algunas integradas, probablemente Apple, llegan a 5×. Un índice continuo por dispositivo sería más preciso.
3. **Sesgo de equipos:** solo **377 mediciones son N1 (0.04 %)** y las integradas son el 3 %. La teoría es menos precisa justo en las computadoras de los alumnos de Amatista.
4. **Interpretación de los factores:** el efecto de la versión y el ajuste backend × versión comparten información. Por separado pueden engañar; lo que vale es el **factor combinado**, que es el que usa la predicción.

### Power BI

`pbip.py` genera un proyecto de Power BI (`TeoriaG7B.pbip`, con el modelo en TMDL) que lee los CSV de `teoria.py`. Con segmentadores de dispositivo, versión y escena, la medida «Teoría (texto)» explica la predicción: «base × dispositivo × versión × escena», con su rango y el tipo de combinación (medida, interpolada, extrapolada o hipotética).

- **Versión 1:** el modelo cargó, pero el informe falló porque le faltaba el tema base.
- **Versión 2:** trae el tema y un script para la vista TMDL.
- Las fórmulas DAX reproducen el modelo con una diferencia máxima de 0.15 %, por el redondeo de los CSV.

## 3. El criterio automático de mediciones

Cada medición recibe un estado:
- **corroborada:** tiene al menos 4 pares en su combinación, a 2.5 desviaciones robustas o menos de su mediana (MAD con piso de 8 %), y a menos de 2.5× de la teoría;
- **anómala:** a más de 4 desviaciones de sus pares o, si no tiene pares suficientes, a más de 2.5× de la teoría;
- **sin pares suficientes:** el resto.

| | Resultado |
|---|---|
| Velocidad | 1,050,137 mediciones en **9 segundos** |
| Estados | Corroboradas 88.7 % · anómalas 3.4 % · sin pares suficientes 7.9 % |

**Prueba sin etiquetas humanas:** se corrompió a propósito el 2 % de las mediciones (21,002) de cuatro formas.

| Error sembrado | Detectado como anómalo | Se escapa como corroborado |
|---|---:|---:|
| Valor ×3 | 93 % | 1.8 % |
| Valor ÷3 | 94 % | 0.9 % |
| Valor ×1.6 (sutil) | 72 % | 11 % |
| Valor de otra medición cualquiera | 84 % | 8.8 % |

- **Pureza de «corroborado»: 99.87 %.**
- Las mediciones intactas marcadas como anómalas son el 3.3 %. Incluyen errores que ya venían en los datos, así que esta prueba no separa las falsas alarmas.
- **Límite:** la prueba mide errores al azar. Un sesgo que afecte por igual a muchas mediciones de una misma combinación no se detecta por consenso.

## 4. Reproducir

```bash
python -m pip install duckdb numpy pandas
```

1. Convertir el snapshot con el código de G7B:

   ```bash
   python analisis/teoria_rendimiento/convertir.py . opendata-latest.zip plano.csv
   ```

2. Ajustar y validar la teoría. Opcionalmente, agregar dispositivos hipotéticos con `--hipotetico "NOMBRE" BACKEND`:

   ```bash
   python analisis/teoria_rendimiento/teoria.py plano.csv salida/datos
   ```

3. Correr el criterio de mediciones y su prueba con errores sembrados:

   ```bash
   python analisis/teoria_rendimiento/criterio.py plano.csv salida/datos
   ```

4. Generar el proyecto de Power BI:

   ```bash
   python analisis/teoria_rendimiento/pbip.py salida/TeoriaG7B salida/datos
   ```

El snapshot está en `https://opendata.blender.org/snapshots/opendata-latest.zip` (unos 100 MB, licencia CC0).
