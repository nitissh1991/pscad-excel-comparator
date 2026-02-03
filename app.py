
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

st.set_page_config(page_title="Two-Excel Overlay Plotter", layout="wide")
st.title("Two-Excel Overlay Plotter (GitHub Deployable)")

@st.cache_data(show_spinner=False)
def load_excel(file):
    return pd.read_excel(file, engine="openpyxl")

def common_columns(df1, df2):
    return sorted(set(df1.columns).intersection(df2.columns))

def plot_overlay(df1, df2, x_col, y_cols, label1, label2):
    n = len(y_cols)
    ncols = 2 if n > 1 else 1
    nrows = (n + ncols - 1) // ncols

    fig, axes = plt.subplots(nrows, ncols, figsize=(14, 4 * nrows), dpi=120)
    axes = axes.flatten() if n > 1 else [axes]

    for i, y in enumerate(y_cols):
        ax = axes[i]
        ax.plot(df1[x_col], df1[y], label=label1, linewidth=1.5)
        ax.plot(df2[x_col], df2[y], label=label2, linestyle="--", linewidth=1.5)
        ax.set_title(y)
        ax.set_xlabel(x_col)
        ax.set_ylabel("p.u.")
        ax.grid(True)
        ax.legend()

    for j in range(i + 1, len(axes)):
        axes[j].axis("off")

    st.pyplot(fig)

col1, col2 = st.columns(2)

with col1:
    f1 = st.file_uploader("Upload File-1 (Actual)", type=["xlsx"])
    label1 = st.text_input("Label File-1", "Actual")

with col2:
    f2 = st.file_uploader("Upload File-2 (PSCAD)", type=["xlsx"])
    label2 = st.text_input("Label File-2", "PSCAD")

if f1 and f2:
    df1 = load_excel(f1)
    df2 = load_excel(f2)

    common = common_columns(df1, df2)
    time_cols = [c for c in common if c.lower().endswith("_time")]
    x_col = st.selectbox("Select Time Column", time_cols)

    y_cols = st.multiselect(
        "Select Y Columns",
        [c for c in common if c != x_col and not c.lower().endswith("_time")]
    )

    if y_cols:
        plot_overlay(df1, df2, x_col, y_cols, label1, label2)
