"""Genera el proyecto de Power BI (.pbip, modelo en TMDL) que lee los CSV de teoria.py."""
import json
import shutil
import sys
import uuid
from pathlib import Path

NOMBRE = 'TeoriaG7B'
T = '\t'


def tag():
    return str(uuid.uuid4())


# (tabla, archivo, [(columna, tipo_tmdl, tipo_m)], oculta)
TEXTO, ENTERO, DECIMAL = ('string', 'type text'), ('int64', 'Int64.Type'), ('double', 'type number')
TABLAS = [
    ('Dispositivos', 'dispositivos.csv', [('id', *TEXTO), ('dispositivo', *TEXTO), ('backend', *TEXTO), ('fabricante', *TEXTO),
                                          ('clase', *TEXTO), ('vram_gb', *DECIMAL), ('grupo_vram', *TEXTO), ('nivel', *TEXTO),
                                          ('efecto', *DECIMAL), ('factor', *DECIMAL), ('n_combinaciones', *ENTERO),
                                          ('n_mediciones', *ENTERO), ('version_min', *TEXTO), ('version_max', *TEXTO),
                                          ('evidencia', *TEXTO), ('vecinos', *TEXTO)], False),
    ('Versiones', 'versiones.csv', [('version', *TEXTO), ('orden', *ENTERO), ('efecto', *DECIMAL), ('factor', *DECIMAL),
                                    ('n_mediciones', *ENTERO)], False),
    ('Escenas', 'escenas.csv', [('escena', *TEXTO), ('efecto', *DECIMAL), ('factor', *DECIMAL), ('n_mediciones', *ENTERO)], False),
    ('BackendVersion', 'backend_version.csv', [('clave', *TEXTO), ('backend', *TEXTO), ('version', *TEXTO),
                                               ('efecto', *DECIMAL), ('factor', *DECIMAL)], True),
    ('BackendEscena', 'backend_escena.csv', [('clave', *TEXTO), ('backend', *TEXTO), ('escena', *TEXTO),
                                             ('efecto', *DECIMAL), ('factor', *DECIMAL)], True),
    ('Combinaciones', 'combinaciones_medidas.csv', [('id', *TEXTO), ('version', *TEXTO), ('escena', *TEXTO), ('clave_bv', *TEXTO),
                                                    ('clave_be', *TEXTO), ('n', *ENTERO), ('mediana', *DECIMAL), ('p25', *DECIMAL),
                                                    ('p75', *DECIMAL), ('teoria', *DECIMAL), ('error_pct', *DECIMAL)], False),
    ('HardwareTeorico', 'hardware_teorico.csv', [('clave', *TEXTO), ('backend', *TEXTO), ('clase', *TEXTO), ('fabricante', *TEXTO),
                                                 ('grupo_vram', *TEXTO), ('efecto', *DECIMAL), ('factor', *DECIMAL),
                                                 ('n_dispositivos', *ENTERO), ('estimado_con', *TEXTO)], False),
    ('Intervalos', 'intervalos.csv', [('evidencia', *TEXTO), ('factor_bajo', *DECIMAL), ('factor_alto', *DECIMAL),
                                      ('n_validacion', *ENTERO)], True),
    ('Modelo', 'modelo.csv', [('clave', *TEXTO), ('valor', *DECIMAL)], True),
]

