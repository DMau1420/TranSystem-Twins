// src/scenario/mockResultado.js
// Resultados INVENTADOS, mientras el backend no tenga /escenarios/crear ni
// /resultados reales. No es una simulación real de tráfico — son números
// que se mueven de forma razonable según la demanda y duración que
// configuraste, para que el flujo se vea y se sienta completo mientras se
// espera al backend. Bórralo (y donde se use) en cuanto haya datos reales.
//
// jitter(base, pct) agrega variación aleatoria de +/- pct% para que cada
// corrida se vea distinta, como lo haría una simulación real.
const jitter = (base, pct = 0.12) => base * (1 + (Math.random() * 2 - 1) * pct);
const round = (n, decimals = 0) => Number(n.toFixed(decimals));

export function generarResultadoCoherente(scenario) {
  const demanda = scenario?.demandaVehicular > 0 ? scenario.demandaVehicular : 100; // fallback razonable
  const duracionHoras = (scenario?.duracionSegundos ?? 3600) / 3600;

  const esperados = demanda * duracionHoras;
  const eficiencia = 0.82 + Math.random() * 0.15; // 82%-97% de lo esperado llega a su destino
  const vehiculosAtendidos = Math.max(1, round(esperados * eficiencia));

  // A más demanda, un poco más de congestión: recorrido, espera y fila suben;
  // velocidad baja. Los coeficientes son solo para que se muevan juntos, no
  // una física real.
  const congestion = Math.min(1, demanda / 400);

  return {
    vehiculos_atendidos: vehiculosAtendidos,
    tiempo_promedio_recorrido: round(jitter(150 + congestion * 150), 2),
    espera_promedio: round(jitter(4 + congestion * 20), 2),
    velocidad_promedio: round(jitter(60 - congestion * 30), 2),
    fila_maxima: round(jitter(3 + congestion * 18), 2),
  };
}