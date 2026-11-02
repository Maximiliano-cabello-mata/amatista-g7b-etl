# Centro de Operaciones G7B — Azure y ofertas estudiantiles (arquitectura de ejecución)

**Fecha:** 2026-11-01. **Estado:** propuesta implementada en una rama; SIN despliegue en Azure.
**Regla:** las ofertas son capacidades de la fábrica de datos, no nuevas bases de datos arbitrarias.

## 1. Resultado que debe producir el sistema

**G7B mide y decide** qué configuraciones 3D ofrecen mejor calidad visual y fluidez según el dispositivo.
**Geoda aplica** las decisiones validadas. **Amatista las consume** mediante contratos versionados,
sin que G7B reciba información personal del alumnado. La ciencia de datos es una función
interna de investigación y de optimización, no el producto vendido.

```text
SONDAS / BLENDER OPEN DATA / ZYTE / BROWSERSTACK
        |
        v
AZURE DATA LAKE (privado, fuente de verdad)
  bronce/ -- inmutable
  plata/  -- Parquet validado
  oro/    -- versiones del cubo DuckDB y perfiles científicos
  control/-- decisiones, aprobaciones, trabajos, audit trail
        |
        v
AZURE JOBS (bajo demanda, sin endpoints públicos) -- DuckDB / tests / calidad
        |
        +--- snapshots LIMITADOS --> Deepnote, Camber, Colab
        |                         solo datasets permitidos
        +--- conocimiento ---> MongoDB (API de consulta por rol)
        +--- informes ---> Microsoft 365 / reportes internos
        |
        v
GEODA: registro de modelos, experimentos y políticas de promoción
        |
        v
AMATISTA: consume versiones APROBADAS con rollback
```

## 2. Entornos cerrados (no confundir privacidad con ausencia de acceso HTTP)

| Entorno | Recursos | Quién accede | Política |
|---|---|---|---|
| `laboratorio` | Datos de prueba y muestras aprobadas | Investigador; runners de prueba | Nunca escribe en oro de producción |
| `validacion` | Réplica filtrada de datasets; versiones candidatas | Jobs de QA y aprobador | Puerta de calidad + reproducibilidad |
| `produccion` | Lago persistente, API privada, modelos aprobados | Servicios con identidad y roles | Inmutable/versionado, sin acceso directo de notebooks |

**En la rama de hoy solo existe una plantilla de laboratorio/validación.** Todavía no
hay redes privadas VNet/Private Link, aislamiento por cuenta de almacenamiento ni
autenticación del Centro de Operaciones. La autenticación a Blob será por identidad
administrada de Azure y RBAC mínimo, y se hará una segunda fase de aislamiento
de red cuando se confirme costo, permisos y acceso remoto administrativo.
No presentar un contenedor privado de Blob como si su endpoint ya estuviera
aislado de Internet: está protegido por autenticación, no necesariamente por red.

## 3. Cómo usamos el Student Pack

El inventario machine-readable está en `infra/ofertas/catalogo.json`.
Cada servicio tiene función, clasificación, responsable y estado.
Un servicio no se registra como conectado sin verificación. Algunos sirven
como alternativas o capacitación; integrar cada uno en producción causaría
duplicidad, riesgos y consumo innecesario de créditos.

**Capas principales:**

- Azure: almacenamiento, identidad, RBAC, jobs, presupuesto, control de versiones.
- GitHub: código, CI, revisión de PRs, builds; futuros despliegues con OIDC.
- Zyte: ingesta documental autorizada a intervalos controlados.
- MongoDB Atlas: documentos versionados y búsquedas; no la fuente numérica primaria.
- Deepnote: notebooks de investigación dentro de su espacio privado.
- Camber: GPU/CPU para experimentos sobre snapshots aprobados y trazables.
- BrowserStack: sondeo de render/compatibilidad web, sin datos personales.
- Sentry: errores de aplicación; New Relic/Datadog se mantienen como evaluaciones,
  evitando instalar tres agentes duplicados.
- Doppler/1Password: gestión de secretos externos y recuperación humana;
  en Azure se prefieren identidades administradas y OIDC.
- Microsoft 365, Codecov, CodeScene, Copilot, JetBrains y Codespaces:
  productividad, reportes y calidad de ingeniería sin dar permisos sobre datos sensibles.

**Protección del crédito:** no activar promociones de 1 a 6 meses hasta que exista
una tarea, cuota, presupuesto y resultado esperado. Heroku, Appwrite, Clerk,
LocalStack, Travis, etc. son opciones/alternativas, no dependencias simultáneas.
No cargar datos a terceros sin un análisis de condiciones y un dataset minimizado.
Revisar qué créditos requieren activación manual y si son acumulables.

## 4. Qué se ha implementado en esta rama

- `infra/azure/g7b-control-privado.bicep` — usa la cuenta actual, crea de forma
  opcional un entorno de Azure Container Apps y un job de tipo MANUAL sin ingress;
  identidad de sistema con rol **Storage Blob Data Reader** limitado al contenedor
  `lago`; no contiene claves ni crea nuevas cuentas.
