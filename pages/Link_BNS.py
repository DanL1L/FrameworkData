# app_bns_pxweb.py
# ------------------------------------------------------------
# Streamlit – Acces date BNS (PX-Web / Statbank) – MULTI-DOMENIU
# + Fix 429 (Too Many Requests): cache + retry/backoff + Session
# + Navigator generic: selectezi dbid -> intri in foldere -> alegi tabel
# + Salvare în fișiere Excel DIFERITE (pe sectoare) + UPSERT pe chei
# + Salvare specială (formatată) pentru Extern/Lunar: Exp_Lunar (Export/Import/Sold)
# + Routing pe foi: dacă tabelul este "Agricultura" => Real.xlsx / foaia "Agricultura"
# + (Opțional) avertizare dacă sectorul inferred nu corespunde destinației
# ------------------------------------------------------------

import time
import random
from io import BytesIO
from datetime import datetime
from pathlib import Path
import unicodedata

import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# =========================
# CONFIG UI
# =========================
st.set_page_config(layout="wide")
st.title("Datele oficiale ale BNS")

# =========================
# PX-WEB ROOT + DOMAINS
# =========================
API_ROOT = "https://statbank.statistica.md/PxWeb/api/v1/ro"

DOMAINS = [
    {"dbid": "10 Mediul inconjurator", "text": "Mediul inconjurator"},
    {"dbid": "20 Populatia si procesele demografice", "text": "Populatia si procesele demografice"},
    {"dbid": "30 Statistica sociala", "text": "Statistica sociala"},
    {"dbid": "40 Statistica economica", "text": "Statistica economica"},
    {"dbid": "50 Statistica gender", "text": "Statistica gender"},
    {"dbid": "60 Statistica regionala", "text": "Statistica regionala"},
]

# =========================
# DESTINAȚII EXCEL (pe sectoare)
# =========================
SECTOR_EXPORTS = {
    "EXT_LUNAR": {"file": Path("data/Data.xlsx"), "sheet": "Exp_Lunar"},   # format special (Export/Import/Sold)
    "SOCIAL":    {"file": Path("data/Social.xlsx"), "sheet": "Date"},
    "MONETAR":   {"file": Path("data/Monetar.xlsx"), "sheet": "Date"},
    "PUBLIC":    {"file": Path("data/Public.xlsx"), "sheet": "Date"},
    "REAL":      {"file": Path("data/Real.xlsx"), "sheet": "Date"},       # default (se va suprascrie de ROUTING dacă e cazul)
    "MEDIU":     {"file": Path("data/Mediu.xlsx"), "sheet": "Date"},
    "POP":       {"file": Path("data/Populatie.xlsx"), "sheet": "Date"},
    "REGIONAL":  {"file": Path("data/Regional.xlsx"), "sheet": "Date"},
    "GENDER":    {"file": Path("data/Gender.xlsx"), "sheet": "Date"},
}

SAVE_CHOICES = [
    "Nu salva datele în fișiere Excel",
    "Extern",
    "Social",
    "Monetar",
    "Public",
    "Real",
    "Mediu",
    "Populație",
    "Regional",
    "Gender",
]

SAVE_MAP = {
    "Extern": "EXT_LUNAR",
    "Social": "SOCIAL",
    "Monetar": "MONETAR",
    "Public": "PUBLIC",
    "Real": "REAL",
    "Mediu": "MEDIU",
    "Populație": "POP",
    "Regional": "REGIONAL",
    "Gender": "GENDER",
}

# =========================
# ROUTING FOI SPECIALE (după cuvinte cheie din tabel)
# Cheia: un pattern (normalizat). Valoarea: (sector_code, sheet_name)
# Exemplu cerut: Agricultura -> REAL / "Agricultura"
# Poți extinde ușor cu "Industrie", "PIB", "Transport" etc.
# =========================
SHEET_ROUTING_RULES = [
    # (must_contain_keywords, sector_code, sheet_name)
    (["agric"], "REAL", "Agricultura"),
]

# =========================
# HTTP SESSION + RETRY
# =========================
SESSION = requests.Session()
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Streamlit PX-Web client)",
    "Accept": "application/json",
}

