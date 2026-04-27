import pandas as pd
import os
import hashlib

# --- MAPPINGS GLOBALES ---
EMAIL_MAP = {
    'manuelc.rapido@trucksmarter.com': 'agente01@bpo-demo.com',
    # ... (Pega aquí el resto de tus correos tal como los tenías) ...
    'ivan.rapido@trucksmarter.com': 'supervisor@bpo-demo.com',
}

NAME_MAP = {
    'Carlin, Manuel': 'Agent, One',
    # ... (Pega aquí el resto de tus nombres tal como los tenías) ...
    'Ivan Ponce': 'Supervisor Demo',
}

def mask_phone_number(phone):
    """Convierte números reales a formato 555-XXXX usando un hash para mantener consistencia."""
    if pd.isna(phone) or str(phone).strip() == '':
        return phone
    
    phone_str = str(phone).replace('.0', '').strip()
    # Usamos hash para que el mismo número siempre dé el mismo resultado falso (para no romper la gráfica de fricción)
    hash_obj = hashlib.md5(phone_str.encode())
    fake_suffix = str(int(hash_obj.hexdigest(), 16))[-4:]
    return f"555-010-{fake_suffix}"

def anonymize_df(df, filename):
    """
    Recibe un DataFrame, anonimiza correos, nombres, IDs de Controlio, 
    números telefónicos y nombres de clientes/brokers.
    """
    # 1. Columnas de email
    for col in ['Master_Email', 'email']:
        if col in df.columns:
            df[col] = df[col].replace(EMAIL_MAP)

    # 2. Columnas de nombre
    for col in ['Full_Name', 'Dialpad_Name', 'name', 'user_name', 'user_friendly_name']:
        if col in df.columns:
            df[col] = df[col].replace(NAME_MAP)

    # 3. Controlio_ID — reemplazar con ID genérico
    if 'Controlio_ID' in df.columns:
        controlio_map = {v: f'DEMO-AGT-00{i+1}' for i, v in enumerate(df['Controlio_ID'].dropna().unique())}
        df['Controlio_ID'] = df['Controlio_ID'].replace(controlio_map)

    # 4. PROTECCIÓN DE DATOS DEL CLIENTE (Teléfonos)
    for col in ['external_number', 'Clean_Phone']:
        if col in df.columns:
            df[col] = df[col].apply(mask_phone_number)

    # 5. PROTECCIÓN DE DATOS DEL CLIENTE (Brokers)
    if 'Broker_Name' in df.columns:
        # Crea nombres genéricos: "Target Entity 1", "Target Entity 2", etc.
        broker_map = {v: f'Target Entity {i+1}' for i, v in enumerate(df['Broker_Name'].dropna().unique())}
        df['Broker_Name'] = df['Broker_Name'].replace(broker_map)

    return df

def main():
    """Función principal de ejecución del pipeline de anonimización."""
    files = [
        'data/raw/DB_Controlio.xlsx', 
        'data/raw/DB_Dialpad.xlsx', 
        'data/raw/DB_Operations.xlsx', 
        'data/raw/DIM_Agents.xlsx'
    ]
    
    output_dir = 'data/clean'
    os.makedirs(output_dir, exist_ok=True)

    for file in files:
        if not os.path.exists(file):
            print(f"⚠️ Archivo no encontrado: {file}")
            continue
            
        print(f"🔄 Procesando {file}...")
        xl = pd.ExcelFile(file)
        
        with pd.ExcelWriter(f'{output_dir}/{os.path.basename(file)}', engine='openpyxl') as writer:
            for sheet in xl.sheet_names:
                df = xl.parse(sheet)
                df = anonymize_df(df, file)
                df.to_excel(writer, sheet_name=sheet, index=False)
                
        print(f"✅ Guardado en {output_dir}/{os.path.basename(file)}")

    print("\n🚀 Pipeline finalizado. Archivos listos para uso público.")

if __name__ == '__main__':
    main()