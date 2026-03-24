import pandas as pd
import streamlit as st
from rapidfuzz import fuzz
import networkx as nx

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


def build_groups(df, threshold=80):
    groups = {}

    code_col = df["Service Code"].astype(str).str.strip()
    provider_col = df["Provider"].astype(str).str.strip()

    # Pass 1: group by Service Code
    for idx, row in df.iterrows():
        code = code_col[idx]
        if code and code != "nan":
            groups.setdefault(f"CODE:{code}", {}) \
                  .setdefault(row["Service"], []).append(idx)

    # Pass 2: for rows without a Service Code, fuzzy-match within each Provider
    uncoded = df[code_col.isin(["", "nan"])].copy()

    for provider in provider_col[uncoded.index].unique():
        if not provider or provider == "nan":
            continue
        subset = uncoded[provider_col[uncoded.index] == provider]
        unique_services = subset["Service"].unique().tolist()
        for component in _fuzzy_components(unique_services, threshold):
            if len(component) < 2:
                continue
            members = [unique_services[i] for i in component]
            key = f"PROVIDER:{provider}:{members[0]}"
            for variant in members:
                row_indices = subset[subset["Service"] == variant].index.tolist()
                groups.setdefault(key, {}).setdefault(variant, []).extend(row_indices)

    # Pass 3: fuzzy-match rows with neither Service Code nor Provider
    no_provider = uncoded[provider_col[uncoded.index].isin(["", "nan"])]
    unique_services = no_provider["Service"].unique().tolist()
    for component in _fuzzy_components(unique_services, threshold):
        if len(component) < 2:
            continue
        members = [unique_services[i] for i in component]
        key = f"TEXT:{members[0]}"
        for variant in members:
            row_indices = no_provider[no_provider["Service"] == variant].index.tolist()
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

PREFIXES = ("HB ", "HC ")

prefix_indices = df[df["Service"].astype(str).str.startswith(PREFIXES)].index.tolist()

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
