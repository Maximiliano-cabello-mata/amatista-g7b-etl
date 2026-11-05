# Publicar el worker cuando ACR Tasks esta bloqueado

El usuario reporto `TasksOperationsNotAllowed` despues de enviar el contexto.
La imagen no quedo acreditada como construida. El ACR existente sigue siendo util:
GitHub Actions construira con Docker en un runner y enviara la imagen al ACR.

## Configurar desde Cloud Shell

```bash
git pull --ff-only
bash infra/azure/configurar_publicacion_oidc.sh --aplicar
```

Requiere Azure y GitHub CLI autenticados, permisos para identidad/federacion,
asignar AcrPush y administrar variables del repositorio, y G7B_SUSCRIPCION ya
establecida. Crea g7b-github-acr, concede AcrPush solo al registro y configura
OIDC para la rama exacta del PR #9. Cualquier workflow confiable de esa rama con
id-token puede usar esa identidad: proteger el acceso de escritura a la rama.
No concede acceso al lago ni permisos para desplegar Jobs. No guarda claves.
Las variables client/tenant/subscription son identificadores, no secretos.

## Construir y publicar

Tras propagacion de permisos, desde un checkout limpio de la rama del PR #9:

```bash
git commit --allow-empty -m "build: publicar worker G7B [publicar-worker]"
git push origin chatgpt/g7b-arquitectura-privada-ofertas-20261101
gh run list --workflow publicar_worker_acr.yml --branch chatgpt/g7b-arquitectura-privada-ofertas-20261101 --limit 3
```

El workflow solo publica si G7B_ACR_OIDC_LISTO=si y el mensaje contiene el marcador.
No requiere fusionar main ni workflow_dispatch. Usa minutos de Actions y
almacenamiento del ACR; no ACR Tasks. Si falla, revisar el run antes de reintentar.
El resumen de una ejecucion exitosa contiene etiqueta por commit y digest.
No prueba acceso al lago.

## Configurar el Job con esa imagen

Usar el SHA exacto del run exitoso, no necesariamente el HEAD actual:

```bash
export G7B_IMAGEN_EXISTENTE="g7b/auditoria:SHA_COMPLETO_DEL_RUN_EXITOSO"
bash infra/azure/activar_diagnostico.sh --aplicar
```

Esta ruta omite ACR Tasks y resuelve la etiqueta al digest antes de actualizar
el Job. Conserva las comprobaciones de presupuesto, remediacion y suscripcion.
Despues seguir [WORKER_AZURE.md](WORKER_AZURE.md) para iniciar y verificar lectura.
Para pausar publicaciones: `gh variable set G7B_ACR_OIDC_LISTO --repo Maximiliano-cabello-mata/amatista-g7b-etl --body no`.
La identidad/federacion y rol permanecen hasta retirarlos explicitamente.

Fuentes: [OIDC en Azure](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-azure),
[federacion de identidad](https://learn.microsoft.com/en-us/cli/azure/identity/federated-credential?view=azure-cli-latest).