# Medidas: la teoría de la combinación elegida en los segmentadores (dispositivo × versión × escena).
SEL = '''VAR _id = SELECTEDVALUE ( Dispositivos[id] )
VAR _b = SELECTEDVALUE ( Dispositivos[backend] )
VAR _v = SELECTEDVALUE ( Versiones[version] )
VAR _e = SELECTEDVALUE ( Escenas[escena] )'''
MEDIDAS = [
    ('Factor dispositivo', '0.00"×"', 'SELECTEDVALUE ( Dispositivos[factor] )'),
    ('Factor versión', '0.00"×"', SEL + '''
RETURN
    IF ( ISBLANK ( _v ) || ISBLANK ( _b ), BLANK (),
        EXP ( SELECTEDVALUE ( Versiones[efecto] )
            + COALESCE ( LOOKUPVALUE ( BackendVersion[efecto], BackendVersion[clave], _b & "|" & _v ), 0 ) ) )'''),
    ('Factor escena', '0.00"×"', SEL + '''
RETURN
    IF ( ISBLANK ( _e ) || ISBLANK ( _b ), BLANK (),
        EXP ( SELECTEDVALUE ( Escenas[efecto] )
            + COALESCE ( LOOKUPVALUE ( BackendEscena[efecto], BackendEscena[clave], _b & "|" & _e ), 0 ) ) )'''),
    ('Base', '#,0.0', 'EXP ( LOOKUPVALUE ( Modelo[valor], Modelo[clave], "base_log" ) )'),
    ('Teoría (samples/min)', '#,0.0', SEL + '''
RETURN
    IF ( ISBLANK ( _id ) || ISBLANK ( _v ) || ISBLANK ( _e ), BLANK (),
        [Base] * [Factor dispositivo] * [Factor versión] * [Factor escena] )'''),
    ('Teoría mínimo (80 %)', '#,0.0', '''[Teoría (samples/min)]
    * LOOKUPVALUE ( Intervalos[factor_bajo], Intervalos[evidencia], SELECTEDVALUE ( Dispositivos[evidencia] ) )'''),
    ('Teoría máximo (80 %)', '#,0.0', '''[Teoría (samples/min)]
    * LOOKUPVALUE ( Intervalos[factor_alto], Intervalos[evidencia], SELECTEDVALUE ( Dispositivos[evidencia] ) )'''),
    ('Medido (samples/min)', '#,0.0', SEL + '''
RETURN
    LOOKUPVALUE ( Combinaciones[mediana], Combinaciones[id], _id, Combinaciones[version], _v, Combinaciones[escena], _e )'''),
    ('Mediciones de la combinación', '#,0', SEL + '''
RETURN
    COALESCE ( LOOKUPVALUE ( Combinaciones[n], Combinaciones[id], _id, Combinaciones[version], _v, Combinaciones[escena], _e ), 0 )'''),
    ('Error de la teoría (%)', '0.0', '''VAR _m = [Medido (samples/min)]
RETURN IF ( ISBLANK ( _m ), BLANK (), ( [Teoría (samples/min)] / _m - 1 ) * 100 )'''),
    ('Tipo de combinación', None, SEL + '''
VAR _ev = SELECTEDVALUE ( Dispositivos[evidencia] )
VAR _orden = SELECTEDVALUE ( Versiones[orden] )
VAR _min = LOOKUPVALUE ( Versiones[orden], Versiones[version], SELECTEDVALUE ( Dispositivos[version_min] ) )
VAR _max = LOOKUPVALUE ( Versiones[orden], Versiones[version], SELECTEDVALUE ( Dispositivos[version_max] ) )
RETURN
    SWITCH ( TRUE (),
        ISBLANK ( _id ) || ISBLANK ( _v ) || ISBLANK ( _e ), "Elige un dispositivo, una versión y una escena",
        NOT ISBLANK ( [Medido (samples/min)] ), "Medida: hay datos reales de esta combinación",
        LEFT ( _ev, 10 ) = "hipotético", "Hipotética: dispositivo estimado por nombres parecidos",
        _orden >= _min && _orden <= _max, "Interpolada: nunca medida, dentro de las versiones medidas del dispositivo",
        "Extrapolada: fuera de las versiones medidas del dispositivo (más incierta)" )'''),
    ('Teoría (texto)', None, '''VAR _t = [Teoría (samples/min)]
RETURN
    IF ( ISBLANK ( _t ), [Tipo de combinación],
        "Teoría: " & FORMAT ( _t, "#,0" ) & " samples/min (80 %: " & FORMAT ( [Teoría mínimo (80 %)], "#,0" ) & "–"
            & FORMAT ( [Teoría máximo (80 %)], "#,0" ) & "). = base " & FORMAT ( [Base], "#,0" )
            & " × dispositivo " & FORMAT ( [Factor dispositivo], "0.00" ) & " × versión " & FORMAT ( [Factor versión], "0.00" )
            & " × escena " & FORMAT ( [Factor escena], "0.00" ) & ". " & [Tipo de combinación] & "."
            & IF ( NOT ISBLANK ( [Medido (samples/min)] ),
                " Medido: " & FORMAT ( [Medido (samples/min)], "#,0" ) & " (" & [Mediciones de la combinación] & " mediciones).", "" )
            & " Evidencia del dispositivo: " & SELECTEDVALUE ( Dispositivos[evidencia] ) & "." )'''),
    ('Error mediano · combinaciones al azar (%)', '0.0', 'LOOKUPVALUE ( Modelo[valor], Modelo[clave], "A_combinaciones_al_azar_error_mediano_pct" )'),
    ('Error mediano · versión nueva (%)', '0.0', 'LOOKUPVALUE ( Modelo[valor], Modelo[clave], "B_dispositivo_en_version_nueva_error_mediano_pct" )'),
    ('Error mediano · dispositivo nunca medido (%)', '0.0', 'LOOKUPVALUE ( Modelo[valor], Modelo[clave], "C_dispositivo_nunca_medido_por_nombre_error_mediano_pct" )'),
]


