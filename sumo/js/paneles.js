// =====================================================================
// PANELES HTML: edición de calle, edición de semáforo y resultados
// =====================================================================
function mostrarEstado(mensaje) {
    const el = document.getElementById('estado');
    if (!el) return;
    el.textContent = mensaje;
    el.className = 'visible';
}

function mostrarPanelEdicion(feature, layer) {
    const p = feature.properties;
    const badge = calleModificada(p) ? '<div class="badge-modificada">Modificada en este escenario</div>' : '';

    document.getElementById('contenido-panel').innerHTML = `
        <div class="nombre-calle">${p.nombre_calle}</div>
        <div class="edge-id">ID: ${p.edge_id}</div>
        ${badge}
        <div class="campo">
            <label>Número de carriles</label>
            <input type="number" id="input-carriles" value="${p.carriles}" min="1" max="10" />
            <div class="info" id="info-carriles">Valor original: ${originalesCalles.get(p.edge_id).carriles}</div>
        </div>
        <div class="campo">
            <label>Velocidad máxima (km/h)</label>
            <input type="number" id="input-velocidad" value="${p.velocidad_max}" min="5" max="120" step="5" />
            <div class="info" id="info-velocidad">Valor original: ${originalesCalles.get(p.edge_id).velocidad_max} km/h</div>
        </div>
        <div class="campo">
            <label>Tipo de vía</label>
            <input type="text" value="${p.tipo || 'desconocido'}" readonly disabled />
        </div>
        <div class="campo">
            <label>Longitud (metros)</label>
            <input type="text" value="${p.longitud} m" readonly disabled />
        </div>
        <div class="btn-group">
            <button class="btn-primary" id="btn-guardar">Guardar cambios</button>
            <button class="btn-secondary" id="btn-restaurar">Restaurar</button>
        </div>
        <div id="estado"></div>`;

    document.getElementById('btn-guardar').addEventListener('click', () => guardarCambios(feature, layer));
    document.getElementById('btn-restaurar').addEventListener('click', () => restaurarCambios(feature, layer));
}

// fasesOverride: lo usa "Restaurar" para mostrar las fases originales sin tocar feature.properties
function mostrarPanelEdicionSemaforo(feature, layer, fasesOverride) {
    const p = feature.properties;
    const contenedor = document.getElementById('contenido-panel');
    const idsPrograma = Object.keys(p.programas || {});

    if (idsPrograma.length === 0) {
        contenedor.innerHTML = `
            <div class="nombre-calle">Semáforo ${p.tls_id}</div>
            <div class="edge-id">Tipo: ${p.tipo_control}</div>
            <p class="vacio" style="padding:20px 0;">
                Este semáforo no tiene un programa de fases disponible
                (netconvert no pudo construirle uno). No hay nada que editar aquí.
            </p>`;
        return;
    }

    const idPrograma = idsPrograma[0];
    const fases = fasesOverride || p.programas[idPrograma];
    const badge = semaforoModificado(p) ? '<div class="badge-modificada">Modificado en este escenario</div>' : '';

    const filasFases = fases.map((fase, i) => `
        <div class="fase-item">
            <div class="fase-titulo">Fase ${i}</div>
            <div class="campo" style="margin-bottom:6px;">
                <label>Duración (segundos)</label>
                <input type="number" class="input-fase-duracion" data-indice="${i}"
                       value="${fase.duracion}" min="1" max="300" />
            </div>
            <div class="fase-estado">estado: ${fase.estado}</div>
        </div>`).join('');

    contenedor.innerHTML = `
        <div class="nombre-calle">Semáforo ${p.tls_id}</div>
        <div class="edge-id">Tipo: ${p.tipo_control} · Programa: ${idPrograma}</div>
        ${badge}
        <div class="campo"><label>Calles entrantes</label>
            <input type="text" value="${p.calles_entrantes.length}" readonly disabled /></div>
        <div class="campo"><label>Calles salientes</label>
            <input type="text" value="${p.calles_salientes.length}" readonly disabled /></div>
        <div class="aviso-static">
            Al guardar, este semáforo pasa a <strong>tiempo fijo</strong> con las duraciones
            que definas aquí abajo: deja de ajustarse solo según el tráfico. Los semáforos
            que no edites siguen funcionando de forma automática, sin cambios.
        </div>
        <h2 style="margin-top:8px;">Fases del programa</h2>
        ${filasFases}
        <div class="btn-group">
            <button class="btn-primary" id="btn-guardar-semaforo">Guardar cambios</button>
            <button class="btn-secondary" id="btn-restaurar-semaforo">Restaurar</button>
        </div>
        <div id="estado"></div>`;

    document.getElementById('btn-guardar-semaforo').addEventListener('click', () => guardarCambiosSemaforo(feature, layer));
    document.getElementById('btn-restaurar-semaforo').addEventListener('click', () => {
        const original = originalesSemaforos.get(p.tls_id);
        const idOriginal = original ? Object.keys(original)[0] : null;
        mostrarPanelEdicionSemaforo(feature, layer, idOriginal ? original[idOriginal] : null);
        mostrarEstado('Valores restaurados al original (sin guardar todavía)');
    });
}

function mostrarResultado(indicadores) {
    const contenedor = document.getElementById('contenido-resultado');

    if (indicadores.error) {
        contenedor.innerHTML = `
            <strong>Error al simular</strong>
            <p style="font-size:13px; color:var(--muted)">${indicadores.error}</p>`;
    } else {
        contenedor.innerHTML = `
            <strong>Resultados de la simulación</strong>
            <div style="margin-top:10px; font-size:13px; line-height:1.8;">
                <div>Tiempo promedio de espera: <strong>${indicadores.tiempo_promedio_espera ?? '-'} s</strong></div>
                <div>Velocidad promedio: <strong>${indicadores.velocidad_promedio ?? '-'} km/h</strong></div>
                <div>Longitud máxima de fila: <strong>${indicadores.longitud_max_fila ?? '-'} m</strong></div>
                <div>Vehículos atendidos: <strong>${indicadores.vehiculos_atendidos ?? '-'}</strong></div>
            </div>`;
    }
    document.getElementById('modal-resultado').style.display = 'block';
}
