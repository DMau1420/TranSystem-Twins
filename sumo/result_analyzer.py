import xml.etree.ElementTree as ET  # Libreria para abrir XML


def procesar_resultados(archivo):
    """
    Procesa los resultados SOLO después de verificar el archivo.

    Las claves del diccionario que se regresa deben coincidir EXACTO con
    las que lee el frontend (ver el bloque que arma el modal de
    "Resultados de la simulación"):
        - tiempo_promedio_espera
        - velocidad_promedio
        - longitud_max_fila
        - vehiculos_atendidos
    """

    try:
        tree = ET.parse(archivo)
        root = tree.getroot()

        print("\n" + "=" * 50)
        print(" ESTADISTICAS DEL ESCENARIO")
        print("=" * 50)

        vehiculos = root.findall("tripinfo")

        if len(vehiculos) == 0:
            print("No se encontraron vehículos en la simulación")
            return None

        duraciones = []
        espera = []
        velocidades = []  # m/s, una por vehículo: routeLength / duration

        for v in vehiculos:
            duracion = float(v.attrib["duration"])
            duraciones.append(duracion)
            espera.append(float(v.attrib["waitingTime"]))

            # routeLength viene en metros; si algún tripinfo llegara con
            # duration=0 (no debería pasar, pero por seguridad) se descarta
            # para no dividir entre cero.
            largo_ruta = float(v.attrib.get("routeLength", 0))
            if duracion > 0:
                velocidades.append(largo_ruta / duracion)

        tiempo_promedio_recorrido = sum(duraciones) / len(duraciones)
        tiempo_promedio_espera = sum(espera) / len(espera)

        # m/s -> km/h
        velocidad_promedio = (
            (sum(velocidades) / len(velocidades)) * 3.6 if velocidades else None
        )

        print(f"Vehículos simulados: {len(vehiculos)}")
        print(f"Tiempo promedio de recorrido: {tiempo_promedio_recorrido:.2f} segundos")
        print(f"Espera promedio: {tiempo_promedio_espera:.2f} segundos")
        if velocidad_promedio is not None:
            print(f"Velocidad promedio: {velocidad_promedio:.2f} km/h")
        print("=" * 50 + "\n")

        return {
            "vehiculos_atendidos": len(vehiculos),
            "tiempo_promedio_espera": round(tiempo_promedio_espera, 2),
            "velocidad_promedio": round(velocidad_promedio, 2) if velocidad_promedio is not None else None,
            # TODO: "longitud máxima de fila" (cola de vehículos detenidos)
            # NO se puede calcular a partir de tripinfo.xml -- ese archivo
            # solo tiene datos agregados por viaje YA TERMINADO, no el
            # estado de la simulación en el tiempo. Para calcular esto de
            # verdad hace falta que simulation_engine.py corra SUMO con
            # --queue-output (o detectores E2 de ocupación) y que aquí se
            # parsee ese archivo aparte para sacar el máximo histórico.
            # Por ahora se regresa None explícitamente -- el frontend ya
            # maneja ese caso mostrando "-".
            "longitud_max_fila": None,
            # Se conserva por si algo más del sistema todavía lo usa,
            # aunque el frontend actual no lo lee.
            "tiempo_promedio_recorrido": round(tiempo_promedio_recorrido, 2),
        }

    except ET.ParseError as e:
        print(f"ERROR: No se pudo parsear tripinfo.xml: {e}")
        return None
    except Exception as e:
        print(f"ERROR inesperado: {e}")
        return None