def get_with_retry(url: str, retries: int = 6, timeout: int = 30) -> requests.Response:
    """GET cu retry + exponential backoff pentru 429."""
    last = None
    for i in range(retries):
        try:
            r = SESSION.get(url, timeout=timeout, headers=DEFAULT_HEADERS)
            last = r
            if r.status_code == 200:
                return r
            if r.status_code == 429:
                wait = (2 ** i) + random.random()
                time.sleep(wait)
                continue
            return r
        except requests.RequestException:
            wait = (2 ** i) + random.random()
            time.sleep(wait)
            last = None
    if last is not None:
        return last
    raise RuntimeError("Eroare rețea: nu s-a putut efectua GET după retry-uri.")

def post_with_retry(url: str, payload: dict, retries: int = 6, timeout: int = 60) -> requests.Response:
    """POST cu retry + exponential backoff pentru 429."""
    last = None
    for i in range(retries):
        try:
            r = SESSION.post(url, json=payload, timeout=timeout, headers=DEFAULT_HEADERS)
            last = r
            if r.status_code == 200:
                return r
            if r.status_code == 429:
                wait = (2 ** i) + random.random()
                time.sleep(wait)
                continue
            return r
        except requests.RequestException:
            wait = (2 ** i) + random.random()
            time.sleep(wait)
            last = None
    if last is not None:
        return last
    raise RuntimeError("Eroare rețea: nu s-a putut efectua POST după retry-uri.")

# =========================
# CACHED CALLS
# =========================
@st.cache_data(ttl=3600, show_spinner=False)
def list_directory(url_base_dir: str) -> list:
    """Listează item-urile dintr-un director PX-Web. Cache 1 oră."""
    r = get_with_retry(url_base_dir)
    if r.status_code != 200:
        raise RuntimeError(f"Directory error {r.status_code}: {r.text[:300]}")
    return r.json()

@st.cache_data(ttl=3600, show_spinner=False)
def get_metadata(url_table: str) -> dict:
    """Metadate pentru un tabel PX-Web. Cache 1 oră."""
    r = get_with_retry(url_table)
    if r.status_code == 200:
        try:
            return r.json()
        except Exception:
            return {}
    return {}

# =========================
# HELPERS
# =========================
def _norm(s: str) -> str:
    """lower + remove diacritics + trim"""
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s

def detect_time_column(cols):
    """Detectează coloana timp (an/lună/trimestru/perioadă) din dataframe."""
    for col in cols:
        c = str(col).lower()
        if any(x in c for x in ["an", "ani", "luna", "luni", "lun", "trimestru", "perioad", "quarter", "month", "year", "time"]):
            return col
    return None

def pick_keys_for_upsert(df: pd.DataFrame, max_keys: int = 2) -> list[str]:
    """
    Alege chei rezonabile pentru upsert:
      1) An + Lună, dacă există
      2) An + Trimestru/Perioadă, dacă există
      3) Regiune + An, dacă există
      4) Altfel: primele 1-2 coloane diferite de 'Valoare'
    """
    cols = list(df.columns)
    if not cols:
        return []

    def find_by_norm(names):
        for c in cols:
            if _norm(c) in names:
                return c
        return None

    col_year = find_by_norm({"an", "ani", "year"})
    col_month = find_by_norm({"luna", "luni", "month"})
    col_q = None
    for c in cols:
        cn = _norm(c)
        if "trimestru" in cn or "quarter" in cn or "trim" == cn:
            col_q = c
            break
    col_region = None
    for c in cols:
        cn = _norm(c)
        if any(x in cn for x in ["regi", "raion", "municip", "localit", "zona", "region", "district"]):
            col_region = c
            break

    if col_year and col_month:
        return [col_year, col_month][:max_keys]
    if col_year and col_q:
        return [col_year, col_q][:max_keys]
    if col_region and col_year:
        return [col_region, col_year][:max_keys]
    if col_year:
        return [col_year][:max_keys]

    fallback = [c for c in cols if c != "Valoare"]
    return fallback[:max_keys] if fallback else []

