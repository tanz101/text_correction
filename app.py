import pandas as pd
import streamlit as st
from rapidfuzz import fuzz
import networkx as nx
import pdfplumber
from datetime import datetime

PREFIXES = ("HB ", "HC ")

# ── Grouping logic ───────────────────────────────────────────────────────────

def _fuzzy_components(services, threshold):
    """Return connected components of fuzzy-matched service names."""
    G = nx.Graph()
    G.add_nodes_from(range(len(services)))
    for i in range(len(services)):
        for j in range(i + 1, len(services)):
            if fuzz.token_sort_ratio(services[i], services[j]) >= threshold:
                G.add_edge(i, j)
    return list(nx.connected_components(G))


@st.cache_data
def build_groups(df, threshold=80):
    groups = {}

    code_col = df["Service Code"].astype(str).str.strip()
    provider_col = df["Provider"].astype(str).str.strip()

    # Pass 1: group by Service Code (groupby is much faster than iterrows)
    coded_mask = ~code_col.isin(["", "nan"])
    for code, grp in df[coded_mask].groupby(code_col[coded_mask]):
        for service, sub in grp.groupby("Service"):
            groups.setdefault(f"CODE:{code}", {}).setdefault(service, []).extend(sub.index.tolist())

    # Pass 2: for rows without a Service Code, fuzzy-match within each Provider
    uncoded = df[~coded_mask]
    uncoded_provider = provider_col[uncoded.index]

    for provider, prov_grp in uncoded.groupby(uncoded_provider):
        if not provider or provider == "nan":
            continue
        service_index = {svc: list(sub.index) for svc, sub in prov_grp.groupby("Service")}
        unique_services = list(service_index.keys())
        for component in _fuzzy_components(unique_services, threshold):
            if len(component) < 2:
                continue
            members = [unique_services[i] for i in component]
            key = f"PROVIDER:{provider}:{members[0]}"
            for variant in members:
                groups.setdefault(key, {}).setdefault(variant, []).extend(service_index[variant])

    # Pass 3: fuzzy-match rows with neither Service Code nor Provider
    no_provider = uncoded[uncoded_provider.isin(["", "nan"])]
    service_index = {svc: list(sub.index) for svc, sub in no_provider.groupby("Service")}
    unique_services = list(service_index.keys())
    for component in _fuzzy_components(unique_services, threshold):
        if len(component) < 2:
            continue
        members = [unique_services[i] for i in component]
        key = f"TEXT:{members[0]}"
        for variant in members:
            groups.setdefault(key, {}).setdefault(variant, []).extend(service_index[variant])

    # Only return groups with more than one distinct variant
    return {k: v for k, v in groups.items() if len(v) > 1}


@st.cache_data
def load_data(uploaded_file):
    return pd.read_csv(uploaded_file)


@st.cache_data
def find_prefix_rows(df):
    return df[df["Service"].astype(str).str.startswith(PREFIXES)].index.tolist()


@st.cache_data
def extract_pdf_charges(pdf_file):
    """Extract charges from PDF table using OCR"""
    try:
        with pdfplumber.open(pdf_file) as pdf:
            tables = pdf.pages[0].extract_tables()
            if tables:
                # Assumes first row is header
                df = pd.DataFrame(tables[0][1:], columns=tables[0][0])
                # Clean and normalize columns
                df.columns = df.columns.str.strip().str.lower()
                return df
    except Exception as e:
        st.error(f"Error extracting PDF: {e}")
    return None


def normalize_for_matching(df, amount_col, desc_col, date_col):
    """Normalize data for comparison"""
    df = df.copy()
    # Convert amounts to float
    df[amount_col] = pd.to_numeric(df[amount_col], errors='coerce')
    # Normalize descriptions (lowercase, strip whitespace)
    df[desc_col] = df[desc_col].astype(str).str.strip().str.lower()
    # Parse dates
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    return df


