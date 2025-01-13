import streamlit as st
import pandas as pd
import io

# Fonction pour parser les lignes Quadratus basées sur des tailles fixes
def parse_quadra_line(line):
    return {
        "Type de ligne": line[0:1].strip(),
        "Numéro de compte": line[1:9].strip(),
        "Code journal": line[9:11].strip(),
        "Folio": line[11:14].strip(),
        "Date d’écriture": line[14:20].strip(),
        "Libellé de l’écriture": line[21:41].strip(),
        "Sens de l’écriture": line[41:42].strip(),
        "Signe du montant": line[42:43].strip(),
        "Montant": line[43:55].strip(),
        "Contrepartie": line[55:63].strip(),
        "Date d’échéance": line[63:69].strip(),
        "Lettrage": line[69:74].strip(),
        "Numéro de pièce": line[74:79].strip(),
        "Devise": line[99:102].strip(),
        "Code journal 2": line[102:105].strip(),
        "Libellé étendu": line[125:157].strip(),
    }

# Fonction pour convertir une date Quadratus en format JJ/MM/AAAA
def convert_date_quad_to_ebp(date_quad):
    return date_quad[:2] + "/" + date_quad[2:4] + "/" + date_quad[4:]

# Fonction de conversion Quadratus -> EBP
def convert_quad_to_ebp(parsed_lines):
    ebp_data = []
    for index, row in parsed_lines.iterrows():
        numero_ligne = index + 1
        date_ecriture = convert_date_quad_to_ebp(row['Date d’écriture'])
        code_journal = row['Code journal 2'][:4]
        compte = row['Numéro de compte']
        libelle = ""
        libelle_manuel = '"' + row["Libellé étendu"][:40] + '"'
        numero_piece = '"' + row['Numéro de pièce'][:15] + '"'
        montant = abs(float(row['Montant']) / 100)
        sens = 'D' if row['Sens de l’écriture'] == 'D' else 'C'
        date_echeance = convert_date_quad_to_ebp(row['Date d’échéance']) if row['Date d’échéance'] != '000000' else ""
        devise = "EUR"

        ebp_data.append([
            numero_ligne,
            date_ecriture,
            code_journal,
            compte,
            libelle,
            libelle_manuel,
            numero_piece,
            montant,
            sens,
            date_echeance,
            devise,
        ])

    columns = [
        "Numéro de ligne", "Date", "Code journal", "Compte général", "Libellé automatique",
        "Libellé manuel", "Numéro de pièce", "Montant", "Sens", "Date d'échéance", "Devise"
    ]
    df_ebp = pd.DataFrame(ebp_data, columns=columns)
    return df_ebp

# Fonction pour convertir un DataFrame en fichier texte au format EBP
def df_to_ebp_txt(df):
    output = io.StringIO()
    df.to_csv(output, sep=",", index=False, header=False, lineterminator="\n")
    output.seek(0)
    return output.read()

# Application Streamlit
st.title("Conversion Quadratus vers EBP")

uploaded_file = st.file_uploader("Importer un fichier Quadratus (TXT)", type=["txt"])

if uploaded_file:
    try:
        # Lecture ligne par ligne du fichier TXT
        lines = uploaded_file.read().decode("ISO-8859-1").splitlines()
        parsed_lines = pd.DataFrame([parse_quadra_line(line) for line in lines])

        st.subheader("Visualisation des écritures Quadratus")
        st.dataframe(parsed_lines)

        # Conversion au format EBP
        df_ebp = convert_quad_to_ebp(parsed_lines)
        st.subheader("Visualisation des écritures converties au format EBP")
        st.dataframe(df_ebp)

        # Télécharger le fichier EBP
        ebp_txt = df_to_ebp_txt(df_ebp)
        st.download_button(
            label="Télécharger le fichier EBP",
            data=ebp_txt,
            file_name="ECRITURES.TXT",
            mime="text/plain"
        )
    except Exception as e:
        st.error(f"Erreur lors de la lecture ou du traitement du fichier : {e}")
