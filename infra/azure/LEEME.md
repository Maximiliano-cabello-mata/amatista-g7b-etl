# Configurar Azure (el lago de datos de G7B)

Azure guarda **todo lo que se extrae, tal como llegó** (zona bronce del [plan](../../docs/PLAN.md#7-arquitectura)), y después lo validado y lo curado (plata y oro). Zyte borra sus datos a los 120 días; el lago no.

**Qué se crea:**
- **Un grupo de recursos `g7b`:** la carpeta donde vive todo lo de G7B en Azure.
- **Una cuenta de almacenamiento:** privada, solo HTTPS, con papelera de 7 días para lo que se borre.
- **Un contenedor `lago`** con las zonas como carpetas: `bronce/`, `plata/`, `oro/`, `sintetico/`, `control/` y `tmp/`.
- **Una regla de ciclo de vida:** lo de bronce pasa al nivel Cool (más barato) a los 30 días, y `tmp/` se borra solo a los 7.

**Costo:** el almacenamiento cuesta centavos de dólar por GB al mes, así que los $100 del crédito alcanzan de sobra para el lago. Revisa los precios de tu región en la calculadora de Azure si quieres el número exacto.

Tiempo total: unos 20 minutos.

## Paso 1. Activar Azure for Students

1. Entra a la oferta de Azure en el GitHub Student Developer Pack y conecta tu cuenta. No pide tarjeta.
2. En [portal.azure.com](https://portal.azure.com) › **Suscripciones** debe aparecer **Azure for Students** con el crédito de $100.

Cuando el crédito se acaba, los servicios se detienen; no te cobran por sorpresa. Aun así, el paso 4 te avisa antes.

## Paso 2. Abrir Cloud Shell

Cloud Shell es una terminal dentro del portal que ya trae la CLI de Azure y tu sesión iniciada. No instalas nada en tu PC.

1. En el portal, haz clic en el icono **>_** de la barra de arriba.
2. Elige **Bash**.
3. Si te pregunta por almacenamiento, elige la opción que **no requiere cuenta de almacenamiento**. Así no se crea nada extra.
4. Revisa que estés en la suscripción correcta:

```bash
az account show --query name -o tsv
```

Debe decir **Azure for Students**. Si no:

```bash
az account set --subscription "Azure for Students"
```

## Paso 3. Crear el lago

En Cloud Shell, primero descarga el repo:

```bash
git clone -b claude/peaceful-tesla-ctqaps https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl.git
```

Después corre el script:

```bash
bash amatista-g7b-etl/infra/azure/crear_lago.sh
```

(Cuando la PR se fusione a `main`, quita `-b claude/peaceful-tesla-ctqaps` del primer comando.)

El script crea todo en la primera región que tu cuenta permita (empieza por México Central) y al final imprime una línea así:

```text
AZURE_LAGO_URL=https://g7blagoxxxxxx.blob.core.windows.net/lago?sv=...&sig=...
```

**Ese valor es una llave.** Cópialo directo al paso 5. No lo pegues en ningún chat, ni en un issue, ni en un archivo del repo. Permite leer, agregar y escribir en el lago, **pero no borrar**, y vence en un año.

**Si tu cuenta no permite una región:** Azure for Students solo deja usar algunas regiones, distintas en cada cuenta. El script prueba solo, en orden, México Central y otras regiones cercanas (South Central US, Central US, East US 2...), y se queda con la primera permitida. En pantalla verás `... no está permitida en tu suscripción` hasta que una funcione. Si ninguna de la lista sirve, lista todas las regiones:

```bash
az account list-locations -o table
```

Y prueba una a mano:

```bash
UBICACION=westeurope bash amatista-g7b-etl/infra/azure/crear_lago.sh
```

El script se puede correr varias veces: lo que ya existe se deja igual, y cada vez imprime una llave nueva. Úsalo así también cuando la llave esté por vencer.

## Paso 4. Presupuesto con avisos

En el portal: **Cost Management** › **Presupuestos** › **Agregar**.

- Alcance: la suscripción Azure for Students.
- Monto: **$10 al mes**.
- Avisos a tu correo al **50 %, 80 % y 100 %**.

El lago no debería pasar de centavos. Si llega un aviso, algo está gastando de más y hay que revisarlo. Si tu suscripción no permite presupuestos, revisa **Cost Management** › **Análisis de costos** una vez por semana.

## Paso 5. Guardar las llaves

Estos son los secretos que usan las tareas programadas:

| Nombre | Qué es | De dónde sale |
|---|---|---|
| `AZURE_LAGO_URL` | La llave del lago | Paso 3 |
| `ZYTE_API_KEY` | La llave de tu cuenta de Zyte | Panel de Zyte › tu cuenta › API key |
| `MONGO_URI` | La cadena del usuario de MongoDB que **solo escribe** en `conocimiento_3d` | MongoDB Atlas › Database Access (crear el usuario) › Connect |

1. **GitHub** (lo que usan las tareas programadas): en el repo, **Settings** › **Secrets and variables** › **Actions** › **New repository secret**. Crea los dos secretos. En la pestaña **Variables**, crea `ZYTE_PROJECT_ID` con el valor `883618`.
2. **Doppler** (la copia central de todas las llaves, plan 7.2): crea el proyecto `g7b` y guarda ahí los mismos dos valores, más `MONGO_URI`. Más adelante, la integración de Doppler con GitHub puede sincronizarlos sola.

## Paso 6. Probar que Zyte llega al lago

Las tareas programadas solo aparecen en GitHub cuando su archivo está en `main`, así que **primero hay que fusionar la PR**.

1. En GitHub: **Actions** › **Zyte al lago** › **Run workflow**, con "Solo listar" marcado. Debe listar tus trabajos terminados en Zyte.
2. Otra vez **Run workflow**, ahora sin marcar. Copia los trabajos al lago.
3. A partir de ahí corre sola cada noche (03:17, hora de la Ciudad de México) y solo copia lo nuevo.

## Paso 7. Ver lo que hay en el lago

- **En el portal:** tu cuenta de almacenamiento › **Contenedores** › `lago` › `bronce/zyte/blender_docs/...`
- **Más cómodo:** Azure Storage Explorer, una aplicación gratuita de Microsoft para Windows, Mac y Linux. Inicia sesión con tu cuenta y navega el lago como si fueran carpetas.

## Paso 8. Subir las mediciones de la sonda desde tu PC

Necesitas Python con las dependencias:

```bash
pip install -r requirements-lago.txt
```

En **Windows (cmd)**, con las comillas exactamente así, porque la llave contiene `&`:

```bat
set "AZURE_LAGO_URL=https://...pega aquí la llave..."
```

```bat
python -m g7b_lago.subir_mediciones resultados
```

En **Linux o macOS**:

```bash
export AZURE_LAGO_URL='https://...pega aquí la llave...'
```

```bash
python -m g7b_lago.subir_mediciones resultados
```

Las mediciones reales van a `bronce/sonda/` y las sintéticas a `sintetico/sonda/`. Lo que ya se subió no se vuelve a subir.

## Si la llave se filtra

Corre esto en Cloud Shell (cambia el nombre por el de tu cuenta):

```bash
az storage account keys renew -g g7b -n g7blagoxxxxxx --key primary
```

Esto invalida todas las llaves que imprimió el script. Después vuelve a correr el script para obtener una nueva y actualízala en GitHub y Doppler.

## Qué ya está probado y qué no

- **Probado aquí:** el código del lago y las dos herramientas (`zyte_a_lago` y `subir_mediciones`), contra Azurite, el emulador oficial de Azure Storage. Las mismas pruebas corren en GitHub Actions con cada cambio.
- **No probado:** el script `crear_lago.sh` en una cuenta real de Azure, porque no tengo acceso a la tuya. Se revisó solo su sintaxis. Si un paso falla, copia el mensaje de error (sin la llave) y lo corregimos.

## Paso 9. Encender la ingesta

Con la PR fusionada y los secretos del paso 5:

1. **Las arañas se despliegan solas en Zyte:** la tarea **Desplegar a Zyte** corre las pruebas y despliega con cada push a `main` que toque las arañas. La primera vez, córrela a mano (Actions › **Desplegar a Zyte** › Run workflow). En Zyte, quita `ITEM_PIPELINES` de los Raw Settings: ahora vive en `settings.py`.

2. **Probar en simulacro:** Actions › **Vigilar fuentes** › Run workflow, con "simulacro" marcado. Debe listar arXiv, Stack Exchange y el manual de Blender, sin errores.
3. **Correrla de verdad:** lo mismo, sin marcar "simulacro". Después corre **Zyte al lago** y **Procesar bronce** con "Evaluar sin escribir" marcado, para ver cuánto acepta y cuánto rechaza el embudo antes de escribir en plata.
4. **Opcional:** el secreto `STACKEXCHANGE_KEY`, que se pide gratis en stackapps.com, sube la cuota de la API de Stack Exchange.

Cómo funciona todo esto: [docs/INGESTA.md](../../docs/INGESTA.md).

**El interruptor:** las tareas programadas (Vigilar fuentes, Zyte al lago y Procesar bronce) **no corren solas** hasta que crees la variable `G7B_INGESTA_ACTIVA` con el valor `true` (Settings › Secrets and variables › Actions › Variables). Las corridas manuales siempre funcionan. Para pausar todo, cambia el valor a `false`.
