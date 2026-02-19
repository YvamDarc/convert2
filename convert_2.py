import io
import streamlit as st
import pandas as pd

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

def safe_slice(line: str, a: int, b: int) -> str:
    if not line:
        return ""
    if a >= len(line):
        return ""
    return line[a:min(b, len(line))]

def parse_amount_centimes(s: str) -> float:
    s = (s or "").strip()
    if not s:
        return 0.0
    # Quadratus: souvent montant en centimes, parfois avec signe
    # On garde digits + signe
    cleaned = "".join(ch for ch in s if ch.isdigit() or ch == "-")
    if cleaned in ("", "-"):
        return 0.0
    try:
        return float(cleaned) / 100.0
    except ValueError:
        return 0.0

def convert_date_quad_to_fec(date_quad: str) -> str:
    # Quadratus: ddmmyy
    try:
        dt = pd.to_datetime(date_quad, format="%d%m%y", errors="coerce")
        return "" if pd.isna(dt) else dt.strftime("%Y%m%d")
    except Exception:
        return ""

def pick_piece_ref(line: str) -> str:
    # Priorité comme ton code, mais en safe
    c1 = safe_slice(line, 231, 252).strip()
    if len(line) >= 252 and safe_slice(line, 232, 252).strip():
        return c1

    c2 = safe_slice(line, 148, 169).strip()
    if len(line) >= 169 and safe_slice(line, 149, 169).strip():
        return c2

    c3 = safe_slice(line, 99, 120).strip()
    if len(line) >= 120 and safe_slice(line, 100, 120).strip():
        return c3

    c4 = safe_slice(line, 74, 95).strip()
    if len(line) >= 95 and safe_slice(line, 75, 95).strip():
        return c4

    return "000000"

def parse_quadra_line(line: str) -> dict:
    sens = safe_slice(line, 41, 42).strip().upper()

    montant = parse_amount_centimes(safe_slice(line, 43, 55))
    debit = montant if sens == "D" else 0.0
    credit = montant if sens == "C" else 0.0

    compte_num = safe_slice(line, 1, 9).strip()

    ecriture_date_raw = safe_slice(line, 14, 20).strip()
    piece_date_raw = ecriture_date_raw

    ecriture_num = safe_slice(line, 74, 79).strip()
    piece_ref = pick_piece_ref(line)

    return {
        "JournalCode": safe_slice(line, 9, 11).strip(),
        "JournalLib": "Journal comptable",
        "EcritureNum": ecriture_num,
        "EcritureDate": ecriture_date_raw,
        "CompteNum": compte_num,
        "CompteLib": "Libellé du compte" if compte_num else "",
        "CompAuxNum": "",
        "CompAuxLib": "",
        "PieceRef": piece_ref,
        "PieceDate": piece_date_raw,
        "EcritureLib": safe_slice(line, 21, 41).strip(),
        "Debit": debit,
        "Credit": credit,
        "EcritureLet": "",
        "DateLet": "",
        "ValidDate": "",
        "Montantdevise": 0.0,
        "Idevise": "EUR",
    }

def convert_to_fec_format(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out["EcritureDate"] = out["EcritureDate"].astype(str).apply(convert_date_quad_to_fec)
    out["PieceDate"] = out["PieceDate"].astype(str).apply(convert_date_quad_to_fec)
    out["DateLet"] = out["DateLet"].astype(str).apply(convert_date_quad_to_fec)

    # FEC en général: décimales avec point (souvent attendu)
    # Si toi tu veux absolument la virgule, remets .replace('.', ',')
    for col in ["Debit", "Credit", "Montantdevise"]:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0).map(lambda x: f"{x:.2f}")

    # Nettoyage NaN
    for c in out.columns:
        out[c] = out[c].astype(str).replace({"nan": "", "None": ""})

    return out

def df_to_fec_txt_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, sep="\t", index=False, encoding="utf-8", lineterminator="\n")
    return buf.getvalue().encode("utf-8")

# -------------------------
# Streamlit UI
# -------------------------
st.set_page_config(page_title="Conversion Quadratus vers FEC", layout="wide")
st.title("Conversion Quadratus → FEC")

uploaded_file = st.file_uploader("Importer un fichier Quadratus (.txt)", type=["txt"])

if uploaded_file is None:
    st.info("Charge un fichier .txt Quadratus.")
    st.stop()

try:
    raw_bytes = uploaded_file.getvalue()
    # Essai ISO-8859-1 (comme tu avais) puis fallback UTF-8
    try:
        text = raw_bytes.decode("ISO-8859-1")
    except UnicodeDecodeError:
        text = raw_bytes.decode("utf-8", errors="replace")

    lines = text.splitlines()

    st.write(f"📄 Lignes lues : **{len(lines)}**")

    parsed = [parse_quadra_line(line) for line in lines if line.strip()]

    df = pd.DataFrame(parsed, columns=FEC_COLUMNS)

    # Filtre: on garde si compte ou montant non nul
    df = df[
        (df["CompteNum"].astype(str).str.strip() != "")
        | (pd.to_numeric(df["Debit"], errors="coerce").fillna(0.0) != 0.0)
        | (pd.to_numeric(df["Credit"], errors="coerce").fillna(0.0) != 0.0)
    ].copy()

    df_fec = convert_to_fec_format(df)

    st.subheader("Aperçu (200 premières lignes)")
    st.dataframe(df_fec.head(200), use_container_width=True, height=520)

    with st.expander("Afficher tout (attention si très gros fichier)"):
        st.dataframe(df_fec, use_container_width=True, height=520)

    st.subheader("Téléchargement")
    st.download_button(
        "Télécharger FEC.txt",
        data=df_to_fec_txt_bytes(df_fec),
        file_name="FEC.txt",
        mime="text/plain",
    )

except Exception as e:
    st.exception(e)
