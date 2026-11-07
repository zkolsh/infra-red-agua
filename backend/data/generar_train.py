import os
import pandas as pd
import numpy as np

# 1. Configuración de rutas dinámicas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
csv_input_path = os.path.join(BASE_DIR, 'datosAustin.csv')
output_csv_path = os.path.join(BASE_DIR, 'train_red_agua_austin.csv')

# Parámetros del emparejamiento anual
OFFSET_ANIOS = 6          # salto entre el año base y el año del target (antes: 72 meses)
MESES_MINIMOS = 12        # un año solo cuenta si tiene los 12 meses
RATIO_MIN, RATIO_MAX = 0.3, 3.0   # filtro de outliers sobre el ratio futuro/histórico

# Exclusión de ZIPs anómalos (baja cobertura municipal)
ZIPS_ANOMALOS = {'78610', '78613', '78653', '78660', '78681', '78725', '78732', '78737', '78738'}

# Diccionarios Maestros de Austin
POBLACION_CENSO = {
    '78617': 29631, '78652': 6124,  '78701': 9534,  '78702': 23891, '78703': 21820,
    '78704': 47926, '78705': 33177, '78717': 29641, '78719': 1954,  '78721': 13426,
    '78722': 7291,  '78723': 34327, '78724': 27814, '78726': 14457, '78727': 30048,
    '78728': 22534, '78729': 30376, '78730': 9102,  '78731': 28269, '78735': 17820,
    '78736': 8847,  '78739': 20436, '78741': 52917, '78742': 612,   '78744': 48753,
    '78745': 62451, '78746': 28659, '78747': 21475, '78748': 49914, '78749': 37812,
    '78750': 31089, '78751': 14856, '78752': 20568, '78753': 58514, '78754': 24719,
    '78756': 13914, '78757': 24108, '78758': 48123, '78759': 42805
}

TASAS_CENSALES_REALES = {
    '78617': 3.62, '78652': 3.08, '78701': 2.03, '78702': 1.22, '78703': 0.58,
    '78704': 1.27, '78705': 0.74, '78717': 2.82, '78719': 2.15, '78721': 2.56,
    '78722': 0.88, '78723': 1.33, '78724': 2.92, '78726': 1.70, '78727': 0.73,
    '78728': 1.35, '78729': 1.06, '78730': 1.42, '78731': 0.65, '78735': 1.17,
    '78736': 1.80, '78739': 2.40, '78741': 1.19, '78742': 1.50, '78744': 1.30,
    '78745': 1.19, '78746': 0.78, '78747': 3.10, '78748': 2.05, '78749': 0.68,
    '78750': 0.84, '78751': 0.67, '78752': 1.26, '78753': 1.38, '78754': 2.47,
    '78756': 0.95, '78757': 0.97, '78758': 1.03, '78759': 0.90
}

LATITUD_ZCTA = {
    '78617': 30.1706, '78652': 30.1332, '78701': 30.2713, '78702': 30.2625, '78703': 30.2828,
    '78704': 30.2452, '78705': 30.2906, '78717': 30.4907, '78719': 30.1311, '78721': 30.2678,
    '78722': 30.2891, '78723': 30.3073, '78724': 30.3013, '78726': 30.4431, '78727': 30.4326,
    '78728': 30.4578, '78729': 30.4571, '78730': 30.3664, '78731': 30.3475, '78735': 30.2465,
    '78736': 30.2343, '78739': 30.1706, '78741': 30.2335, '78742': 30.2474, '78744': 30.1837,
    '78745': 30.2076, '78746': 30.2818, '78747': 30.1189, '78748': 30.1583, '78749': 30.2091,
    '78750': 30.4243, '78751': 30.3093, '78752': 30.3341, '78753': 30.3791, '78754': 30.3663,
    '78756': 30.3135, '78757': 30.3551, '78758': 30.3848, '78759': 30.4042,
}

LONGITUD_ZCTA = {
    '78617': -97.6186, '78652': -97.8682, '78701': -97.7426, '78702': -97.7164, '78703': -97.7618,
    '78704': -97.7686, '78705': -97.7397, '78717': -97.7685, '78719': -97.6744, '78721': -97.6853,
    '78722': -97.7161, '78723': -97.6826, '78724': -97.6133, '78726': -97.8488, '78727': -97.7162,
    '78728': -97.6888, '78729': -97.7675, '78730': -97.8385, '78731': -97.7645, '78735': -97.8596,
    '78736': -97.9351, '78739': -97.8936, '78741': -97.7196, '78742': -97.6705, '78744': -97.7408,
    '78745': -97.7946, '78746': -97.8172, '78747': -97.7471, '78748': -97.8329, '78749': -97.8601,
    '78750': -97.8288, '78751': -97.7259, '78752': -97.7088, '78753': -97.6749, '78754': -97.6322,
    '78756': -97.7402, '78757': -97.7297, '78758': -97.7099, '78759': -97.7554,
}

