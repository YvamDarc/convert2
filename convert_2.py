import streamlit as st
import pandas as pd
import numpy as np
import io

# Fonction pour parser les lignes Quadratus basées sur des tailles fixes
def parse_quadra_line(line):
    sens = line[41:42].strip()
    try:
        montant = float(line[43:55].strip()) / 100 if line[43:55].strip().isdigit() else 0.00
    except ValueError:
        montant = 0.00
    
    debit = montant if sens == 'D' else 0.00
    credit = montant if sens == 'C' else 0.00
    compte_num = line[1:9].strip()
    
    # Priorité de la récupération du numéro de pièce
    piece_ref = line[231:252].strip() if len(line) >= 252 and line[232:252].strip() else \
                line[148:169].strip() if len(line) >= 169 and line[149:169].strip() else \
                line[99:120].strip() if len(line) >= 120 and line[100:120].strip() else \
                line[74:95].strip() if len(line) >= 95 and line[75:95].strip() else "000000"
    
    return {
        "JournalCode": line[9:11].strip(),
        "JournalLib": "Journal comptable",
        "EcritureNum": line[74:79].strip(),
        "EcritureDate": line[14:20].strip(),
        "CompteNum": compte_num,
        "CompteLib": "Libellé du compte" if compte_num else "",
        "CompAuxNum": "",
        "CompAuxLib": "",
        "PieceRef": piece_ref,
        "PieceDate": line[14:20].strip(),
        "EcritureLib": line[21:41].strip(),
        "Debit": debit,
        "Credit": credit,
        "EcritureLet": "",
        "DateLet": "",
        "ValidDate": "",
        "Montantdevise": 0.00,
        "Idevise": "EUR"
    }

# Fonction pour convertir une date Quadratus en format AAAAMMJJ
def convert_date_quad_to_fec(date_quad):
    try:
        return pd.to_datetime(date_quad, format='%d%m%y', errors='coerce').strftime('%Y%m%d')
    except:
        return ""

# Fonction pour convertir le DataFrame au format FEC
def convert_to_fec_format(df):
    df["EcritureDate"] = df["EcritureDate"].apply(convert_date_quad_to_fec)
    df["PieceDate"] = df["PieceDate"].apply(convert_date_quad_to_fec)
    df["DateLet"] = df["DateLet"].apply(convert_date_quad_to_fec)
    
    # Définition du séparateur et format des nombres
    df["Debit"] = df["Debit"].astype(float).apply(lambda x: f"{x:.2f}".replace('.', ','))
    df["Credit"] = df["Credit"].astype(float).apply(lambda x: f"{x:.2f}".replace('.', ','))
    df["Montantdevise"] = df["Montantdevise"].astype(float).apply(lambda x: f"{x:.2f}".replace('.', ','))
    
    return df

# Fonction pour convertir un DataFrame en fichier texte au format FEC
def df_to_fec_txt(df):
    output = io.StringIO()
    df.to_csv(output, sep="\t", index=False, encoding='utf-8', header=True)
    output.seek(0)
    return output.read()

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
        df_quadra = df_quadra[(df_quadra["CompteNum"].str.strip() != "") | (df_quadra["Debit"].astype(float) != 0.00) | (df_quadra["Credit"].astype(float) != 0.00)]
        df_quadra = convert_to_fec_format(df_quadra)
        
        st.subheader("Visualisation des écritures FEC")
        st.dataframe(df_quadra)
        
        # Télécharger le fichier FEC
        fec_txt = df_to_fec_txt(df_quadra)
        st.download_button(
            label="Télécharger le fichier FEC",
            data=fec_txt,
            file_name="FEC.txt",
            mime="text/plain"
        )
    except Exception as e:
        st.error(f"Erreur lors de la lecture ou du traitement du fichier : {e}")
