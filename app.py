"""
Offline Document Anonymiser — Streamlit UI

Upload documents (PDF, Excel, Word, CSV, Text), detect PII entities,
review and toggle which to anonymise, download anonymised files + mapping key.

100 % offline — spaCy NER + regex, no external API calls.
"""

from __future__ import annotations

import sys
import os

# Ensure project root is on sys.path so local imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

from config import SPACY_MODEL
from entity_registry import EntityRegistry
from detectors.ner_detector import detect_ner_entities, DetectedEntity
from detectors.regex_detector import detect_regex_entities
from anonymiser import anonymise_text
from utils import detect_file_type, merge_entity_lists

from file_io.text_handler import read_text, write_text
from file_io.csv_handler import read_csv, write_csv
from file_io.excel_handler import read_excel, write_excel
from file_io.word_handler import read_word, write_word
from file_io.pdf_handler import read_pdf, write_pdf, is_scanned_pdf

# ──────────────────────────────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────────────────────────────
import de_anonymiser

st.set_page_config(
    page_title="Offline Document Anonymiser",
    page_icon="🔒",
    layout="wide",
)

# ──────────────────────────────────────────────────────────────────────
# Sidebar — page navigation
# ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    page = st.radio("Mode", ["Anonymise", "De-Anonymise"], index=0)
    st.divider()

# ──────────────────────────────────────────────────────────────────────
# De-Anonymise page (separate flow)
# ──────────────────────────────────────────────────────────────────────
if page == "De-Anonymise":
    st.title("Offline Document De-Anonymiser")
    st.caption("100 % offline. Restore original content using a mapping key.")
    de_anonymiser.render()
    st.stop()

# ──────────────────────────────────────────────────────────────────────
# Anonymise page (default)
# ──────────────────────────────────────────────────────────────────────
st.title("Offline Document Anonymiser")
st.caption("100 % offline — spaCy NER + regex. No data leaves your machine.")


# ──────────────────────────────────────────────────────────────────────
# Load spaCy model (cached)
# ──────────────────────────────────────────────────────────────────────
@st.cache_resource
def load_nlp():
    import spacy
    return spacy.load(SPACY_MODEL)


try:
    nlp = load_nlp()
except OSError:
    st.error(
        f"spaCy model **{SPACY_MODEL}** not found. "
        f"Run: `python -m spacy download {SPACY_MODEL}`"
    )
    st.stop()


# ──────────────────────────────────────────────────────────────────────
# Session state defaults
# ──────────────────────────────────────────────────────────────────────
if "registry" not in st.session_state:
    st.session_state.registry = EntityRegistry()
if "file_data" not in st.session_state:
    st.session_state.file_data = {}  # filename -> {type, raw_bytes, obj, text, entities}
if "detected" not in st.session_state:
    st.session_state.detected = False
if "anonymised_outputs" not in st.session_state:
    st.session_state.anonymised_outputs = {}


