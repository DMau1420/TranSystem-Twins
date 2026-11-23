"""
verificar_secuencias.py: comprueba que, tras REDUCIR carriles junto a un semáforo, cada enlace
que sobrevive muestra la MISMA secuencia de luces (a lo largo de las fases) que su enlace
original en la red base.

Esto detecta lo que "Consistencia state/enlaces" no puede ver: un renumerado corrido una
posición deja el número de caracteres correcto pero las luces cambiadas de enlace.

Uso (desde sumo/):
    python verificar_secuencias.py <red_nueva.net.xml> <via> <carriles_menos>
Ejemplo (sobre el resultado del experimento):
    python verificar_secuencias.py data\\proyectos\\3\\prueba_reduccion_semaforo\\red_prueba.net.xml 128250766 1
"""
import sys
import xml.etree.ElementTree as ET

from escenario_calles import pertenece_a_via

BASE_POR_DEFECTO = "data/proyectos/3/red_base.net.xml"
NO_VIALES = ("internal", "crossing", "walkingarea")


def reducciones_de_via(ruta_base, via, menos):
    """{tramo: (carriles_antes, carriles_despues)} para una reducción de `menos` carriles."""
    reducciones = {}
    for e in ET.parse(ruta_base).getroot().findall("edge"):
        if e.get("function") in NO_VIALES or not pertenece_a_via(e.get("id"), via):
            continue
        antes = len(e.findall("lane"))
        despues = max(1, antes - menos)
        if despues < antes:
            reducciones[e.get("id")] = (antes, despues)
    return reducciones


def _leer(ruta):
    """Regresa ({(tl, from, fromLane, to, toLane): linkIndex}, {tl: [state de cada fase]})."""
    raiz = ET.parse(ruta).getroot()
    fases = {}
    for logica in raiz.findall("tlLogic"):
        fases.setdefault(logica.get("id"), [p.get("state") for p in logica.findall("phase")])
    enlaces = {}
    for c in raiz.findall("connection"):
        if c.get("tl") and c.get("linkIndex") is not None:
            clave = (c.get("tl"), c.get("from"), int(c.get("fromLane")), c.get("to"), int(c.get("toLane")))
            enlaces[clave] = int(c.get("linkIndex"))
    return enlaces, fases


def _secuencia(fases, tl, indice):
    """Las luces de un enlace a lo largo de todas las fases, ej. 'GGrrry'."""
    return "".join(estado[indice] for estado in fases[tl])


def _clave_nueva(clave, reducciones):
    """A qué enlace se convierte un enlace de la base tras la reducción."""
    tl, o, f, d, t = clave
    nf = min(f, reducciones[o][1] - 1) if o in reducciones else f
    nt = min(t, reducciones[d][1] - 1) if d in reducciones else t
    return (tl, o, nf, d, nt)


def verificar_secuencias(ruta_base, ruta_nueva, reducciones):
    """Imprime el resultado y regresa la lista de problemas (vacía si todo coincide)."""
    base_enlaces, base_fases = _leer(ruta_base)
    nueva_enlaces, nueva_fases = _leer(ruta_nueva)

    # A qué enlace de la base corresponde cada enlace nuevo (si varios se fusionan,
    # la referencia es el que no cambió de carril)
    referencia = {}
    for clave in base_enlaces:
        nueva = _clave_nueva(clave, reducciones)
        if nueva not in referencia or nueva == clave:
            referencia[nueva] = clave

    problemas = []
    for nueva in referencia:
        if nueva not in nueva_enlaces:
            problemas.append(f"SE PERDIÓ el enlace {nueva}")
    for nueva, indice in nueva_enlaces.items():
        if nueva not in referencia:
            problemas.append(f"enlace que no existía en la base: {nueva}")
            continue
        origen = referencia[nueva]
        esperada = _secuencia(base_fases, origen[0], base_enlaces[origen])
        obtenida = _secuencia(nueva_fases, nueva[0], indice)
        if esperada != obtenida:
            problemas.append(f"LUCES DISTINTAS en {nueva}: base {esperada} / ahora {obtenida}")

    print("\n=== SECUENCIAS DE LUCES (contra la base) ===")
    print(f"  Enlaces en la base: {len(base_enlaces)} | ahora: {len(nueva_enlaces)} | "
          f"comparados: {len(nueva_enlaces) - sum(1 for p in problemas if p.startswith('enlace que no'))}")
    for p in problemas:
        print("  PROBLEMA", p)
    if not problemas:
        print("  Todos los enlaces conservan exactamente las mismas luces.")
    return problemas


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit()
    ruta_nueva, via, menos = sys.argv[1], sys.argv[2], int(sys.argv[3])
    base = sys.argv[4] if len(sys.argv) > 4 else BASE_POR_DEFECTO
    verificar_secuencias(base, ruta_nueva, reducciones_de_via(base, via, menos))