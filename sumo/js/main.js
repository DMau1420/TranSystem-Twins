// =====================================================================
// ARRANQUE
// =====================================================================
async function init() {
    initMap();
    const geojson = await cargarRed();
    if (geojson) agregarCalles(geojson);

    document.getElementById('btn-simular').addEventListener('click', dispararSimulacion);
    document.getElementById('btn-cerrar-resultado').addEventListener('click', () => {
        document.getElementById('modal-resultado').style.display = 'none';
    });
}

document.addEventListener('DOMContentLoaded', init);