- `infra/azure/validar_y_aprovisionar.sh` — bloquea el despliegue si no se
  confirma rotación de credenciales y presupuesto; ejecuta `az bicep build`
  y `az deployment group what-if` antes de ofrecer aprovisionamiento.
- `g7b_ops/auditoria.py` — diagnóstico read-only basado en
  `DefaultAzureCredential`, exclusivamente cuenta objetos/tamaños por zona;
  rechaza credenciales SAS o cadenas de conexión y no recupera contenidos.
- `infra/azure/worker/Dockerfile` — worker ejecutado sin usuario root y sin
  puerto HTTP; se construye localmente con `docker build -f ... .`.
- `infra/ofertas/catalogo.json` — inventario de ofertas y funciones.
- `herramientas/validar_catalogo.py` + `pruebas/test_operacion_azure.py`
  — reglas que impiden asumir conexiones o eludir los límites.

**Importante:** el job de Bicep arranca con una imagen pública de prueba (smoke).
No ejecutar el worker real hasta crear una imagen PRIVADA en Azure Container
Registry (ACR) y conceder explícitamente `AcrPull` a su identidad.
El manifest deja cambiar `workerImage` después; esta fase aún no configura
ACR ni Log Analytics y, por tanto, no es un Centro de Operaciones completo.
ACR, Log Analytics y redes privadas pueden generar cargos incluso sin trabajos.

## 5. Incidente previo: detener y corregir primero

Un registro público de GitHub Actions de la ejecución
`41381723814` divulgó una URL SAS válida, por un problema de
configuración del workflow. Se corrigió el código que introducía el
carácter extra, pero **eso no revoca la credencial ni borra los logs**.

Acciones en el portal de Azure y GitHub que deben realizarse ANTES de
ejecutar el script de aprovisionamiento:

1. Identificar los sistemas que dependen de la clave primaria (el script
   `crear_lago.sh` usa `keys list --query '[0].value'`).
2. En Azure Cloud Shell, con el nombre real de la cuenta y tu autorización,
   ejecutar `az storage account keys renew -g g7b -n NOMBRE_CUENTA --key primary`.
   Esa operación puede invalidar otras SAS firmadas con la clave primaria.
3. Regenerar firmas de tiempo corto mientras se migran los conectores antiguos;
   sustituir sus secretos de GitHub y Doppler sin compartirlos por chat ni logs.
4. Borrar la ejecución de GitHub Actions `41381723814` (incluidos los registros)
   y revisar otros runs que pudieran haber expuesto el mismo valor. Borrar logs
   no basta: la rotación es indispensable.
5. Migrar jobs Azure a identidad administrada y acceso mínimo; GitHub a OIDC,
   restringiendo federación al environment de despliegue.

**No se han realizado desde esta rama rotaciones, cambios en el Portal Azure ni
conexiones externas; no existe aquí una sesión de Azure para operarlo.**

## 6. Primera ejecución en Azure Cloud Shell (cuando estén completas las puertas)

Para inspeccionar la plantilla, no son necesarios cambios de recursos:

```bash
git clone --branch chatgpt/g7b-arquitectura-privada-ofertas-20261101 \
  https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl.git g7b-op
cd g7b-op

# Obtén SOLO el nombre de tu cuenta de almacenamiento desde Azure Portal.
export STORAGE_ACCOUNT_NAME="NOMBRE_CUENTA"
export G7B_ROTACION_CONFIRMADA=si
bash infra/azure/validar_y_aprovisionar.sh
```

Esto ejecuta validación sintáctica y `what-if`, **no despliega**. El comando
de aprovisionamiento existe detrás de dos confirmaciones de entorno:
`G7B_APROVISIONAR=si` y `G7B_PRESUPUESTO_REVISADO=si`, además de la
rotación confirmada. Antes de usarlo revisa los cargos y las cuotas de tu
suscripción Azure for Students.

Comprobar que la suscripción permite Azure Container Apps, el registro de los
resource providers `Microsoft.App` y `Microsoft.OperationalInsights`,
y que tu identidad tiene permisos para `roleAssignments/write`.
Si faltan permisos, la plantilla debe fallar sin conceder privilegios extras.

## 7. Definición de terminado (primer servicio operativo)

No marcar `listo` hasta disponer de evidencia de:

1. SAS anterior revocada y logs públicos revisados.
2. Bicep validado en Cloud Shell de la suscripción.
3. Coste máximo y alerta configurados.
4. ACR privado con imagen G7B reproducible, sin secreto en Dockerfile.
5. Job real con identidad y lectura de `lago`, con diagnósticos correctos.
6. Logs privados con retención; alarmas de error.
7. Dataset de salida versionado con prueba de calidad y rollback.
8. Centro de Operaciones autenticado en la red autorizada.
9. Promoción explícita de perfiles a Geoda y Amatista por contrato, nunca
   publicación de datos brutos de estudiantes.

**Regla de producción:** una prueba verde no representa una decisión científica
válida. Se deben medir muestras reales variadas, con licencias, orígenes y
calidad estadística documentados antes de automatizar recomendaciones.