TIPO_ZONA_ZCTA = {
    '78617': 'Residential', '78652': 'Residential', '78701': 'Multi-Family', '78702': 'Residential',
    '78703': 'Residential', '78704': 'Multi-Family', '78705': 'Multi-Family', '78717': 'Residential',
    '78719': 'Residential', '78721': 'Residential', '78722': 'Residential', '78723': 'Residential',
    '78724': 'Residential', '78726': 'Residential', '78727': 'Residential', '78728': 'Residential',
    '78729': 'Residential', '78730': 'Residential', '78731': 'Residential', '78735': 'Residential',
    '78736': 'Residential', '78739': 'Residential', '78741': 'Multi-Family', '78742': 'Residential',
    '78744': 'Residential', '78745': 'Residential', '78746': 'Residential', '78747': 'Residential',
    '78748': 'Residential', '78749': 'Residential', '78750': 'Residential', '78751': 'Multi-Family',
    '78752': 'Multi-Family', '78753': 'Residential', '78754': 'Residential', '78756': 'Multi-Family',
    '78757': 'Residential', '78758': 'Multi-Family', '78759': 'Residential',
}

def generar_train_anual():
    print(f"Leyendo datos originales desde: {csv_input_path}")
    df_raw = pd.read_csv(csv_input_path)

    # 1. Limpieza y parseo básico
    df_raw['zcta'] = df_raw['Postal Code'].astype(str).str.extract(r'(\d{5})')[0]
    df_raw['Total Gallons'] = pd.to_numeric(df_raw['Total Gallons'].str.replace(',', ''), errors='coerce')
    df_raw['Year Month'] = df_raw['Year Month'].astype(str)

    df_clean = df_raw.dropna(subset=['zcta', 'Total Gallons', 'Year Month']).copy()
    df_clean = df_clean[~df_clean['zcta'].isin(ZIPS_ANOMALOS)]

    # 2. Agrupación mensual por zona y luego agregación ANUAL (consumo medio mensual de cada año)
    df_mensual = df_clean.groupby(['zcta', 'Year Month'])['Total Gallons'].sum().reset_index()
    df_mensual['year'] = pd.to_datetime(df_mensual['Year Month'], format='%Y%m').dt.year

    df_anual = (
        df_mensual.groupby(['zcta', 'year'])['Total Gallons']
        .agg(consumo_medio='mean', n_meses='count')
        .reset_index()
    )
    df_anual = df_anual[df_anual['n_meses'] >= MESES_MINIMOS].drop(columns='n_meses')

    # 3. Emparejamiento anual empírico: año base Y -> año Y + OFFSET_ANIOS de la misma zona
    df_futuro = df_anual.rename(columns={'consumo_medio': 'consumo_futuro_target'})
    df_futuro['year'] = df_futuro['year'] - OFFSET_ANIOS

    df_train_emp = pd.merge(
        df_anual.rename(columns={'consumo_medio': 'consumo_historico_mensual'}),
        df_futuro,
        on=['zcta', 'year'],
        how='inner'
    )

    # 4. Mapeo de diccionarios completos
    df_train_emp['pob_2020'] = df_train_emp['zcta'].map(POBLACION_CENSO)
    df_train_emp['cagr'] = df_train_emp['zcta'].map(TASAS_CENSALES_REALES)
    df_train_emp['latitud'] = df_train_emp['zcta'].map(LATITUD_ZCTA)
    df_train_emp['longitud'] = df_train_emp['zcta'].map(LONGITUD_ZCTA)
    df_train_emp['tipo_zona'] = df_train_emp['zcta'].map(TIPO_ZONA_ZCTA)

    # 5. Población del año (a mitad de año, en base al CAGR censal)
    df_train_emp['years_from_2020'] = (df_train_emp['year'] + 0.5) - 2020
    df_train_emp['poblacion'] = (df_train_emp['pob_2020'] * ((1 + df_train_emp['cagr'] / 100.0) ** df_train_emp['years_from_2020'])).round().astype(int)

    # 6. Columnas base y feature engineering
    df_train_emp['nodo_id'] = df_train_emp.groupby('zcta').ngroup() + 1
    df_train_emp['crecimiento_poblacional_estimado'] = df_train_emp['cagr']
    df_train_emp['consumo_por_habitante'] = (df_train_emp['consumo_historico_mensual'] / df_train_emp['poblacion']).round(4)

    # 7. Filtro de outliers
    df_train_emp['ratio_real'] = df_train_emp['consumo_futuro_target'] / df_train_emp['consumo_historico_mensual']
    df_train_emp = df_train_emp[(df_train_emp['ratio_real'] >= RATIO_MIN) & (df_train_emp['ratio_real'] <= RATIO_MAX)]

    # 8. Selección y guardado
    cols = [
        'nodo_id', 'zcta', 'year',
        'latitud', 'longitud', 'tipo_zona',
        'poblacion', 'crecimiento_poblacional_estimado',
        'consumo_historico_mensual', 'consumo_por_habitante', 'consumo_futuro_target'
    ]
    df_final = df_train_emp[cols].sort_values(['zcta', 'year']).reset_index(drop=True)
    df_final['consumo_historico_mensual'] = df_final['consumo_historico_mensual'].round(1)
    df_final['consumo_futuro_target'] = df_final['consumo_futuro_target'].round(1)

    df_final.to_csv(output_csv_path, index=False)

    print("\n" + "=" * 50)
    print(f"Dataset TRAIN anual generado exitosamente: {output_csv_path}")
    print(f"Filas: {len(df_final)} | Zonas: {df_final['zcta'].nunique()} | Años base: {df_final['year'].min()}-{df_final['year'].max()}")
    print("=" * 50 + "\n")

if __name__ == '__main__':
    generar_train_anual()