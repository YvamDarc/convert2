import re
from datetime import datetime

def parse_quadra_line(line):
    # Extraction des données de chaque ligne QUADRA en fonction des positions définies
    code = line[1:9].strip()
    journal = line[9:11].strip()
    date = line[14:20].strip()
    # Correction de la date pour qu'elle soit en format JJMMAAAA
    date = date[:2] + date[2:4] + "20" + date[4:]  # Transforme 200723 en 20072023
    libelle = line[21:41].strip()
    sens = line[41].strip()
    montant = line[42:55].replace('+', '').replace(',', '.').strip()
    ref_piece = line[74:79].strip()
    
    return code, date, libelle, montant, sens, ref_piece, journal

def format_ebp_line(index, date, code, journal, libelle, ref_piece, montant, sens):
    # Formatage de la ligne pour le fichier EBP avec les nouvelles exigences
    return f"{index},{date},{journal},{code},,\"{libelle}\",\"{ref_piece}\",{montant},{sens},,EUR"

def quadra_to_ebp(quadra_lines):
    ebp_lines = []
    index = 1  # Numéro de ligne commence à 1
    
    # Ajout de la ligne d'entête
    ebp_lines.append("Numéro de ligne,Date,Code journal,Compte,Vide,Libellé,Pièce,Montant,Sens,Echéance,Devise")
    
    for line in quadra_lines:
        # Ignorer les lignes qui commencent par 'C'
        if line.startswith('C'):
            continue
        
        code, date, libelle, montant, sens, ref_piece, journal = parse_quadra_line(line)
        ebp_line = format_ebp_line(index, date, code, journal, libelle, ref_piece, montant, sens)
        ebp_lines.append(ebp_line)
        index += 1
    
    return ebp_lines

def convert_quadra_to_ebp(uploaded_file):
    # Lire le fichier QUADRA
    quadra_lines = uploaded_file.read().decode("utf-8").splitlines()
    
    # Convertir en format EBP
    ebp_lines = quadra_to_ebp(quadra_lines)
    
    # Convertir en dataframe pour un téléchargement facile
    df = pd.DataFrame([line.split(",") for line in ebp_lines])
    
    return df

# Streamlit App
st.title("Convertisseur d'écritures QUADRA vers EBP")

uploaded_file = st.file_uploader("Téléchargez votre fichier QUADRA", type=["txt"])

if uploaded_file is not None:
    df = convert_quadra_to_ebp(uploaded_file)
    
    st.write("Aperçu des premières lignes des écritures converties :")
    st.dataframe(df.head())

    # Télécharger le fichier EBP
    today = datetime.today().strftime('%Y%m%d')
    filename = f"LIBSOCIETE_export_EBP_{today}.txt"
    
    csv = df.to_csv(index=False, header=False).encode('utf-8')
    st.download_button(
        label="Télécharger les écritures EBP",
        data=csv,
        file_name=filename,
        mime='text/csv',
    )
