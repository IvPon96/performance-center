import pandas as pd
import os
import hashlib

# --- MAPPINGS GLOBALES DE CORREO ---
EMAIL_MAP = {
    'manuelc.rapido@trucksmarter.com': 'agente01@bpo-demo.com',
    'mcarlin@gorapido.com': 'agente01@bpo-demo.com',
    'mario.rapido@trucksmarter.com': 'agente02@bpo-demo.com',
    'mcobian@gorapido.com': 'agente02@bpo-demo.com',
    'fernanda@trucksmarter.com': 'agente03@bpo-demo.com',
    'vguzman@gorapido.com': 'agente03@bpo-demo.com',
    'jonathan.rapido@trucksmarter.com': 'agente04@bpo-demo.com',
    'jpadilla@gorapido.com': 'agente04@bpo-demo.com',
    'arturo.rapido@trucksmarter.com': 'agente05@bpo-demo.com',
    'assanchez@gorapido.com': 'agente05@bpo-demo.com',
    'evelyn.rapido@trucksmarter.com': 'agente06@bpo-demo.com',
    'esimental@gorapido.com': 'agente06@bpo-demo.com',
    'abraham.rapido@trucksmarter.com': 'agente07@bpo-demo.com',
    'emorales@gorapido.com': 'agente07@bpo-demo.com',
    'daniel.rapido@trucksmarter.com': 'agente08@bpo-demo.com',
    'dflores@gorapido.com': 'agente08@bpo-demo.com',
    'ivan.rapido@trucksmarter.com': 'supervisor@bpo-demo.com',
    'iponce@gorapido.com': 'supervisor@bpo-demo.com',
}

# --- MAPPINGS DE NOMBRES (Incluyendo variaciones de Controlio) ---
NAME_MAP = {
    'Carlin, Manuel': 'Agent One',
    'Cobian Castellanos, Mario': 'Agent Two',
    'Guzman Navarro, Viridiana Fernanda': 'Agent Three',
    'Padilla Soto, Jonathan Ivan': 'Agent Four',
    'Sanchez Sanchez, Arturo': 'Agent Five',
    'Simental Woodward, Evelyn Maria': 'Agent Six',
    'Morales Campos, Eduardo Abraham': 'Agent Seven',
    'Flores Alvarez, Daniel Antonio': 'Agent Eight',
    'Manuel Carlin': 'Agent One',
    'Mario Cobian': 'Agent Two',
    'Fernanda Guzman': 'Agent Three',
    'Jonathan Padilla': 'Agent Four',
    'Arthur Sanchez': 'Agent Five',
    'Evelyn Woodward': 'Agent Six',
    'Abraham Morales': 'Agent Seven',
    'Daniel Flores': 'Agent Eight',
    'Ivan Ponce': 'Supervisor Demo',
    
    # Nombres exactos como salen en Controlio
    'Arturo Sanchez Sanchez': 'Agent Five',
    'Daniel Antonio Flores Alvarez': 'Agent Eight',
    'Viridiana Fernanda Guzman Navarro': 'Agent Three',
    'Mario Cobian Castellanos': 'Agent Two',
    'Jonathan Ivan Padilla Soto': 'Agent Four',
    'Ivan Ponce Rodriguez': 'Supervisor Demo',
    'Evelyn Maria Simental Woodward': 'Agent Six',
}

# --- MAPPINGS DE CONTROLIO (Usuarios de Windows y PCs) ---
CONTROLIO_USER_MAP = {
    'mcarlin@LENRSGC00726LP': 'agent01@BPO-PC',
    'mcobian@LENRSGC02213LP': 'agent02@BPO-PC',
    'vguzman@LENRSGC01107LP': 'agent03@BPO-PC',
    'jpadilla@LENRSGC01892LP': 'agent04@BPO-PC',
    'assanchez@LENRSGC00559LP': 'agent05@BPO-PC',
    'esimental@LENRSGC00615LP': 'agent06@BPO-PC',
    'dflores@LENRSGC00138LP': 'agent08@BPO-PC',
    'iponce@LENRSGC00010LP': 'supervisor@BPO-PC',
}

CONTROLIO_PC_MAP = {
    'LENRSGC00726LP': 'PC-AGENT-01',
    'LENRSGC02213LP': 'PC-AGENT-02',
    'LENRSGC01107LP': 'PC-AGENT-03',
    'LENRSGC01892LP': 'PC-AGENT-04',
    'LENRSGC00559LP': 'PC-AGENT-05',
    'LENRSGC00615LP': 'PC-AGENT-06',
    'LENRSGC00138LP': 'PC-AGENT-08',
    'LENRSGC00010LP': 'PC-SUPERVISOR',
}

def mask_phone_number(phone):
    """Convierte números reales a formato 555-XXXX usando un hash para mantener consistencia."""
    if pd.isna(phone) or str(phone).strip() == '':
        return phone
    
    phone_str = str(phone).replace('.0', '').strip()
    hash_obj = hashlib.md5(phone_str.encode())
    fake_suffix = str(int(hash_obj.hexdigest(), 16))[-4:]
    return f"555-010-{fake_suffix}"

def anonymize_df(df, filename):
    """Anonimiza correos, nombres, IDs de Controlio, teléfonos y equipos."""
    # 1. Columnas de email
    for col in ['Master_Email', 'email']:
        if col in df.columns:
            df[col] = df[col].replace(EMAIL_MAP)

    # 2. Columnas de nombre
    for col in ['Full_Name', 'Dialpad_Name', 'name', 'user_friendly_name']:
        if col in df.columns:
            df[col] = df[col].replace(NAME_MAP)

    # 3. Controlio Especiales (Usuarios de Windows y Nombres de PC)
    if 'user_name' in df.columns:
        df['user_name'] = df['user_name'].replace(CONTROLIO_USER_MAP)
    
    if 'computer_name' in df.columns:
        df['computer_name'] = df['computer_name'].replace(CONTROLIO_PC_MAP)

    if 'Controlio_ID' in df.columns:
        controlio_map = {v: f'DEMO-AGT-00{i+1}' for i, v in enumerate(df['Controlio_ID'].dropna().unique())}
        df['Controlio_ID'] = df['Controlio_ID'].replace(controlio_map)

    # 4. PROTECCIÓN DE DATOS DEL CLIENTE (Teléfonos)
    for col in ['external_number', 'Clean_Phone']:
        if col in df.columns:
            df[col] = df[col].apply(mask_phone_number)

    # 5. PROTECCIÓN DE DATOS DEL CLIENTE (Brokers)
    if 'Broker_Name' in df.columns:
        broker_map = {v: f'Target Entity {i+1}' for i, v in enumerate(df['Broker_Name'].dropna().unique())}
        df['Broker_Name'] = df['Broker_Name'].replace(broker_map)

    return df

def main():
    """Ejecuta el pipeline de anonimización."""
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
            print(f"⚠️ Archivo no encontrado en tu entorno local: {file}")
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