import pandas as pd
import numpy as np
import os

# -----------------------------------------------------------------------------
# 1. DICCIONARIOS DE RESPALDO (U.S. CENSUS BUREAU 2020 ZCTA & GAZETTEER FILES)
# -----------------------------------------------------------------------------
# Coordenadas reales del centroide de cada Código Postal (ZCTA)
AUSTIN_COORDS = {
    '78610': (30.0754, -97.8384), '78613': (30.5057, -97.8306), '78617': (30.1706, -97.6186),
    '78652': (30.1332, -97.8682), '78653': (30.3444, -97.5332), '78660': (30.4398, -97.6009),
    '78681': (30.5284, -97.7126), '78701': (30.2713, -97.7426), '78702': (30.2625, -97.7164),
    '78703': (30.2828, -97.7618), '78704': (30.2452, -97.7686), '78705': (30.2906, -97.7397),
    '78712': (30.2857, -97.7348), '78717': (30.4907, -97.7685), '78719': (30.1311, -97.6744),
    '78721': (30.2678, -97.6853), '78722': (30.2891, -97.7161), '78723': (30.3073, -97.6826),
    '78724': (30.3013, -97.6133), '78725': (30.2312, -97.5843), '78726': (30.4431, -97.8488),
    '78727': (30.4326, -97.7162), '78728': (30.4578, -97.6888), '78729': (30.4571, -97.7675),
    '78730': (30.3664, -97.8385), '78731': (30.3475, -97.7645), '78732': (30.3639, -97.9009),
    '78733': (30.3168, -97.8761), '78734': (30.3683, -97.9749), '78735': (30.2465, -97.8596),
    '78736': (30.2343, -97.9351), '78737': (30.1989, -97.9626), '78738': (30.3175, -98.0055),
    '78739': (30.1706, -97.8936), '78741': (30.2335, -97.7196), '78742': (30.2474, -97.6705),
    '78744': (30.1837, -97.7408), '78745': (30.2076, -97.7946), '78746': (30.2818, -97.8172),
    '78747': (30.1189, -97.7471), '78748': (30.1583, -97.8329), '78749': (30.2091, -97.8601),
    '78750': (30.4243, -97.8288), '78751': (30.3093, -97.7259), '78752': (30.3341, -97.7088),
    '78753': (30.3791, -97.6749), '78754': (30.3663, -97.6322), '78756': (30.3135, -97.7402),
    '78757': (30.3551, -97.7297), '78758': (30.3848, -97.7099), '78759': (30.4042, -97.7554)
}

# Población censal real (2020 Decennial Census)
POBLACION_CENSO = {
    '78610': 38242, '78613': 85474, '78617': 29631, '78652': 6124,  '78653': 23971,
    '78660': 98647, '78681': 30145, '78701': 9534,  '78702': 23891, '78703': 21820,
    '78704': 47926, '78705': 33177, '78712': 786,   '78717': 29641, '78719': 1954,
    '78721': 13426, '78722': 7291,  '78723': 34327, '78724': 27814, '78725': 8493,
    '78726': 14457, '78727': 30048, '78728': 22534, '78729': 30376, '78730': 9102,
    '78731': 28269, '78732': 18012, '78733': 8962,  '78734': 20743, '78735': 17820,
    '78736': 8847,  '78737': 18903, '78738': 18406, '78739': 20436, '78741': 52917,
    '78742': 612,   '78744': 48753, '78745': 62451, '78746': 28659, '78747': 21475,
    '78748': 49914, '78749': 37812, '78750': 31089, '78751': 14856, '78752': 20568,
    '78753': 58514, '78754': 24719, '78756': 13914, '78757': 24108, '78758': 48123, '78759': 42805
}

# 9 ZIP Codes atípicos excluidos (cobertura parcial de red de agua municipal respecto al ZIP entero)
ZIPS_ANOMALOS = {'78610', '78613', '78653', '78660', '78681', '78725', '78732', '78737', '78738'}

