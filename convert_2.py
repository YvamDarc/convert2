import streamlit as st
import pandas as pd
import numpy as np
import io

# Fonction pour parser les lignes Quadratus basées sur des tailles fixes
def parse_quadra_line(line):
    sens = line[41:42].strip()
    montant = float(line[43:55].strip()) / 100 if line[43:55].strip().isdigit() else 0.00
    debit = montant if sens == 'D' else 0.00
    credit = montant if sens == 'C' else 0.00
    compte_num = line[1:9].strip()
    
    return {
        "JournalCode": line[9:11].strip(),
        "JournalLib": "Journal comptable",
        "EcritureNum": line[74:79].strip(),
        "EcritureDate": line[14:20].strip(),
        "CompteNum": compte_num,
        "CompteLib": "Libellé du compte" if compte_num else "",
        "CompAuxNum": "",
        "CompAuxLib": "",
        "PieceRef": line[74:79].strip(),
        "PieceDate": line[14:20].strip(),
        "EcritureLib": line[21:41].strip(),
        "Debit": debit,
        "Credit": credit,
        "EcritureLet": "",
        "DateLet": "",
        "ValidDate": "",
        "Montantdevise": "0.00",
        "Idevise": "EUR"
    }

# Fonction pour convertir une date Quadratus en format datetime
def convert_date_quad_to_datetime(date_quad):
    try:
        return pd.to_datetime(date_quad, format='%d%m%y', errors='coerce')
    except:
        return pd.NaT

# Application Streamlit
st.title("Conversion Quadratus vers FEC")

uploaded_file = st.file_uploader("Importer un fichier Quadratus (TXT)", type=["txt"])

if uploaded_file:
    try:
        # Lecture ligne par ligne du fichier TXT
        lines = uploaded_file.read().decode("ISO-8859-1").splitlines()
        parsed_lines = [parse_quadra_line(line) for line in lines]

        # Création du DataFrame et suppression des lignes sans numéro de compte et sans montant
        df_quadra = pd.DataFrame(parsed_lines)
        df_quadra = df_quadra[(df_quadra["CompteNum"].str.strip() != "") | ((df_quadra["Debit"] != 0.00) | (df_quadra["Credit"] != 0.00))]
        
        df_quadra["EcritureDate"] = df_quadra["EcritureDate"].apply(convert_date_quad_to_datetime)
        df_quadra.set_index("EcritureDate", inplace=True)
        
        st.subheader("Visualisation des écritures Quadratus")
        st.dataframe(df_quadra)
    except Exception as e:
        st.error(f"Erreur lors de la lecture ou du traitement du fichier : {e}")
