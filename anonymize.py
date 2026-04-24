import pandas as pd
import os

EMAIL_MAP = {
    'manuelc.rapido@trucksmarter.com': 'agente01@bpo-demo.com',
    'mario.rapido@trucksmarter.com': 'agente02@bpo-demo.com',
    'fernanda@trucksmarter.com': 'agente03@bpo-demo.com',
    'jonathan.rapido@trucksmarter.com': 'agente04@bpo-demo.com',
    'arturo.rapido@trucksmarter.com': 'agente05@bpo-demo.com',
    'evelyn.rapido@trucksmarter.com': 'agente06@bpo-demo.com',
    'abraham.rapido@trucksmarter.com': 'agente07@bpo-demo.com',
    'daniel.rapido@trucksmarter.com': 'agente08@bpo-demo.com',
    'mcarlin@gorapido.com': 'agente01@bpo-demo.com',
    'mcobian@gorapido.com': 'agente02@bpo-demo.com',
    'vguzman@gorapido.com': 'agente03@bpo-demo.com',
    'jpadilla@gorapido.com': 'agente04@bpo-demo.com',
    'assanchez@gorapido.com': 'agente05@bpo-demo.com',
    'esimental@gorapido.com': 'agente06@bpo-demo.com',
    'emorales@gorapido.com': 'agente07@bpo-demo.com',
    'dflores@gorapido.com': 'agente08@bpo-demo.com',
    'ivan.rapido@trucksmarter.com': 'supervisor@bpo-demo.com',
}

NAME_MAP = {
    'Carlin, Manuel': 'Agent, One',
    'Cobian Castellanos, Mario': 'Agent, Two',
    'Guzman Navarro, Viridiana Fernanda': 'Agent, Three',
    'Padilla Soto, Jonathan Ivan': 'Agent, Four',
    'Sanchez Sanchez, Arturo': 'Agent, Five',
    'Simental Woodward, Evelyn Maria': 'Agent, Six',
    'Morales Campos, Eduardo Abraham': 'Agent, Seven',
    'Flores Alvarez, Daniel Antonio': 'Agent, Eight',
    'Manuel Carlin': 'Agent One',
    'Mario Cobian': 'Agent Two',
    'Fernanda Guzman': 'Agent Three',
    'Jonathan Padilla': 'Agent Four',
    'Arthur Sanchez': 'Agent Five',
    'Evelyn Woodward': 'Agent Six',
    'Abraham Morales': 'Agent Seven',
    'Daniel Flores': 'Agent Eight',
    'Ivan Ponce': 'Supervisor Demo',
}

def anonymize_df(df, filename):
    # Columnas de email
    for col in ['Master_Email', 'email']:
        if col in df.columns:
            df[col] = df[col].replace(EMAIL_MAP)

    # Columnas de nombre
    for col in ['Full_Name', 'Dialpad_Name', 'name', 'user_name', 'user_friendly_name']:
        if col in df.columns:
            df[col] = df[col].replace(NAME_MAP)

    # Controlio_ID — reemplazar con ID genérico
    if 'Controlio_ID' in df.columns:
        controlio_map = {v: f'DEMO-AGT-00{i+1}' for i, v in enumerate(df['Controlio_ID'].dropna().unique())}
        df['Controlio_ID'] = df['Controlio_ID'].replace(controlio_map)

    return df

files = ['data/raw/DB_Controlio.xlsx', 'data/raw/DB_Dialpad.xlsx', 'data/raw/DB_Operations.xlsx', 'data/raw/DIM_Agents.xlsx']
os.makedirs('data/clean', exist_ok=True)

for file in files:
    print(f"Procesando {file}...")
    xl = pd.ExcelFile(file)
    with pd.ExcelWriter(f'data/clean/{os.path.basename(file)}', engine='openpyxl') as writer:
        for sheet in xl.sheet_names:
            df = xl.parse(sheet)
            df = anonymize_df(df, file)
            df.to_excel(writer, sheet_name=sheet, index=False)
    print(f"  Guardado en data/clean/{file}")

print("\nListo. Archivos limpios en data/clean/")