def indentar(texto, n):
    return '\n'.join((T * n + linea) if linea.strip() else '' for linea in texto.splitlines())


def fuente_m(archivo, columnas):
    tipos = ', '.join(f'{{"{c}", {m}}}' for c, _, m in columnas)
    return f'''let
    Origen = Csv.Document(File.Contents(CarpetaDatos & "{archivo}"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Encabezados = Table.PromoteHeaders(Origen, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Encabezados, {{{tipos}}}, "en-US")
in
    Tipos'''


def tabla_tmdl(nombre, archivo, columnas, oculta):
    lineas = [f'table {nombre}', f'{T}lineageTag: {tag()}', '']
    if oculta:
        lineas[1:1] = [f'{T}isHidden']
    for col, tipo, _ in columnas:
        lineas += [f'{T}column {col}', f'{T*2}dataType: {tipo}']
        if oculta:
            lineas.append(f'{T*2}isHidden')
        lineas += [f'{T*2}lineageTag: {tag()}', f'{T*2}summarizeBy: none', f'{T*2}sourceColumn: {col}', '',
                   f'{T*2}annotation SummarizationSetBy = Automatic', '']
    lineas += [f'{T}partition {nombre} = m', f'{T*2}mode: import', f'{T*2}source =', indentar(fuente_m(archivo, columnas), 4), '',
               f'{T}annotation PBI_ResultType = Table', '']
    return '\n'.join(lineas)


def tabla_medidas():
    lineas = ['table Teoria', f'{T}lineageTag: {tag()}', '']
    for nombre, formato, dax in MEDIDAS:
        lineas += [f"{T}measure '{nombre}' = ```", indentar(dax, 3), f'{T*3}```']
        if formato:
            lineas.append(f'{T*2}formatString: {formato}')
        lineas += [f'{T*2}lineageTag: {tag()}', '']
    lineas += [f'{T}column Columna', f'{T*2}dataType: int64', f'{T*2}isHidden', f'{T*2}lineageTag: {tag()}',
               f'{T*2}summarizeBy: none', f'{T*2}sourceColumn: Columna', '', f'{T*2}annotation SummarizationSetBy = Automatic', '',
               f'{T}partition Teoria = m', f'{T*2}mode: import', f'{T*2}source =',
               indentar('let\n    Origen = #table(type table [Columna = Int64.Type], {{1}})\nin\n    Origen', 4), '',
               f'{T}annotation PBI_ResultType = Table', '']
    return '\n'.join(lineas)