def resolve_destination(save_code: str, table_name: str, table_url: str) -> tuple[Path, str, str]:
    """
    Returnează (excel_file, sheet_name, reason)
    - pornește de la destinația selectată (save_code)
    - apoi aplică reguli de routing pe foi (ex: Agricultura -> REAL/Agricultura)
    """
    base = SECTOR_EXPORTS[save_code]
    excel_file = base["file"]
    sheet_name = base["sheet"]
    reason = f"Destinație standard: {save_code}/{sheet_name}"

    context = _norm(f"{table_name or ''} {table_url or ''}")

    for keywords, sector_code, target_sheet in SHEET_ROUTING_RULES:
        if all(k in context for k in keywords):
            routed = SECTOR_EXPORTS[sector_code]
            excel_file = routed["file"]
            sheet_name = target_sheet
            reason = f"Routing activ: {keywords} => {sector_code}/{target_sheet}"
            break

    return excel_file, sheet_name, reason

# =========================
# GENERIC EXCEL UPSERT
# =========================
def excel_upsert(df: pd.DataFrame, excel_path: Path, sheet_name: str, keys: list[str]):
    if df.empty:
        st.warning("Nu am date de salvat (df gol).")
        return

    excel_path.parent.mkdir(parents=True, exist_ok=True)
    st.info(f"Scriere în: {excel_path.resolve()} | foaia: {sheet_name} | chei: {keys}")

    for k in keys:
        if k not in df.columns:
            st.error(f"Lipsește cheia '{k}' din date.")
            return

    if excel_path.exists():
        try:
            existing = pd.read_excel(excel_path, sheet_name=sheet_name)
        except Exception:
            existing = pd.DataFrame()
    else:
        existing = pd.DataFrame()

    if existing.empty:
        combined = df.copy()
    else:
        for k in keys:
            if k not in existing.columns:
                existing[k] = pd.NA

        new_keys = set(df[keys].astype(str).agg("|".join, axis=1))
        keep_mask = ~existing[keys].astype(str).agg("|".join, axis=1).isin(new_keys)
        existing_kept = existing.loc[keep_mask].copy()
        combined = pd.concat([existing_kept, df], ignore_index=True)

    try:
        if excel_path.exists():
            with pd.ExcelWriter(excel_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
                combined.to_excel(writer, sheet_name=sheet_name, index=False)
        else:
            with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
                combined.to_excel(writer, sheet_name=sheet_name, index=False)
    except PermissionError:
        st.error("Nu pot scrie în Excel: fișierul este deschis/blocat. Închide fișierul și încearcă din nou.")
        return

    st.success(f"Salvat: {excel_path.name} → '{sheet_name}' (înscris pe {keys}).")
    st.caption("Previzualizare (ultimele 50 rânduri):")
    st.dataframe(combined.tail(50), use_container_width=True)

# =========================
# SALVARE SPECIALĂ: Exp_Lunar (Export/Import/Sold)
# =========================
def save_exp_lunar_to_excel(df_px: pd.DataFrame, excel_path: Path, sheet_name: str = "Exp_Lunar"):
    if df_px.empty:
        st.warning("Nu am date de salvat (df gol).")
        return

    st.info(f"Scriere Exp_Lunar în: {excel_path.resolve()} | foaia: {sheet_name}")

    col_ind = next((c for c in df_px.columns if "indicator" in _norm(c)), None)
    col_year = next((c for c in df_px.columns if _norm(c) in ["ani", "an", "year"]), None)
    col_month = next((c for c in df_px.columns if _norm(c) in ["luni", "luna", "month"]), None)

    if not col_ind or not col_year or not col_month or "Valoare" not in df_px.columns:
        st.warning(
            "Exp_Lunar: nu am găsit coloanele necesare (Indicator/An/Lună/Valoare). "
            "Dacă tabelul nu e cel de comerț lunar, e normal."
        )
        return

    dfw = df_px.copy()

    col_group = next((c for c in dfw.columns if "grupe" in _norm(c) and "tari" in _norm(c)), None)
    if col_group:
        dfw = dfw[dfw[col_group].astype(str).apply(_norm).str.contains("total", na=False)]

    dfw["_ind_norm"] = dfw[col_ind].astype(str).apply(_norm)

    wanted = {"exporturi", "importuri", "balanta comerciala"}
    dfw = dfw[dfw["_ind_norm"].isin(wanted)].copy()

    if dfw.empty:
        st.warning("Exp_Lunar: nu există Exporturi/Importuri/Balanța comercială în selecția curentă.")
        return

    dfw[col_year] = pd.to_numeric(dfw[col_year], errors="coerce")
    dfw = dfw.dropna(subset=[col_year, col_month])

    pivot = (
        dfw.pivot_table(index=[col_year, col_month], columns="_ind_norm", values="Valoare", aggfunc="sum")
        .reset_index()
    )

    pivot = pivot.rename(columns={
        col_year: "An",
        col_month: "Lună",
        "exporturi": "Exporturi (mil. $)",
        "importuri": "Importuri (mil. $)",
        "balanta comerciala": "Sold Comercial (mil. $)",
    })

    needed = ["An", "Lună", "Exporturi (mil. $)", "Importuri (mil. $)", "Sold Comercial (mil. $)"]
    for c in needed:
        if c not in pivot.columns:
            pivot[c] = pd.NA
    pivot = pivot[needed].copy()

    pivot["An"] = pd.to_numeric(pivot["An"], errors="coerce").astype("Int64")
    pivot = pivot.dropna(subset=["An", "Lună"])

    if pivot.empty:
        st.warning("Exp_Lunar: pivot gol (nu am An/Lună valide).")
        return

    excel_path.parent.mkdir(parents=True, exist_ok=True)
    if excel_path.exists():
        try:
            existing = pd.read_excel(excel_path, sheet_name=sheet_name)
        except Exception:
            existing = pd.DataFrame(columns=needed)
    else:
        existing = pd.DataFrame(columns=needed)

    if "An" in existing.columns:
        existing["An"] = pd.to_numeric(existing["An"], errors="coerce").astype("Int64")
    else:
        existing["An"] = pd.Series(dtype="Int64")
    if "Lună" not in existing.columns:
        existing["Lună"] = pd.NA

    key_new = set((int(a), str(l)) for a, l in zip(pivot["An"], pivot["Lună"]))

    if not existing.empty:
        keep_mask = ~existing.apply(
            lambda r: ((int(r["An"]) if pd.notna(r["An"]) else -1), str(r["Lună"])) in key_new,
            axis=1
        )
        existing = existing[keep_mask].copy()

    combined = pd.concat([existing, pivot], ignore_index=True)

    month_order = {
        "ianuarie": 1, "februarie": 2, "martie": 3, "aprilie": 4, "mai": 5, "iunie": 6,
        "iulie": 7, "august": 8, "septembrie": 9, "octombrie": 10, "noiembrie": 11, "decembrie": 12
    }
    combined["_m"] = combined["Lună"].astype(str).apply(_norm).map(month_order)
    combined = combined.sort_values(["An", "_m", "Lună"], kind="stable").drop(columns=["_m"])

    try:
        if excel_path.exists():
            with pd.ExcelWriter(excel_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
                combined.to_excel(writer, sheet_name=sheet_name, index=False)
        else:
            with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
                combined.to_excel(writer, sheet_name=sheet_name, index=False)
    except PermissionError:
        st.error("Exp_Lunar: nu pot scrie în Excel: fișierul este deschis/blocat.")
        return

    st.success(f"Exp_Lunar salvat: {excel_path.name} → '{sheet_name}' (upsert An+Lună).")
    st.caption("Previzualizare Exp_Lunar (ultimele 50 rânduri):")
    st.dataframe(combined.tail(50), use_container_width=True)

# =========================
# SIDEBAR – SELECT DOMAIN
# =========================
st.sidebar.header("1) Domeniul")
domain_label = st.sidebar.selectbox("Alege domeniul", [d["text"] for d in DOMAINS])
domain_dbid = next(d["dbid"] for d in DOMAINS if d["text"] == domain_label)
domain_url = f"{API_ROOT}/{domain_dbid}"

# =========================
# SIDEBAR – NAVIGATOR
# =========================
st.sidebar.header("2) Navigare foldere")
st.sidebar.caption("Navighează până alegi un tabel (metadata cu variabile).")

if "nav_path" not in st.session_state:
    st.session_state["nav_path"] = []
if "nav_items" not in st.session_state:
    st.session_state["nav_items"] = None
if "nav_domain" not in st.session_state:
    st.session_state["nav_domain"] = None
if "selected_table_url" not in st.session_state:
    st.session_state["selected_table_url"] = None
if "selected_table_name" not in st.session_state:
    st.session_state["selected_table_name"] = None

if st.session_state["nav_domain"] != domain_dbid:
    st.session_state["nav_domain"] = domain_dbid
    st.session_state["nav_path"] = []
    st.session_state["nav_items"] = None
    st.session_state["selected_table_url"] = None
    st.session_state["selected_table_name"] = None

def build_current_url() -> str:
    if not st.session_state["nav_path"]:
        return domain_url
    return domain_url + "/" + "/".join(st.session_state["nav_path"])

current_dir_url = build_current_url()

colA, colB = st.sidebar.columns([1, 1])
with colA:
    if st.button("Încarcă folderul"):
        try:
            st.session_state["nav_items"] = list_directory(current_dir_url)
            st.sidebar.success("Folder încărcat.")
        except Exception as e:
            st.sidebar.error(f"Eroare director: {e}")
with colB:
    if st.button("Înapoi"):
        if st.session_state["nav_path"]:
            st.session_state["nav_path"] = st.session_state["nav_path"][:-1]
            st.session_state["nav_items"] = None
            st.session_state["selected_table_url"] = None
            st.session_state["selected_table_name"] = None
            st.rerun()

st.sidebar.markdown("**Cale curentă:**")
st.sidebar.code("/".join([domain_dbid] + st.session_state["nav_path"]) or domain_dbid)

items = st.session_state["nav_items"]
if not items:
    st.info("Alege domeniul, apoi apasă «Încarcă folderul».")
    st.stop()

options = []
id_by_label = {}
for it in items:
    if "id" in it and "text" in it:
        label = f'{it["text"]}  [{it["id"]}]'
        options.append(label)
        id_by_label[label] = it["id"]

selected_label = st.sidebar.selectbox("Selectează item", options)
selected_id = id_by_label[selected_label]
candidate_url = current_dir_url.rstrip("/") + "/" + selected_id

meta_candidate = get_metadata(candidate_url)
is_table = bool(meta_candidate and isinstance(meta_candidate, dict) and "variables" in meta_candidate)

nav_cols = st.sidebar.columns([1, 1])
with nav_cols[0]:
    if st.button("Deschide"):
        if is_table:
            st.session_state["selected_table_url"] = candidate_url
            st.session_state["selected_table_name"] = selected_label
            st.sidebar.success("Tabel selectat.")
        else:
            st.session_state["nav_path"].append(selected_id)
            st.session_state["nav_items"] = None
            st.session_state["selected_table_url"] = None
            st.session_state["selected_table_name"] = None
            st.rerun()

with nav_cols[1]:
    if st.button("Reset navigare"):
        st.session_state["nav_path"] = []
        st.session_state["nav_items"] = None
        st.session_state["selected_table_url"] = None
        st.session_state["selected_table_name"] = None
        st.rerun()

table_url = st.session_state.get("selected_table_url")
table_name = st.session_state.get("selected_table_name")

st.sidebar.header("3) Salvare")
save_to = st.sidebar.selectbox("Destinație Excel", SAVE_CHOICES)

if not table_url:
    st.warning("Navighează până alegi un **tabel** și apasă «Deschide».")
    st.stop()

st.markdown("### Tabel selectat")
st.write(table_name)
st.caption(table_url)

# =========================
# METADATA & FILTERS
# =========================
metadata = get_metadata(table_url)
if not metadata or "variables" not in metadata:
    st.warning("Nu s-au putut încărca variabilele pentru acest tabel.")
    st.stop()

st.sidebar.header("4) Filtre (dimensiuni)")

dimensiuni = {}
coduri_dim = {}

for dim in metadata["variables"]:
    nume = dim.get("text", "")
    cod = dim.get("code", "")
    valori = dim.get("values", [])
    etichete = dim.get("valueTexts", [])
    optiuni = dict(zip(valori, etichete))
    if nume and cod and optiuni:
        dimensiuni[nume] = optiuni
        coduri_dim[nume] = cod

selectii = {}
for nume_dim, optiuni in dimensiuni.items():
    chei = list(optiuni.keys())
    etichete = list(optiuni.values())
    default_labels = etichete[:1] if len(etichete) > 0 else []
    selectie_labels = st.sidebar.multiselect(nume_dim, etichete, default=default_labels)
    valori_selectate = [chei[etichete.index(lbl)] for lbl in selectie_labels if lbl in etichete]
    if valori_selectate:
        selectii[nume_dim] = valori_selectate

payload = {"query": [], "response": {"format": "json-stat2"}}
for nume_dim, cod in coduri_dim.items():
    values = selectii.get(nume_dim, list(dimensiuni[nume_dim].keys())[:1])
    payload["query"].append({
        "code": cod,
        "selection": {"filter": "item", "values": values}
    })

# =========================
# MAIN ACTION
# =========================
if st.sidebar.button("Afișează datele"):
    r = post_with_retry(table_url, payload)

    if r.status_code != 200:
        st.error(f"Eroare API (POST): {r.status_code} | {r.text[:300]}")
        st.stop()

    try:
        data = r.json()
        if "value" not in data or "dimension" not in data:
            st.error("Răspuns API invalid: lipsesc câmpuri necesare ('value'/'dimension').")
            st.stop()

        valori = data["value"]
        dim_order = [d for d in data["dimension"].keys() if d not in ["id", "size"]]

        categorii = []
        for dim in dim_order:
            cat = data["dimension"][dim]["category"]
            labels = list(cat["label"].values())
            categorii.append(labels)

        index = pd.MultiIndex.from_product(categorii, names=dim_order)
        df = pd.DataFrame(valori, index=index, columns=["Valoare"]).reset_index()

        st.success("Date preluate cu succes!")
        st.dataframe(df, use_container_width=True)

        col_timp = detect_time_column(df.columns)
        if col_timp:
            color_col = next((c for c in df.columns if c not in [col_timp, "Valoare"]), None)
            if color_col:
                fig = px.line(df, x=col_timp, y="Valoare", color=color_col, markers=True, title="Evoluția indicatorului")
            else:
                fig = px.line(df, x=col_timp, y="Valoare", markers=True, title="Evoluția indicatorului")
            st.plotly_chart(fig, use_container_width=True)

        # =========================
        # SALVARE: dacă e AGRICULTURA => Real.xlsx / foaia "Agricultura"
        # altfel: salvează în destinația selectată
        # =========================
        if save_to != "Nu salva":
            save_code = SAVE_MAP[save_to]

            # routing pe foi (Agricultura etc.)
            excel_file, sheet_name, reason = resolve_destination(save_code, table_name, table_url)
            st.caption(f"Destinație finală: **{excel_file.name} / {sheet_name}** | {reason}")

            # dacă user a ales Extern, păstrăm salvarea specială (doar pe foaia Exp_Lunar)
            if save_code == "EXT_LUNAR":
                dest = SECTOR_EXPORTS["EXT_LUNAR"]
                save_exp_lunar_to_excel(df, dest["file"], dest["sheet"])
            else:
                keys = pick_keys_for_upsert(df, max_keys=2)
                if not keys:
                    st.warning("Nu am putut detecta chei pentru upsert. Nu salvez.")
                else:
                    excel_upsert(df, excel_file, sheet_name, keys=keys)

        # =========================
        # EXPORT EXCEL (download) – pentru sesiunea curentă
        # =========================
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Date")

        st.download_button(
            "Descarcă Excel (datele curente)",
            output.getvalue(),
            file_name="pxweb_export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Eroare la procesarea datelor: {str(e)}")
