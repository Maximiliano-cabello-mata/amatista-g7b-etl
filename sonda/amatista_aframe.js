/* Sonda manual de Amatista. Cargar este archivo solo define la herramienta. */
globalThis.AmatistaTelemetria = (() => {
  async function medir({escena = document.querySelector("a-scene"), segundos = 5,
                        entorno = "equipo_voluntario", carga = "otra"} = {}) {
    const render = escena?.renderer?.info?.render;
    if (!escena?.isPlaying || !Number.isFinite(render?.frame)) throw Error("Abre una escena A-Frame en reproducción");
    if (!["laboratorio", "github_actions", "equipo_voluntario"].includes(entorno)) throw Error("Entorno desconocido");
    if (!["cubo_basico", "practica", "otra"].includes(carga)) throw Error("Carga desconocida");
    if (!Number.isInteger(segundos) || segundos < 3 || segundos > 30) throw Error("Duración de 3 a 30 segundos");
    const version = globalThis.AFRAME?.version;
    if (!version) throw Error("Falta la versión de A-Frame");
    const intervalos = [];
    let maxLlamadas = 0;
    let maxTriangulos = 0;
    let cuadro = render.frame;
    let inicio;
    let anterior;
    let raf;
    let temporizador;
    let alOcultar;
    try {
      await new Promise((resolve, reject) => {
        const detener = () => reject(Error("Medición interrumpida o escena no visible"));
        alOcultar = () => { if (document.hidden) detener(); };
        document.addEventListener("visibilitychange", alOcultar);
        temporizador = setTimeout(detener, (segundos + 10) * 1000);
        function observar(t) {
          if (document.hidden || !escena.isConnected || !escena.isPlaying || escena.renderer.xr.isPresenting) {
            detener();
            return;
          }
          if (render.frame !== cuadro) {
            cuadro = render.frame;
            inicio ??= t;
            if (anterior !== undefined && t > anterior) intervalos.push(Number((t - anterior).toFixed(3)));
            anterior = t;
            maxLlamadas = Math.max(maxLlamadas, render.calls);
            maxTriangulos = Math.max(maxTriangulos, render.triangles);
            if (t - inicio >= segundos * 1000) {
              resolve();
              return;
            }
          }
          raf = requestAnimationFrame(observar);
        }
        raf = requestAnimationFrame(observar);
      });
    } finally {
      clearTimeout(temporizador);
      cancelAnimationFrame(raf);
      document.removeEventListener("visibilitychange", alOcultar);
    }
    return {contrato: "amatista.sonda_aframe/1", fecha: new Date().toISOString(), version,
            entorno, carga, intervalos_ms: intervalos, max_llamadas: maxLlamadas, max_triangulos: maxTriangulos};
  }

  function descargar(medicion) {
    const url = URL.createObjectURL(new Blob([JSON.stringify(medicion)], {type: "application/json"}));
    const enlace = document.createElement("a");
    enlace.href = url;
    enlace.download = "amatista-aframe-" + Date.now() + ".json";
    enlace.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return {medir, descargar};
})();