def main():
    destino = Path(sys.argv[1])
    datos = Path(sys.argv[2])
    carpeta_por_omision = sys.argv[3] if len(sys.argv) > 3 else 'C:\\TeoriaG7B\\datos\\'
    if destino.exists():
        shutil.rmtree(destino)
    modelo = destino / f'{NOMBRE}.SemanticModel'
    defin = modelo / 'definition'
    (defin / 'tables').mkdir(parents=True)
    reporte = destino / f'{NOMBRE}.Report'
    reporte.mkdir()
    (destino / f'{NOMBRE}.pbip').write_text(json.dumps({
        'version': '1.0', 'artifacts': [{'report': {'path': f'{NOMBRE}.Report'}}], 'settings': {'enableAutoRecovery': True}},
        indent=2), encoding='utf-8')
    (modelo / 'definition.pbism').write_text(json.dumps({'version': '4.0', 'settings': {}}, indent=2), encoding='utf-8')
    (defin / 'database.tmdl').write_text('database\n\tcompatibilityLevel: 1567\n', encoding='utf-8')
    nombres = [t[0] for t in TABLAS] + ['Teoria']
    (defin / 'model.tmdl').write_text('\n'.join([
        'model Model', f'{T}culture: en-US', f'{T}defaultPowerBIDataSourceVersion: powerBI_V3', f'{T}sourceQueryCulture: en-US',
        f'{T}dataAccessOptions', f'{T*2}legacyRedirects', f'{T*2}returnErrorValuesAsNull', '',
        f'annotation PBI_QueryOrder = {json.dumps(["CarpetaDatos"] + nombres)}', '',
        *[f'ref table {n}' for n in nombres], '', 'ref expression CarpetaDatos', '']), encoding='utf-8')
    (defin / 'expressions.tmdl').write_text('\n'.join([
        f'expression CarpetaDatos = "{carpeta_por_omision}" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]',
        f'{T}lineageTag: {tag()}', '', f'{T}annotation PBI_ResultType = Text', '']), encoding='utf-8')
    for nombre, archivo, columnas, oculta in TABLAS:
        (defin / 'tables' / f'{nombre}.tmdl').write_text(tabla_tmdl(nombre, archivo, columnas, oculta), encoding='utf-8')
    (defin / 'tables' / 'Teoria.tmdl').write_text(tabla_medidas(), encoding='utf-8')
    (reporte / 'definition.pbir').write_text(json.dumps({
        'version': '1.0', 'datasetReference': {'byPath': {'path': f'../{NOMBRE}.SemanticModel'}, 'byConnection': None}},
        indent=2), encoding='utf-8')
    # Tema base: Power BI lo exige (sin él falla con «Cannot read properties of undefined (reading 'customTheme')»).
    tema = 'CY24SU10'
    temas = reporte / 'StaticResources' / 'SharedResources' / 'BaseThemes'
    temas.mkdir(parents=True)
    (temas / f'{tema}.json').write_text(json.dumps({
        'name': tema, 'dataColors': ['#118DFF', '#12239E', '#E66C37', '#6B007B', '#E044A7', '#744EC2', '#D9B300', '#D64550'],
        'foreground': '#252423', 'background': '#FFFFFF', 'tableAccent': '#118DFF'}, indent=2), encoding='utf-8')
    (reporte / 'report.json').write_text(json.dumps({
        'config': json.dumps({'version': '5.59', 'themeCollection': {'baseTheme': {'name': tema, 'version': '5.61', 'type': 2}},
                              'activeSectionIndex': 0, 'defaultDrillFilterOtherVisuals': True, 'linguisticSchemaSyncVersion': 0,
                              'settings': {'useNewFilterPaneExperience': True, 'allowChangeFilterTypes': True,
                                           'useStylableVisualContainerHeader': True, 'exportDataMode': 1},
                              'objects': {}}),
        'layoutOptimization': 0,
        'resourcePackages': [{'resourcePackage': {'disabled': False, 'name': 'SharedResources', 'type': 2,
                                                  'items': [{'name': tema, 'path': f'BaseThemes/{tema}.json', 'type': 202}]}}],
        'sections': [{'name': 'Teoria', 'displayName': 'Teoría', 'displayOption': 1, 'filters': '[]', 'ordinal': 0,
                      'height': 720.0, 'width': 1280.0, 'config': '{}', 'visualContainers': []}]}, indent=2), encoding='utf-8')
    shutil.copytree(datos, destino / 'datos')
    # Respaldo: el modelo completo como script para la vista TMDL de Power BI Desktop (informe en blanco → Vista TMDL →
    # pegar → Aplicar). Crea el parámetro, las 10 tablas y las medidas.
    partes = [(defin / 'expressions.tmdl').read_text(encoding='utf-8')]
    partes += [(defin / 'tables' / f'{n}.tmdl').read_text(encoding='utf-8') for n in nombres]
    cuerpo = '\n\n'.join('\n'.join((T + l) if l.strip() else '' for l in p.splitlines()) for p in partes)
    (destino / 'modelo_para_vista_TMDL.tmdl').write_text('createOrReplace\n\n' + cuerpo + '\n', encoding='utf-8')
    # Las mismas medidas, para pegarlas a mano si hiciera falta.
    (destino / 'medidas.dax').write_text('\n\n'.join(f"-- {n}\n{n} =\n{d}" for n, _, d in MEDIDAS) + '\n', encoding='utf-8')
    print(f'Proyecto en {destino}')


if __name__ == '__main__':
    main()
