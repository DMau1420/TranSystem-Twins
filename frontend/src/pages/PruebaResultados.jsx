import ResultadosPanel from '../components/resultados/ResultadosPanel';

let datos = [
  { id: 1, creado_en: '2026-11-20T10:00:00Z', estado: 'completada', vehiculos_hora: 1200, tiempo_medio_s: 84 },
  { id: 2, creado_en: '2026-11-22T16:30:00Z', estado: 'completada', vehiculos_hora: 1350, tiempo_medio_s: 71 },
];
const espera = (v) => new Promise((r) => setTimeout(() => r(v), 400));

const apiFalsa = {
  listarResultados: () => espera([...datos]),
  obtenerResultado: (id) => espera({ ...datos.find((d) => d.id === id), metricas: { colas_max: 14 } }),
  eliminarResultado: (id) => { datos = datos.filter((d) => d.id !== id); return espera({ ok: true }); },
};

export default function PruebaResultados() {
  return (
    <div style={{ background: '#07090d', minHeight: '100vh', padding: 16 }}>
      <ResultadosPanel escenarioId={1} api={apiFalsa} />
    </div>
  );
}