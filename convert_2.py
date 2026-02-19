import io
from dataclasses import dataclass
from typing import List, Optional

import pandas as pd
import streamlit as st


# ============================
# Constantes / config
# ============================
FEC_COLUMNS = [
    "JournalCode", "JournalLib",
    "EcritureNum", "EcritureDate",
    "CompteNum", "CompteLib",
    "CompAuxNum", "CompAuxLib",
    "PieceRef", "PieceDate",
    "EcritureLib",
    "Debit", "Credit",
    "EcritureLet", "DateLet",
    "ValidDate",
    "Montantdevise", "Idevise"
]

ENCODINGS_TO_TRY = ["ISO-8859-1", "cp1252", "utf-8"]


# ============================
# Helpers robustes
# ============================
def safe_slice(s: str, a: int, b: int) -> str:
    """Slice sécurisé : ne plante pas si la ligne est plus courte."""
    if not s:
        return ""
    if a >= len(s):
        return ""
    return s[a:min(b, len(s))]


def parse_amount_centimes(raw: str) -> float:
    """Convertit une zone '000000001234' en euros (12.34)."""
    t = (raw or "").strip()
    if not t:
        return 0.0
    # Certains exports contiennent des espaces/zeros => on ne garde que digits + signe
    t = "".join(ch for ch in t if ch.isdigit() or ch in "+-")
    if not t:
        return 0.0
    try:
        return float(int(t)) / 100.0
    except Exception:
        return 0.0


def convert_date_quad_to_fec(date_quad: str) -> str:
    """Convertit JJMMYY -> AAAAMMJJ. Renvoie '' si non parsable."""
    t = (date_quad or "").strip()
    if not t:
        return ""
    dt = pd.to_datetime(t, format="%d%m%y", errors="coerce")
    if pd.isna(dt):
        return ""
    return dt.strftime("%Y%m%d")


def pick_piece_ref(line: str) -> str:
    """
    Priorité de la récupération du numéro de pièce.
    Attention : on utilise safe_slice partout et on garde la logique d'origine.
    """
    # on teste les zones dans l'ordre, et on renvoie la 1ère non vide
    candidates = [
        safe_slice(line, 231, 252).strip(),  # ancien: line[231:252]
        safe_slice(line, 148, 169).strip(),
        safe_slice(line, 99, 120).strip(),
        safe_slice(line, 74, 95).strip(),
    ]
    for c in candidates:
        if c:
            return c
    return "000000"


def parse_quadra_line(line: str) -> dict:
    """
    Parse une ligne Quadratus (tailles fixes) en dict FEC.
    Sécurisé contre les lignes plus courtes.
    """
    sens = safe_slice(line, 41, 42).strip().upper()

    montant = parse_amount_centimes(safe_slice(line, 43, 55))
    debit = montant if sens == "D" else 0.0
    credit = montant if sens == "C" else 0.0

    compte_num = safe_slice(line, 1, 9).strip()

    ecriture_date_raw = safe_slice(line, 14, 20).strip()
    ecriture_num = safe_slice(line, 74, 79).strip()
    ecriture_lib = safe_slice(line, 21, 41).strip()
    journal_code = safe_slice(line, 9, 11).strip()

    piece_ref = pick_piece_ref(line)

    return {
        "JournalCode": journal_code,
        "JournalLib": "Journal comptable",
        "EcritureNum": ecriture_num,
        "EcritureDate": ecriture_date_raw,
        "CompteNum": compte_num,
        "CompteLib": "Libellé du compte" if compte_num else "",
        "CompAuxNum": "",
        "CompAuxLib": "",
        "PieceRef": piece_ref,
        "PieceDate": ecriture_date_raw,
        "EcritureLib": ecriture_lib,
        "Debit": debit,
        "Credit": credit,
        "EcritureLet": "",
        "DateLet": "",
        "ValidDate": "",
        "Montantdevise": 0.00,
        "Idevise": "EUR",
    }


def convert_to_fec_format(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convertit les dates + force les montants au format FEC (décimales avec virgule comme ton script).
    """
    out = df.copy()

    out["EcritureDate"] = out["EcritureDate"].apply(convert_date_quad_to_fec)
    out["PieceDate"] = out["PieceDate"].apply(convert_date_quad_to_fec)
    out["DateLet"] = out["DateLet"].apply(convert_date_quad_to_fec)

    # Montants : on garde la logique de ton fichier (virgule)
    for col in ["Debit", "Credit", "Montantdevise"]:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)
        out[col] = out[col].map(lambda x: f"{x:.2f}".replace(".", ","))

    # Remet les colonnes dans l'ordre FEC si besoin
    out = out.reindex(columns=FEC_COLUMNS, fill_value="")
    return out


def df_to_fec_txt(df: pd.DataFrame) -> str:
    output = io.StringIO()
    df.to_csv(output, sep="\t", index=False, encoding="utf-8", header=True, lineterminator="\n")
    return output.getvalue()


def read_uploaded_text(uploaded_file) -> List[str]:
    """Lit le fichier uploadé en essayant plusieurs encodages."""
    raw = uploaded_file.read()
    last_err: Optional[Exception] = None
    for enc in ENCODINGS_TO_TRY:
        try:
            return raw.decode(enc).splitlines()
        except Exception as e:
            last_err = e
    raise RuntimeError(f"Impossible de décoder le fichier avec {ENCODINGS_TO_TRY}. Dernière erreur: {last_err}")


# ============================
# Streamlit UI
# ============================
st.set_page_config(page_title="Conversion Quadratus vers FEC", layout="wide")
st.title("Conversion Quadratus vers FEC")

uploaded_file = st.file_uploader("Importer un fichier Quadratus (TXT)", type=["txt"])

if uploaded_file:
    try:
        lines = read_uploaded_text(uploaded_file)

        # Parse
        parsed_lines = [parse_quadra_line(line) for line in lines if line and line.strip()]

        df_quadra = pd.DataFrame(parsed_lines)

        # Suppression des lignes inutiles (comme ton script)
        df_quadra = df_quadra[
            (df_quadra["CompteNum"].astype(str).str.strip() != "")
            | (pd.to_numeric(df_quadra["Debit"], errors="coerce").fillna(0.0) != 0.0)
            | (pd.to_numeric(df_quadra["Credit"], errors="coerce").fillna(0.0) != 0.0)
        ]

        df_fec = convert_to_fec_format(df_quadra)

        st.subheader("Visualisation des écritures FEC")
        st.dataframe(df_fec, use_container_width=True)

        fec_txt = df_to_fec_txt(df_fec)
        st.download_button(
            label="Télécharger le fichier FEC",
            data=fec_txt,
            file_name="FEC.txt",
            mime="text/plain",
        )

    except Exception as e:
        st.error(f"Erreur lors de la lecture ou du traitement du fichier : {e}")