def compare_charges(pdf_charges, excel_charges, amount_col, desc_col, date_col):
    """Match PDF charges against Excel charges"""
    matches = []
    unmatched_pdf = []
    
    for pdf_idx, pdf_row in pdf_charges.iterrows():
        best_match = None
        best_score = 0
        
        for excel_idx, excel_row in excel_charges.iterrows():
            # Multi-criteria scoring
            amount_match = 1.0 if abs(pdf_row[amount_col] - excel_row[amount_col]) < 0.01 else 0.0
            desc_score = fuzz.ratio(pdf_row[desc_col], excel_row[desc_col]) / 100
            date_match = 1.0 if pdf_row[date_col].date() == excel_row[date_col].date() else 0.0
            
            # Weighted score: 50% amount, 30% description, 20% date
            combined_score = (amount_match * 0.5) + (desc_score * 0.3) + (date_match * 0.2)
            
            if combined_score > best_score:
                best_score = combined_score
                best_match = (excel_idx, excel_row.to_dict(), combined_score)
        
        if best_score > 0.7:  # 70% threshold
            matches.append({
                'pdf_idx': pdf_idx,
                'excel_idx': best_match[0] if best_match else None,
                'pdf_charge': pdf_row[amount_col],
                'excel_charge': best_match[1][amount_col] if best_match else None,
                'match_score': best_score,
                'status': '✅ MATCH' if best_score > 0.95 else '⚠️ REVIEW'
            })
        else:
            unmatched_pdf.append({
                'pdf_idx': pdf_idx,
                'amount': pdf_row[amount_col],
                'description': pdf_row[desc_col],
                'date': pdf_row[date_col],
                'status': '❌ NOT FOUND'
            })
    
    return pd.DataFrame(matches), pd.DataFrame(unmatched_pdf)


# ── Streamlit UI ─────────────────────────────────────────────────────────────

st.set_page_config(page_title="Service Name Corrector", layout="wide")
st.title("Service Name Correction Tool")

uploaded = st.file_uploader("Upload CSV", type="csv")
if not uploaded:
    st.info("Upload Book1.csv to begin.")
    st.stop()

df = load_data(uploaded)

# Identify the ID column (first column named "#")
id_col = df.columns[0]

threshold = st.slider("Fuzzy match threshold (%)", 60, 100, 80)
groups = build_groups(df, threshold)

if not groups:
    st.success("No inconsistencies found at this threshold.")
    st.stop()

st.write(f"**{len(groups)} group(s) with inconsistent names found.**")
st.divider()

# corrections[key] = (canonical_string, {variant: [row_indices_to_correct]})
corrections = {}

for key, variants in groups.items():
    if key.startswith("CODE:"):
        label = f"Code: {key[5:]}"
    elif key.startswith("PROVIDER:"):
        provider_name = key[9:].split(":", 1)[0]
        label = f"Provider: {provider_name}"
    elif key.startswith("TEXT:"):
        label = f"Text match: {key[5:]}"
    else:
        label = key

    with st.expander(f"Group — {label}", expanded=True):

        skip = st.checkbox("Skip this group (no corrections applied)", key=f"skip_{key}")
        if skip:
            continue

        # ── Canonical name selector ──────────────────────────────────────────
        suggested = max(variants, key=lambda v: len(variants[v]))
        options = list(variants.keys()) + ["✏️ Enter custom..."]
        choice = st.selectbox(
            "Correct name to apply:",
            options,
            index=options.index(suggested),
            key=f"sel_{key}",
        )
        if choice == "✏️ Enter custom...":
            choice = st.text_input("Custom name:", key=f"txt_{key}")

        st.markdown("**Select variants to correct** (uncheck to exclude):")

        # ── Per-variant checkboxes ───────────────────────────────────────────
        included_indices = {variant: [] for variant in variants}

        header = st.columns([1, 5, 2])
        header[0].markdown("**Include**")
        header[1].markdown("**Variant**")
        header[2].markdown("**Rows**")

        for variant, row_indices in variants.items():
            # Variant matching the chosen canonical is already correct — default unchecked
            default = variant != choice
            row_cols = st.columns([1, 5, 2])
            include = row_cols[0].checkbox(
                "",
                value=default,
                key=f"chk_{key}_{variant}",
                label_visibility="collapsed",
            )
            row_cols[1].write(variant)
            row_cols[2].write(len(row_indices))

            if include:
                included_indices[variant] = list(row_indices)

        if choice:
            corrections[key] = (choice, included_indices)

# ── Prefix Removal ───────────────────────────────────────────────────────────

prefix_indices = find_prefix_rows(df)

prefix_corrections = {}  # idx -> stripped name

if prefix_indices:
    st.divider()
    st.subheader("Prefix Removal — \"HB \" / \"HC \"")
    st.write(f"{len(prefix_indices)} row(s) have a service name starting with `HB ` or `HC `.")

    skip_prefixes = st.checkbox("Skip prefix removal", key="skip_prefixes")

    if not skip_prefixes:
        header = st.columns([1, 5, 5])
        header[0].markdown("**Include**")
        header[1].markdown("**Current Service**")
        header[2].markdown("**Corrected Service**")

        for idx in prefix_indices:
            current = df.loc[idx, "Service"]
            stripped = current
            for pfx in PREFIXES:
                if stripped.startswith(pfx):
                    stripped = stripped[len(pfx):]
                    break
            row_cols = st.columns([1, 5, 5])
            include = row_cols[0].checkbox(
                "",
                value=True,
                key=f"pfx_{idx}",
                label_visibility="collapsed",
            )
            row_cols[1].write(current)
            row_cols[2].write(stripped)
            if include:
                prefix_corrections[idx] = stripped

