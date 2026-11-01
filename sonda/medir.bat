@echo off
rem Sonda de rendimiento de G7B en Windows.
rem Uso: medir.bat            (sin ventana: edicion, animacion y render)
rem      medir.bat ventana    (abre Blender para medir tambien la vista 3D)
rem Si Blender no esta en la ruta de abajo, define BLENDER antes:
rem      set BLENDER=C:\ruta\a\blender.exe
setlocal
if "%BLENDER%"=="" set "BLENDER=C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
if not exist "%BLENDER%" (
  echo No encuentro Blender en "%BLENDER%". Define la variable BLENDER con la ruta de blender.exe.
  exit /b 1
)
set "AQUI=%~dp0"
if /i "%1"=="ventana" (
  "%BLENDER%" --factory-startup --python "%AQUI%g7b_sonda.py" -- --salida "%AQUI%..\resultados" --salir
) else (
  "%BLENDER%" -b --factory-startup --python "%AQUI%g7b_sonda.py" -- --salida "%AQUI%..\resultados"
)
endlocal
