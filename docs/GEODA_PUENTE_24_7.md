# Puente continuo G7B → Geoda → Amatista (entrega 1)

Estado: **implementado en rama; no desplegado hasta fusionar, configurar credenciales y validar la publicación real**.

## Qué se conecta

- `vigilar.yml` detecta novedades y puede disparar una extracción en Zyte.
- `zyte_a_lago.yml` importa trabajos terminados a Azure Bronce.
- `procesar.yml` clasifica documentos y publica los aceptados en MongoDB (`conocimiento_3d.documentos`).
- `telemetria.yml` y `cubo.yml` llevan mediciones de hardware validadas a un cubo versionado en Azure.
- **Nuevo:** `geoda_publicar.yml` se puede lanzar manualmente, cada seis horas o tras finalizar correctamente `Procesar bronce` / `Cubo G7B`. Genera `publicacion/geoda.json` y lo sube a `main` solo si cambió.
- Amatista consulta ese JSON mediante `GET /api/g7b/v1/estado`; su página `#/geoda` presenta el estado y continúa usando perfiles locales base.

**Precaución:** la extracción de manuales Blender genera conocimiento textual, NO FPS ni capacidad de GPU. El cubo actual incluye 3 mediciones aceptadas y 3,000 en revisión (véase `docs/CUBO.md`). No existe evidencia suficiente para perfiles automáticos. El feed publica **cero perfiles**; la optimización por perfiles medidos será una segunda entrega con compuerta de calidad.

## Contrato público

`g7b.geoda.estado/1` contiene solamente:
- `version`, `cubo.version`, `cubo.mediciones`, `cubo.aceptadas`, `cubo.revision`;
- `cubo.recomendaciones_habilitadas = false`;
- `conocimiento.documentos`, conteo agregado en Mongo;
- `perfiles = []`.

No publica correos, usuarios, huellas técnicas, nombres de equipos, documentos crudos ni conexiones Mongo/Oracle. Antes de publicar se comprueban el SHA-256 del manifiesto del cubo, la versión y los conteos; si falla algo, el JSON vigente en GitHub permanece intacto.

## Orden para la activación de verdad

1. Fusionar los PR de G7B y Amatista, y comprobar sus pruebas automáticas.
2. En el environment `amatista1` comprobar que `AZURE_LAGO_URL` **sigue vigente** y `MONGO_URI` es válido. La SAS temporal usada el 3 de noviembre caduca en 24 h. **No habilitar trabajos programados usando una SAS vencida.**
3. Ejecutar manualmente `Publicar estado para Geoda` desde Actions. Confirmar `G7B_GEODA_PUBLICACION_VERIFICADA`, archivo `publicacion/geoda.json` en `main` y que no contiene información privada.
4. Desplegar la API y PWA de Amatista; comprobar `/api/g7b/v1/estado` y `#/geoda`.
5. Solo tras credenciales duraderas, control de costos y pruebas de reintento, habilitar las variables `G7B_INGESTA_ACTIVA=true` y `G7B_GEODA_PUBLICAR_ACTIVA=true` en el environment `amatista1`. Los cron de vigilancia, descarga, procesamiento y publicación podrán trabajar sin Cloud Shell abierta.

La nueva variable de publicación **empieza desactivada**, porque debe valer explícitamente `true`; las ejecuciones manuales están permitidas.

## Disponibilidad y límites

Azure, Mongo y Zyte son servicios gestionados. La API de Amatista corre como servicio systemd en su VM y Cloudflare distribuye la PWA. GitHub Actions funciona por tareas/eventos, **no como un servidor residente 24/7**: el cron es de mejor esfuerzo y puede retrasarse.

La disponibilidad 24/7 de la automatización **no está garantizada** hasta resolver:
- autenticación Azure sin SAS temporal (recomendado OIDC/identidad federada);
- cuenta de VM activa, servicio systemd habilitado, Caddy/Cloudflare/DNS y monitorización;
- permisos del bot para escribir el archivo agregado en `main` (si `main` está protegida, usar una rama de publicación o artefacto estático);
- alarmas por fallos y topes de gasto del rastreo y de nube.

Para detener el publicador automáticamente basta con `G7B_GEODA_PUBLICAR_ACTIVA=false`. Para detener ingestión, `G7B_INGESTA_ACTIVA=false`. Mantener la API de Amatista funcionando con su fallback no depende de esos trabajos.

## Pruebas y diagnóstico

```bash
python -m pytest -q pruebas/test_geoda_estado.py
gh workflow run geoda_publicar.yml --repo Maximiliano-cabello-mata/amatista-g7b-etl --ref main
gh run list --workflow geoda_publicar.yml --repo Maximiliano-cabello-mata/amatista-g7b-etl --limit 5
```

No crear `014_g7b.sql` todavía: Amatista tiene otro PR abierto con `014_panel_del_profesor.sql`. Este puente deliberadamente **no altera Oracle** y evita colisiones entre migraciones.
