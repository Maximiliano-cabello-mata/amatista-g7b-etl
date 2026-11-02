# Centro de Operaciones G7B — Azure y ofertas estudiantiles (arquitectura de ejecución)

**Fecha:** 2026-11-02. **Estado:** laboratorio v3 y auditor privado ejecutados con exito; marcador de la ejecucion a665997 localizado en Log Analytics segun salida del usuario. Entrega persistida comprobada; valores agregados y ETL no acreditados. Prioridad: consolidar la base y preparar migracion, no investigar una averia no demostrada. [Cierre operativo](CIERRE_AZURE.md). [Bitacora](bitacoras/2026-11-02.md).
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

**El laboratorio v3 ya fue desplegado; validación y producción siguen siendo diseño.** No se acreditan
 redes privadas VNet/Private Link, aislamiento por cuenta de almacenamiento ni
autenticación del Centro de Operaciones. La plantilla configura identidad
administrada de Azure y RBAC mínimo; falta probar el acceso efectivo a Blob, y se hará una segunda fase de aislamiento
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
  `ManagedIdentityCredential`, exclusivamente cuenta objetos/tamaños por zona;
  rechaza credenciales SAS o cadenas de conexión y no recupera contenidos.
- `infra/azure/worker/Dockerfile` — worker ejecutado sin usuario root y sin
  puerto HTTP; se construye localmente con `docker build -f ... .`.
- `infra/ofertas/catalogo.json` — inventario de ofertas y funciones.
- `herramientas/validar_catalogo.py` + `pruebas/test_operacion_azure.py`
  — reglas que impiden asumir conexiones o eludir los límites.

**Importante:** la plantilla inicial conserva el smoke publico, pero Azure ya
ejecuta el auditor privado mediante ACR. La plantilla aun no representa ACR,
registro del Job ni Log Analytics: no usarla para actualizar el entorno actual.
El script de aprovisionamiento bloquea entornos v3 existentes hasta reconciliar
estas diferencias. No es aun un Centro de Operaciones completo.
ACR, Log Analytics y redes privadas pueden generar cargos incluso sin trabajos.

## 5. Seguimiento del incidente histórico SAS

La ejecución antigua `41381723814`, asociada al reporte histórico de exposición de SAS, devuelve 404 en GitHub. No demuestra revocación de la credencial ni permite confirmar por sí sola la eliminación del run. La rotación/revocación no fue verificada en esta revisión; no se afirma que siga sin realizarse.

Antes de repetir una rotación, revisar la evidencia de remediación existente y las integraciones afectadas. Si se confirma que falta remediación, seguir el [runbook](AZURE_24_7_CLOUD_SHELL.md#paso-2--incidente-de-sas-y-continuidad-de-servicio) con autorización y sin publicar secretos. Los controles del script de aprovisionamiento se conservan; sus variables de confirmación no prueban por sí mismas el estado de Azure.

## 6. Validación para cambios posteriores en Azure Cloud Shell

Para inspeccionar la plantilla, no son necesarios cambios de recursos:

```bash
git clone --branch chatgpt/g7b-arquitectura-privada-ofertas-20261101 \
  https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl.git g7b-op
cd g7b-op

# Obtén SOLO el nombre de tu cuenta de almacenamiento desde Azure Portal.
export STORAGE_ACCOUNT_NAME="NOMBRE_CUENTA"
# Solo si existe evidencia de remediación revisada:
export G7B_ROTACION_CONFIRMADA=si
bash infra/azure/validar_y_aprovisionar.sh
```

Si ya existe el entorno v3, se detiene para evitar regresiones: usar el
[diagnostico operativo](CIERRE_AZURE.md). Para un entorno nuevo ejecuta
validación sintáctica y `what-if`, **no despliega**. El comando
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

## Siguiente paso: cerrar logs y operacion

El worker ya se ejecuto y su marcador persistido fue localizado por el usuario.
Seguir [CIERRE_AZURE.md](CIERRE_AZURE.md) para comparar la base y preparar cambios
sin lanzar trabajos. La plantilla nueva de mantenimiento usa dependencias
existentes; no es reconstruccion total de la suscripcion. Las pruebas simuladas
no acreditan despliegue, migracion de logs, alertas ni recuperacion en Azure.
