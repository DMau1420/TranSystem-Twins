import sumolib

TLS = "cluster_11514661659_372948820_372948824"
for nombre, ruta in (("BASE", "data/proyectos/3/red_base.net.xml"),
                     ("EXTENSIÓN", "data/proyectos/3/prueba_extension/red_prueba.net.xml")):
    red = sumolib.net.readNet(ruta, withPrograms=True)
    enlaces = red.getTLS(TLS).getConnections()
    print(f"{nombre}: {len(enlaces)} enlaces controlados")
    if nombre == "EXTENSIÓN":
        for entrada, salida, indice in sorted(enlaces, key=lambda e: e[2]):
            if entrada.getID().startswith("128250766#0_4"):
                print(f"  carril nuevo: {entrada.getID()} -> {salida.getID()} (linkIndex {indice})")