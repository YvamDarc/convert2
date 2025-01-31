import streamlit as st
import pandas as pd
import numpy as np
import io

# Fonction pour parser les lignes Quadratus basées sur des tailles fixes
def parse_quadra_line(line):
    debit = float(line[43:55].strip()) / 100 if line[42:43] == '+' else 0.00
    credit = float(line[43:55].strip()) / 100 if line[42:43] == '-' else 0.00
    
    return {
        "JournalCode": line[9:11].strip(),
        "JournalLib": "Journal comptable",
        "EcritureNum": line[74:79].strip(),
        "EcritureDate": line[14:20].strip(),
        "CompteNum": line[1:9].strip(),
        "CompteLib": "Libellé du compte",
        "CompAuxNum": "",
        "CompAuxLib": "",
        "PieceRef": line[74:79].strip(),
        "PieceDate": line[14:20].strip(),
        "EcritureLib": line[21:41].strip(),
        "Debit": debit,
        "Credit": credit,
        "EcritureLet": "",
        "DateLet": "",
        "ValidDate": line[14:20].strip(),
        "Montantdevise": "0.00",
        "Idevise": "EUR"
    }

# Fonction pour convertir une date Quadratus en format JJ/MM/AAAA
def convert_date_quad_to_fec(date_quad):
    return date_quad[:2] + "/" + date_quad[2:4] + "/" + date_quad[4:] if date_quad.strip().isdigit() and len(date_quad) == 6 else ""

# Fonction de conversion Quadratus -> FEC
def convert_quad_to_fec(parsed_lines):
    df_fec = pd.DataFrame(parsed_lines)
    df_fec["EcritureDate"] = df_fec["EcritureDate"].apply(convert_date_quad_to_fec)
    df_fec["PieceDate"] = df_fec["PieceDate"].apply(convert_date_quad_to_fec)
    df_fec["ValidDate"] = df_fec["ValidDate"].apply(convert_date_quad_to_fec)
    df_fec["DateLet"] = df_fec["DateLet"].apply(lambda x: convert_date_quad_to_fec(x) if x else "")
    
    # Vérification du nombre de colonnes et ajout des valeurs par défaut si nécessaire
    required_columns = [
        "JournalCode", "JournalLib", "EcritureNum", "EcritureDate", "CompteNum", "CompteLib",
        "CompAuxNum", "CompAuxLib", "PieceRef", "PieceDate", "EcritureLib", "Debit", "Credit",
        "EcritureLet", "DateLet", "ValidDate", "Montantdevise", "Idevise"
    ]
    
    for col in required_columns:
        if col not in df_fec.columns:
            df_fec[col] = "" if col not in ["Debit", "Credit", "Montantdevise"] else 0.00
    
    return df_fec[required_columns]

# Fonction pour convertir un DataFrame en fichier texte au format FEC
def df_to_fec_txt(df):
    output = io.StringIO()
    df.to_csv(output, sep="|", index=False, encoding='utf-8')
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

        df_fec = convert_quad_to_fec(parsed_lines)

        st.subheader("Visualisation des écritures FEC")
        st.dataframe(df_fec)

        # Télécharger le fichier FEC
        fec_txt = df_to_fec_txt(df_fec)
        st.download_button(
            label="Télécharger le fichier FEC",
            data=fec_txt,
            file_name="FEC.txt",
            mime="text/plain"
        )
    except Exception as e:
        st.error(f"Erreur lors de la lecture ou du traitement du fichier : {e}")
