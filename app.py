import pandas as pd
import streamlit as st
from rapidfuzz import fuzz
import networkx as nx

# ── Grouping logic ───────────────────────────────────────────────────────────

def build_groups(df, threshold=80):
    groups = {}

    code_col = df["Service Code"].astype(str).str.strip()

    # Pass 1: group by Service Code
    for idx, row in df.iterrows():
        code = code_col[idx]
        if code and code != "nan":
            groups.setdefault(f"CODE:{code}", {}) \
                  .setdefault(row["Service"], []).append(idx)

    # Pass 2: fuzzy-match rows without a Service Code
    uncoded = df[code_col.isin(["", "nan"])].copy()
    unique_services = uncoded["Service"].unique().tolist()

    G = nx.Graph()
    G.add_nodes_from(range(len(unique_services)))
    for i in range(len(unique_services)):
        for j in range(i + 1, len(unique_services)):
            score = fuzz.token_sort_ratio(unique_services[i], unique_services[j])
            if score >= threshold:
                G.add_edge(i, j)

    for component in nx.connected_components(G):
        members = [unique_services[i] for i in component]
        key = f"TEXT:{members[0]}"
        for variant in members:
            row_indices = uncoded[uncoded["Service"] == variant].index.tolist()
            groups.setdefault(key, {}).setdefault(variant, []).extend(row_indices)

    # Only return groups with more than one distinct variant
    return {k: v for k, v in groups.items() if len(v) > 1}


# ── Streamlit UI ─────────────────────────────────────────────────────────────

st.set_page_config(page_title="Service Name Corrector", layout="wide")
st.title("Service Name Correction Tool")

uploaded = st.file_uploader("Upload CSV", type="csv")
if not uploaded:
    st.info("Upload Book1.csv to begin.")
    st.stop()

df = pd.read_csv(uploaded)

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
    label = key.replace("CODE:", "Code: ").replace("TEXT:", "Text match: ")

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

    st.success(f"Corrected {total_fixed} row(s) across {len(corrections)} group(s).")
    csv_bytes = df_out.to_csv(index=False).encode()
    st.download_button(
        "Download corrected CSV",
        data=csv_bytes,
        file_name="Book1_corrected.csv",
        mime="text/csv",
    )