def generar_dataset_definitivo():
    # -----------------------------------------------------------------------------
    # 2. CARGA Y LIMPIEZA DEL DATASET MENSUAL ORIGINAL
    # -----------------------------------------------------------------------------
    # Obtener la ruta de la carpeta donde está guardado este mismo script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, 'datosAustin.csv')

    # Cargar el CSV usando la ruta exacta
    df_austin = pd.read_csv(csv_path)

    # Normalizar Código Postal (ZCTA a 5 dígitos) y galones a numérico
    df_austin['zcta'] = df_austin['Postal Code'].astype(str).str.extract(r'(\d{5})')
    df_austin['Total Gallons'] = pd.to_numeric(df_austin['Total Gallons'].str.replace(',', ''), errors='coerce')
    df_austin['Year Month'] = df_austin['Year Month'].astype(str)
    df_austin['year'] = df_austin['Year Month'].str[:4].astype(int)

    # Excluir ZIPs atípicos periféricos
    df_clean = df_austin[~df_austin['zcta'].isin(ZIPS_ANOMALOS)].copy()

    # -----------------------------------------------------------------------------
    # 3. CONSUMO HISTÓRICO MENSUAL (PERÍODO 2012 - 2019)
    # -----------------------------------------------------------------------------
    # Se suman primero todas las clases dentro del mismo mes para cada ZCTA
    df_hist = df_clean[(df_clean['year'] >= 2012) & (df_clean['year'] <= 2019)]
    hist_monthly_sum = df_hist.groupby(['zcta', 'Year Month'])['Total Gallons'].sum().reset_index()
    # Luego se promedian los meses del período
    df_hist_avg = hist_monthly_sum.groupby('zcta')['Total Gallons'].mean().reset_index()
    df_hist_avg.rename(columns={'Total Gallons': 'consumo_historico_mensual'}, inplace=True)

    # -----------------------------------------------------------------------------
    # 4. CONSUMO FUTURO (TARGET 2020 - 2024)
    # -----------------------------------------------------------------------------
    # Se suman las clases de cada mes en el quinquenio reciente y se promedian los meses
    df_fut = df_clean[(df_clean['year'] >= 2020) & (df_clean['year'] <= 2024)]
    fut_monthly_sum = df_fut.groupby(['zcta', 'Year Month'])['Total Gallons'].sum().reset_index()
    df_fut_avg = fut_monthly_sum.groupby('zcta')['Total Gallons'].mean().reset_index()
    df_fut_avg.rename(columns={'Total Gallons': 'consumo_futuro'}, inplace=True)

    # -----------------------------------------------------------------------------
    # 5. TIPO DE ZONA SEGÚN PARTICIPACIÓN VOLUMÉTRICA REAL EN GALONES
    # -----------------------------------------------------------------------------
    vol_por_clase = df_clean.groupby(['zcta', 'Customer Class'])['Total Gallons'].sum().reset_index()
    vol_total_zcta = df_clean.groupby('zcta')['Total Gallons'].sum().reset_index().rename(columns={'Total Gallons': 'vol_total'})
    vol_merged = pd.merge(vol_por_clase, vol_total_zcta, on='zcta')
    vol_merged['pct'] = vol_merged['Total Gallons'] / vol_merged['vol_total']

    def clasificar_zona(group):
        res_pct = group[group['Customer Class'].str.contains('Residential', na=False)]['pct'].sum()
        mf_pct = group[group['Customer Class'].str.contains('Multi-Family', na=False)]['pct'].sum()
        if res_pct >= 0.50:
            return 'Residential'
        elif mf_pct >= 0.40:
            return 'Multi-Family'
        else:
            return 'Comercial / Mixto'

    tipo_zona_df = vol_merged.groupby('zcta').apply(clasificar_zona).reset_index(name='tipo_zona')

  # -----------------------------------------------------------------------------
    # 6. CONSOLIDACIÓN Y FORMATEO FINAL DEL DATASET
    # -----------------------------------------------------------------------------
    df_nodos = pd.merge(df_hist_avg, df_fut_avg, on='zcta', how='inner')
    df_nodos = pd.merge(df_nodos, tipo_zona_df, on='zcta', how='inner')

    # Mapeo de latitud, longitud y población censal
    df_nodos['latitud'] = df_nodos['zcta'].map(lambda z: AUSTIN_COORDS.get(z, (np.nan, np.nan))[0])
    df_nodos['longitud'] = df_nodos['zcta'].map(lambda z: AUSTIN_COORDS.get(z, (np.nan, np.nan))[1])
    df_nodos['poblacion'] = df_nodos['zcta'].map(POBLACION_CENSO)

   
  # -------------------------------------------------------------------------
    # Tasas de crecimiento anual reales por ZCTA (U.S. Census Bureau 2010-2020)
    # -------------------------------------------------------------------------
    tasas_censales_reales = {
        78617: 3.62, 78652: 3.08, 78701: 2.03, 78702: 1.22, 78703: 0.58,
        78704: 1.27, 78705: 0.74, 78717: 2.82, 78719: 2.15, 78721: 2.56,
        78722: 0.88, 78723: 1.33, 78724: 2.92, 78726: 1.70, 78727: 0.73,
        78728: 1.35, 78729: 1.06, 78730: 1.42, 78731: 0.65, 78735: 1.17,
        78736: 1.80, 78739: 2.40, 78741: 1.19, 78742: 1.50, 78744: 1.30,
        78745: 1.19, 78746: 0.78, 78747: 3.10, 78748: 2.05, 78749: 0.68,
        78750: 0.84, 78751: 0.67, 78752: 1.26, 78753: 1.38, 78754: 2.47,
        78756: 0.95, 78757: 0.97, 78758: 1.03, 78759: 0.90
    }

    # SE AGREGA .astype(int) PARA QUE COINCIDA CON LAS LLAVES DEL DICCIONARIO:
    df_nodos['crecimiento_poblacional_estimado'] = df_nodos['zcta'].astype(int).map(tasas_censales_reales)
    # ---------------------------------

    # Consumo por habitante (galones/mes por persona): feature para el modelo
    df_nodos['consumo_por_habitante'] = (df_nodos['consumo_historico_mensual'] / df_nodos['poblacion']).round(4)

    # Asignar nodo_id entero secuencial (1..N) conservando el código postal original (zcta)
    df_nodos['nodo_id'] = range(1, len(df_nodos) + 1)
    
    # Orden exacto de columnas para el TP
    columnas_tp = [
        'nodo_id', 'zcta', 'latitud', 'longitud', 'poblacion', 
        'tipo_zona', 'consumo_historico_mensual', 'consumo_por_habitante',
        'crecimiento_poblacional_estimado', 'consumo_futuro'
    ]
    df_final = df_nodos[columnas_tp]

    # Exportar archivo consolidado en CSV
    output_filename = 'nodos_red_agua_austin.csv'
    df_final.to_csv(output_filename, index=False)
    print(f"Dataset definitivo generado exitosamente con {len(df_final)} nodos limpios en '{output_filename}'.")

if __name__ == '__main__':
    generar_dataset_definitivo()