# ── Apply & Download ──────────────────────────────────────────────────────────

st.divider()
if st.button("Apply Corrections & Download", type="primary"):
    df_out = df.copy()
    total_fixed = 0
    for key, (canonical, variant_map) in corrections.items():
        for variant, row_indices in variant_map.items():
            if variant != canonical:
                df_out.loc[row_indices, "Service"] = canonical
                total_fixed += len(row_indices)

    if prefix_corrections:
        for idx, stripped in prefix_corrections.items():
            df_out.loc[idx, "Service"] = stripped
        total_fixed += len(prefix_corrections)

    st.success(f"Corrected {total_fixed} row(s) across {len(corrections)} group(s) + {len(prefix_corrections)} prefix removal(s).")
    csv_bytes = df_out.to_csv(index=False).encode()
    st.download_button(
        "Download corrected CSV",
        data=csv_bytes,
        file_name="Book1_corrected.csv",
        mime="text/csv",
    )


# ── PDF vs Excel Charge Comparison ───────────────────────────────────────────

st.divider()
st.header("📊 PDF vs Excel Charge Comparison")

tab1, tab2 = st.tabs(["Charge Comparison", "Settings"])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        pdf_file = st.file_uploader("Upload PDF (charges)", type="pdf", key="pdf_charges")
    
    with col2:
        excel_file = st.file_uploader("Upload Excel (charges)", type=["xlsx", "xls"], key="excel_charges")
    
    if pdf_file and excel_file:
        # Extract from PDF
        pdf_df = extract_pdf_charges(pdf_file)
        
        if pdf_df is not None:
            st.write("**PDF Columns detected:**", list(pdf_df.columns))
            
            # Column mappers
            col_left, col_mid, col_right = st.columns(3)
            with col_left:
                pdf_amount = st.selectbox("PDF Amount column", pdf_df.columns, key="pdf_amt")
            with col_mid:
                pdf_desc = st.selectbox("PDF Description column", pdf_df.columns, key="pdf_desc")
            with col_right:
                pdf_date = st.selectbox("PDF Date column", pdf_df.columns, key="pdf_date")
            
            # Load Excel
            excel_df = pd.read_excel(excel_file)
            st.write("**Excel Columns detected:**", list(excel_df.columns))
            
            col_left, col_mid, col_right = st.columns(3)
            with col_left:
                excel_amount = st.selectbox("Excel Amount column", excel_df.columns, key="excel_amt")
            with col_mid:
                excel_desc = st.selectbox("Excel Description column", excel_df.columns, key="excel_desc")
            with col_right:
                excel_date = st.selectbox("Excel Date column", excel_df.columns, key="excel_date")
            
            # Run comparison
            if st.button("Compare Charges", type="primary"):
                pdf_norm = normalize_for_matching(pdf_df, pdf_amount, pdf_desc, pdf_date)
                excel_norm = normalize_for_matching(excel_df, excel_amount, excel_desc, excel_date)
                
                matches_df, unmatched_df = compare_charges(
                    pdf_norm, excel_norm, pdf_amount, pdf_desc, pdf_date
                )
                
                # Display results
                st.subheader("Matched Charges")
                matched_count = len(matches_df[matches_df['status'] == '✅ MATCH'])
                review_count = len(matches_df[matches_df['status'] == '⚠️ REVIEW'])
                
                col1, col2 = st.columns(2)
                col1.metric("Exact Matches", matched_count)
                col2.metric("Needs Review", review_count)
                
                st.dataframe(matches_df, use_container_width=True)
                
                if len(unmatched_df) > 0:
                    st.subheader("Unmatched PDF Charges")
                    st.dataframe(unmatched_df, use_container_width=True)
                    
                    # Download unmatched for manual review
                    csv_unmatched = unmatched_df.to_csv(index=False).encode()
                    st.download_button(
                        "Download unmatched charges",
                        data=csv_unmatched,
                        file_name="unmatched_charges.csv",
                        mime="text/csv"
                    )

with tab2:
    st.write("**Comparison Settings:**")
    st.info("""
    - **Exact Match**: 95%+ score (amount exact, description ≈90% similar, date matches)
    - **Review**: 70-95% score (partial matches that need verification)
    - **Unmatched**: <70% score (likely missing or incorrectly recorded)
    
    Scoring weights:
    - 50% Charge Amount
    - 30% Description (fuzzy matching)
    - 20% Date
    """)
