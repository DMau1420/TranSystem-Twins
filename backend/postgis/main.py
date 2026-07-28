import geopandas as gpd
from sqlalchemy import create_engine, text

def main():
    print("corriendo python...")

    conn_str = "postgresql://gis:password@localhost:5432/gis"
    engine = create_engine(conn_str)

    try:
        with engine.connect() as conn:
            version = conn.execute(text("SELECT PostGIS_Full_Version();")).scalar()
            print("si conecto")
            print(f"postgis version:{version}")
        query = """
            SELECT
                1 AS id,
                'Punto de prueba' AS nombre, 
                ST_SetSRID(ST_MakePoint(-99.1332, 19.4326), 4326) AS geom;
        """

        gdf = gpd.read_postgis(query, con=engine, geom_col='geom')

        print("===========================")
        print(gdf)
        print("\ntipo de objeto:", type(gdf))
        print("sistema de coordenadas (CRS)", gdf.crs)

    except Exception as e:
        print("Fallo critico!!!!!!")
        print(e)

if __name__ == '__main__':
    main()