# ──────────────────────────────────────────────────────────────────────
# Sidebar — file upload
# ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Upload Files")
    uploaded_files = st.file_uploader(
        "Drag and drop or browse",
        type=["pdf", "xlsx", "docx", "csv", "txt"],
        accept_multiple_files=True,
    )

    if st.button("Reset Session"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


# ──────────────────────────────────────────────────────────────────────
# Step 1 — Detect entities
# ──────────────────────────────────────────────────────────────────────
if uploaded_files:
    if st.button("Detect Entities", type="primary"):
        st.session_state.registry = EntityRegistry()
        st.session_state.file_data = {}
        st.session_state.detected = False
        st.session_state.anonymised_outputs = {}

        progress = st.progress(0, text="Processing files...")

        for i, uf in enumerate(uploaded_files):
            progress.progress(
                (i) / len(uploaded_files),
                text=f"Processing {uf.name}...",
            )
            raw = uf.read()
            ftype = detect_file_type(uf.name)

            obj = None
            text = ""
            warnings: list[str] = []

            if ftype == "text":
                text = read_text(raw)
            elif ftype == "csv":
                obj, text = read_csv(raw)
            elif ftype == "excel":
                obj, text = read_excel(raw)
            elif ftype == "word":
                obj, text = read_word(raw)
            elif ftype == "pdf":
                obj, text = read_pdf(raw)
                if is_scanned_pdf(obj):
                    warnings.append(
                        "This PDF appears to be scanned (very little text detected). "
                        "OCR is not supported — anonymisation may be incomplete."
                    )

            # Run detection
            ner_ents = detect_ner_entities(text, nlp)
            regex_ents = detect_regex_entities(text)
            merged = merge_entity_lists(ner_ents, regex_ents)

            st.session_state.file_data[uf.name] = {
                "type": ftype,
                "raw_bytes": raw,
                "obj": obj,
                "text": text,
                "entities": merged,
                "warnings": warnings,
            }

        progress.progress(1.0, text="Detection complete.")
        st.session_state.detected = True


# ──────────────────────────────────────────────────────────────────────
# Step 2 — Review entities
# ──────────────────────────────────────────────────────────────────────
if st.session_state.detected and st.session_state.file_data:
    st.subheader("Detected Entities")

    # Build a deduplicated entity summary across all files
    entity_summary: dict[str, dict] = {}  # text -> {label, count, files}
    for fname, fdata in st.session_state.file_data.items():
        for w in fdata.get("warnings", []):
            st.warning(f"**{fname}**: {w}")
        for ent in fdata["entities"]:
            key = ent.text
            if key not in entity_summary:
                entity_summary[key] = {
                    "label": ent.label,
                    "count": 0,
                    "files": set(),
                }
            entity_summary[key]["count"] += 1
            entity_summary[key]["files"].add(fname)

    if not entity_summary:
        st.info("No entities detected in the uploaded files.")
    else:
        st.write(f"Found **{len(entity_summary)}** unique entities across **{len(st.session_state.file_data)}** file(s).")

        # Initialise toggle state
        if "entity_toggles" not in st.session_state:
            st.session_state.entity_toggles = {}
        for text in entity_summary:
            if text not in st.session_state.entity_toggles:
                st.session_state.entity_toggles[text] = True

        # Select / deselect all
        col_sel1, col_sel2, _ = st.columns([1, 1, 4])
        with col_sel1:
            if st.button("Select All"):
                for k in st.session_state.entity_toggles:
                    st.session_state.entity_toggles[k] = True
                st.rerun()
        with col_sel2:
            if st.button("Deselect All"):
                for k in st.session_state.entity_toggles:
                    st.session_state.entity_toggles[k] = False
                st.rerun()

        # Entity table with checkboxes
        for text, info in sorted(entity_summary.items(), key=lambda x: x[1]["label"]):
            col1, col2, col3, col4 = st.columns([0.5, 3, 1.5, 1])
            with col1:
                st.session_state.entity_toggles[text] = st.checkbox(
                    "sel",
                    value=st.session_state.entity_toggles.get(text, True),
                    key=f"chk_{text}",
                    label_visibility="collapsed",
                )
            with col2:
                st.text(text)
            with col3:
                st.text(info["label"])
            with col4:
                st.text(f"x{info['count']}")

        # ──────────────────────────────────────────────────────────────
        # Step 3 — Anonymise
        # ──────────────────────────────────────────────────────────────
        st.divider()
        if st.button("Anonymise", type="primary"):
            skip = {
                text
                for text, selected in st.session_state.entity_toggles.items()
                if not selected
            }

            registry = EntityRegistry()
            st.session_state.registry = registry
            st.session_state.anonymised_outputs = {}

            with st.spinner("Anonymising files..."):
                for fname, fdata in st.session_state.file_data.items():
                    ftype = fdata["type"]
                    entities = fdata["entities"]

                    if ftype == "text":
                        anon_text = anonymise_text(
                            fdata["text"], entities, registry, skip
                        )
                        out_bytes = write_text(anon_text)

                    elif ftype == "csv":
                        # First pass through anonymiser to populate registry
                        anonymise_text(fdata["text"], entities, registry, skip)
                        out_bytes = write_csv(fdata["obj"], registry, skip)

                    elif ftype == "excel":
                        anonymise_text(fdata["text"], entities, registry, skip)
                        out_bytes = write_excel(fdata["obj"], registry, skip)

                    elif ftype == "word":
                        anonymise_text(fdata["text"], entities, registry, skip)
                        out_bytes = write_word(fdata["obj"], registry, skip)

                    elif ftype == "pdf":
                        anonymise_text(fdata["text"], entities, registry, skip)
                        out_bytes = write_pdf(fdata["obj"], registry, skip)

                    else:
                        anon_text = anonymise_text(
                            fdata["text"], entities, registry, skip
                        )
                        out_bytes = write_text(anon_text)

                    st.session_state.anonymised_outputs[fname] = out_bytes

            st.success(f"Anonymised {len(st.session_state.anonymised_outputs)} file(s).")

    # ──────────────────────────────────────────────────────────────────
    # Step 4 — Downloads
    # ──────────────────────────────────────────────────────────────────
    if st.session_state.anonymised_outputs:
        st.subheader("Download Anonymised Files")

        for fname, out_bytes in st.session_state.anonymised_outputs.items():
            ftype = detect_file_type(fname)
            mime_map = {
                "pdf": "application/pdf",
                "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "word": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "csv": "text/csv",
                "text": "text/plain",
            }
            ext_map = {
                "pdf": ".pdf",
                "excel": ".xlsx",
                "word": ".docx",
                "csv": ".csv",
                "text": ".txt",
            }
            base, _ = os.path.splitext(fname)
            anon_name = f"{base}_anonymised{ext_map.get(ftype, '.txt')}"

            st.download_button(
                label=f"Download {anon_name}",
                data=out_bytes,
                file_name=anon_name,
                mime=mime_map.get(ftype, "application/octet-stream"),
                key=f"dl_{fname}",
            )

        # Mapping key download
        st.divider()
        st.subheader("Mapping Key")
        st.write(
            "The mapping key lets you reverse the anonymisation. "
            "Keep it secure — it links pseudonyms back to originals."
        )

        registry = st.session_state.registry
        if len(registry) > 0:
            import pandas as pd
            mapping_df = pd.DataFrame(registry.mapping_table)
            st.dataframe(mapping_df, use_container_width=True)

            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.download_button(
                    label="Download Mapping (CSV)",
                    data=registry.to_csv_bytes(),
                    file_name="anonymisation_mapping.csv",
                    mime="text/csv",
                    key="dl_mapping_csv",
                )
            with col_m2:
                st.download_button(
                    label="Download Mapping (JSON)",
                    data=registry.to_json_bytes(),
                    file_name="anonymisation_mapping.json",
                    mime="application/json",
                    key="dl_mapping_json",
                )
        else:
            st.info("No entities were anonymised.")

elif not uploaded_files:
    st.info("Upload one or more files in the sidebar to get started.")
