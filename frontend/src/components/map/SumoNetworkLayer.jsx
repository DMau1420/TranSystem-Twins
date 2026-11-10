import { useEffect, useMemo } from 'react';
import { CircleMarker, Polyline, Tooltip, useMap } from 'react-leaflet';
import L from 'leaflet';
import { useSumoNetwork } from '../../hooks/useSumoNetwork';
import { estiloCalle, estiloSemaforo, etiquetaCalle } from '../../utils/sumoNetwork';

// Un solo renderer canvas compartido: con ~1,800 elementos es mucho más fluido que SVG.
const canvas = L.canvas({ padding: 0.5 });

function Capa({
  soloPrincipales,
  mostrarSemaforos,
  callesModificadas,
  semaforosModificados,
  selectedId,
  onCalleClick,
  onSemaforoClick,
  onLoad,
  ajustarVista,
}) {
  const map = useMap();
  const { red, fuente } = useSumoNetwork();

  useEffect(() => {
    if (red && onLoad) onLoad(red, fuente);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [red]);

  useEffect(() => {
    if (red && ajustarVista) map.fitBounds(L.latLngBounds(red.calles.flatMap((c) => c.puntos)));
  }, [red, ajustarVista, map]);

  const calles = useMemo(() => red?.calles ?? [], [red]);

  if (!red) return null;
  return (
    <>
      {calles.map((c) => (
        <Polyline
          key={c.id}
          positions={c.puntos}
          renderer={canvas}
          pathOptions={estiloCalle(c, {
            seleccionada: c.id === selectedId,
            modificada: callesModificadas?.has(c.id),
            soloPrincipales,
          })}
          eventHandlers={
            onCalleClick
              ? { click: (e) => { L.DomEvent.stopPropagation(e); onCalleClick(c.id, c); } }
              : undefined
          }
        >
          <Tooltip sticky>{`${etiquetaCalle(c)} · ${c.carriles} carriles · ${c.velocidad} km/h`}</Tooltip>
        </Polyline>
      ))}
      {mostrarSemaforos &&
        red.semaforos.map((s) => (
          <CircleMarker
            key={s.id}
            center={s.pos}
            renderer={canvas}
            pathOptions={estiloSemaforo({
              seleccionado: s.id === selectedId,
              modificado: semaforosModificados?.has(s.id),
            })}
            radius={estiloSemaforo({ seleccionado: s.id === selectedId }).radius}
            eventHandlers={
              onSemaforoClick
                ? { click: (e) => { L.DomEvent.stopPropagation(e); onSemaforoClick(s.id, s); } }
                : undefined
            }
          >
            <Tooltip>{`// SEMÁFORO // ${s.id}`}</Tooltip>
          </CircleMarker>
        ))}
    </>
  );
}

/**
 * Capa de la red SUMO (calles + semáforos).
 * - visible: igual que la capa anterior; si es false no dibuja ni descarga la red.
 * - selectedId: id de la calle o semáforo seleccionado (se resalta en magenta).
 * - onCalleClick(id, calle) / onSemaforoClick(id, semaforo): para conectar el editor.
 * - callesModificadas / semaforosModificados: Set de ids con cambios en el escenario.
 * - onLoad(red, fuente): entrega la red convertida (idxCalles, idxSemaforos...).
 */
export default function SumoNetworkLayer({
  visible = true,
  soloPrincipales = false,
  mostrarSemaforos = true,
  ajustarVista = false,
  ...resto
}) {
  if (!visible) return null;
  return (
    <Capa
      soloPrincipales={soloPrincipales}
      mostrarSemaforos={mostrarSemaforos}
      ajustarVista={ajustarVista}
      {...resto}
    />
  );
}