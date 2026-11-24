import { useState } from 'react';
import FlujosEditor from '../components/demanda/FlujosEditor';
import CsvFlujosUploader from '../components/demanda/CsvFlujosUploader';
import { validarFlujo } from '../utils/flujosCsv';

export default function PruebaDemanda() {
  const [flujos, setFlujos] = useState([]);
  const hayErrores = flujos.some((f) => validarFlujo(f).length > 0);

  return (
    <div style={{ background: '#07090d', minHeight: '100vh', padding: 16 }}>
      <CsvFlujosUploader onImportar={(n) => setFlujos((p) => [...p, ...n])} />
      <FlujosEditor value={flujos} onChange={setFlujos} edges={['E1', 'E2', 'E3', 'E4']} />
      <pre style={{ color: '#7f95a0' }}>
        {hayErrores ? 'Hay filas por corregir' : 'Listo para enviar'}
        {'\n'}
        {JSON.stringify(flujos, null, 2)}
      </pre>
    </div>
  );
}