// =====================================================================
// ACCIONES: comunicación con el servidor (cargar, guardar, simular)
// =====================================================================
async function cargarRed() {
    try {
        const response = await fetch('/red');

        if (response.status === 409) {
            document.getElementById('cargando').innerHTML = `
                La red todavía no se ha importado en esta sesión.<br>
                Da clic en <strong>"Simular escenario"</strong> para descargarla
                (la primera vez puede tardar unos segundos).`;
            return null;
        }
        if (!response.ok) throw new Error('Error al cargar la red');

        redData = await response.json();
        document.getElementById('cargando').style.display = 'none';

        const totalCalles = redData.features.filter(f => f.properties.tipo_elemento === 'calle').length;
        document.getElementById('contador-calles').textContent = `${totalCalles} calles`;
        return redData;
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('cargando').innerHTML = `Error al cargar la red<br><small>${error.message}</small>`;
        return null;
    }
}

// PATCH genérico; lanza Error con el mensaje del servidor si lo rechaza
async function enviarPatch(url, cuerpo) {
    const respuesta = await fetch(url, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cuerpo)
    });
    if (!respuesta.ok) {
        const err = await respuesta.json().catch(() => ({}));
        throw new Error(err.error || 'El servidor rechazó el cambio');
    }
}

async function guardarCambios(feature, layer) {
    const p = feature.properties;
    const carriles = parseInt(document.getElementById('input-carriles').value, 10);
    const velocidad = parseFloat(document.getElementById('input-velocidad').value);

    if (isNaN(carriles) || carriles < 1 || carriles > 10) return mostrarEstado('Los carriles deben ser entre 1 y 10');
    if (isNaN(velocidad) || velocidad < 5 || velocidad > 120) return mostrarEstado('La velocidad debe ser entre 5 y 120 km/h');

    mostrarEstado('Guardando...');
    try {
        await enviarPatch(`/infraestructura/${p.edge_id}`, { carriles, velocidad_max: velocidad });

        // Solo cambia el estado "de trabajo"; los originales quedan intactos para Restaurar
        p.carriles = carriles;
        p.velocidad_max = velocidad;
        layer.closePopup();
        layer.bindPopup(popupCalle(p));
        actualizarContadorCambios();

        const o = originalesCalles.get(p.edge_id);
        mostrarEstado('Cambios guardados en el servidor');
        document.getElementById('info-carriles').textContent = `Valor guardado: ${p.carriles} (original: ${o.carriles})`;
        document.getElementById('info-velocidad').textContent = `Valor guardado: ${p.velocidad_max} km/h (original: ${o.velocidad_max} km/h)`;
    } catch (error) {
        mostrarEstado(`No se pudo guardar: ${error.message}`);
    }
}

async function guardarCambiosSemaforo(feature, layer) {
    const p = feature.properties;
    const fases = [];

    for (const input of document.querySelectorAll('.input-fase-duracion')) {
        const duracion = parseInt(input.value, 10);
        if (isNaN(duracion) || duracion < 1 || duracion > 300) {
            return mostrarEstado('Cada duración debe ser entre 1 y 300 segundos');
        }
        fases.push({ indice: parseInt(input.dataset.indice, 10), duracion });
    }

    mostrarEstado('Guardando...');
    try {
        await enviarPatch(`/semaforo/${p.tls_id}`, { fases });

        const idPrograma = Object.keys(p.programas)[0];
        fases.forEach(f => { p.programas[idPrograma][f.indice].duracion = f.duracion; });
        actualizarContadorCambios();

        mostrarEstado('Cambios guardados. Este semáforo correrá a tiempo fijo en la próxima simulación.');
    } catch (error) {
        mostrarEstado(`No se pudo guardar: ${error.message}`);
    }
}

// Restaurar: rellena el formulario con el valor ORIGINAL (no guarda nada todavía)
function restaurarCambios(feature) {
    const original = originalesCalles.get(feature.properties.edge_id);
    if (!original) return;
    document.getElementById('input-carriles').value = original.carriles;
    document.getElementById('input-velocidad').value = original.velocidad_max;
    mostrarEstado('Valores restaurados al original (sin guardar todavía)');
}

async function dispararSimulacion() {
    const boton = document.getElementById('btn-simular');
    const textoOriginal = boton.textContent;
    boton.textContent = 'Simulando...';
    boton.disabled = true;

    try {
        const respuesta = await fetch('/simular', { method: 'POST' });
        const datos = await respuesta.json();
        if (!respuesta.ok) throw new Error(datos.error || 'Error al simular');

        mostrarResultado(datos);

        if (!capaRed) {   // primera simulación: ya existe la red, se dibuja
            document.getElementById('cargando').innerHTML = 'Cargando red de calles...';
            document.getElementById('cargando').style.display = 'block';
            const geojson = await cargarRed();
            if (geojson) agregarCalles(geojson);
        }
    } catch (error) {
        mostrarResultado({ error: error.message });
    } finally {
        boton.textContent = textoOriginal;
        boton.disabled = false;
    }
}
