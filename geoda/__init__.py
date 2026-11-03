"""Geoda: el kernel que adapta el trabajo 3D a los recursos de cada equipo (cimientos, v0).

Geoda no es un programa 3D ni un fork de Blender. Es la capa que, con datos medidos por G7B,
decide CÓMO se hace el trabajo 3D en un equipo concreto, y se lo deja listo a las herramientas
libres que ya existen (Blender, el editor web de Amatista, después Godot).

Cinco verbos (docs/GEODA.md):

    detectar   huella técnica del equipo (contratos.Huella)        → niveles.clasificar → N0..N4
    consultar  perfiles publicados (g7b.perfil/1) y modelo de costos  → perfiles, costos
    decidir    plan de ejecución (g7b.plan/1): programa, versión,      → planificador.decidir
               perfil, dónde correr, acciones y cómo deshacerlas
    aplicar    lo hace el cliente (add-on de Amatista) con las acciones del plan; Geoda no toca bpy
    medir      el cliente reporta la fluidez lograda; G7B la mete al cubo y Geoda aprende

Este paquete es el CEREBRO (vive en G7B, se alimenta del cubo). El CLIENTE vive en el add-on de
Amatista y solo necesita los contratos JSON, no este código.
"""
VERSION = "0.1.0"
