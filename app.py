import io
from typing import List, Tuple

import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

st.set_page_config(page_title="Two-File Overlay Plotter", layout="wide")
st.title("Two-File Overlay Plotter (Excel + CSV, GitHub Deployable)")

st.markdown(
    """
Upload **two files** (Excel or CSV), then select **X (time)** and **Y** columns for each file.
Plots are overlaid (File-1 solid, File-2 dashed), similar to PSCAD comparison plots.
"""
)

# -----------------------------
# Loading
# -----------------------------
@st.cache_data(show_spinner=False)
def load_table(uploaded_file) -> pd.DataFrame:
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        # Try common encodings gracefully
        try:
            return pd.read_csv(uploaded_file)
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, encoding="latin1")
    elif name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(uploaded_file, sheet_name=0, engine="openpyxl")
    else:
        raise ValueError("Unsupported file type. Please upload .csv, .xlsx, or .xls")


def to_numeric_series(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(df[col], errors="coerce")


def aligned_xy(df: pd.DataFrame, x_col: str, y_col: str) -> Tuple[pd.Series, pd.Series]:
    x = to_numeric_series(df, x_col)
    y = to_numeric_series(df, y_col)
    tmp = pd.DataFrame({"x": x, "y": y}).dropna()
    return tmp["x"], tmp["y"]


def suggest_time_cols(cols: List[str]) -> List[str]:
    return [c for c in cols if str(c).lower().endswith("_time")]


def fig_to_png_bytes(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    return buf.read()


# -----------------------------
# UI: uploads
# -----------------------------
col1, col2 = st.columns(2)

with col1:
    f1 = st.file_uploader("Upload File-1", type=["xlsx", "xls", "csv"], key="f1")
    label1 = st.text_input("Legend label for File-1", value="File-1")

with col2:
    f2 = st.file_uploader("Upload File-2", type=["xlsx", "xls", "csv"], key="f2")
    label2 = st.text_input("Legend label for File-2", value="File-2")

if not f1 or not f2:
    st.info("Upload both files to continue.")
    st.stop()

df1 = load_table(f1)
df2 = load_table(f2)

cols1 = list(df1.columns.astype(str))
cols2 = list(df2.columns.astype(str))

# -----------------------------
# Selection mode
# -----------------------------
st.subheader("Column selection")

same_names = st.checkbox(
    "Column names are same in both files (use common columns selector)",
    value=True,
    help="If your two files have different column names, uncheck this to select X/Y separately for each file.",
)

if same_names:
    common = sorted(set(cols1).intersection(cols2))

    if not common:
        st.error("No common columns found between the two files. Uncheck the checkbox and select columns separately.")
        st.stop()

    time_common = suggest_time_cols(common)
    default_x = "P_zero_pu_time" if "P_zero_pu_time" in time_common else (time_common[0] if time_common else common[0])

    x_col = st.selectbox(
        "X-axis (time) column (common to both files)",
        options=time_common if time_common else common,
        index=(time_common.index(default_x) if default_x in time_common else 0),
    )

    y_candidates = [c for c in common if c != x_col]
    y_cols = st.multiselect("Y-axis column(s) (common to both files)", options=y_candidates)

    pairs = [(y, y, y) for y in y_cols]  # (y1, y2, title)
    x1 = x_col
    x2 = x_col

else:
    # Separate selectors for each file
    cA, cB = st.columns(2)

    with cA:
        st.markdown("**File-1 columns**")
        time1 = suggest_time_cols(cols1)
        default_x1 = "P_zero_pu_time" if "P_zero_pu_time" in time1 else (time1[0] if time1 else cols1[0])
        x1 = st.selectbox("X-axis for File-1", options=time1 if time1 else cols1, index=(time1.index(default_x1) if default_x1 in time1 else 0))
    with cB:
        st.markdown("**File-2 columns**")
        time2 = suggest_time_cols(cols2)
        default_x2 = "P_zero_pu_time" if "P_zero_pu_time" in time2 else (time2[0] if time2 else cols2[0])
        x2 = st.selectbox("X-axis for File-2", options=time2 if time2 else cols2, index=(time2.index(default_x2) if default_x2 in time2 else 0))

    st.markdown("### Create Y-column pairs (File-1 vs File-2)")
    nplots = st.number_input("How many plots/subplots?", min_value=1, max_value=16, value=6, step=1)

    pairs = []
    for i in range(int(nplots)):
        r1, r2, r3 = st.columns([4, 4, 3])
        with r1:
            y1 = st.selectbox(f"Plot {i+1}: Y from File-1", options=[c for c in cols1 if c != x1], key=f"y1_{i}")
        with r2:
            y2 = st.selectbox(f"Plot {i+1}: Y from File-2", options=[c for c in cols2 if c != x2], key=f"y2_{i}")
        with r3:
            title = st.text_input(f"Title {i+1} (optional)", value=y1, key=f"title_{i}")
        pairs.append((y1, y2, title))

# -----------------------------
# Plotting
# -----------------------------
st.subheader("Plot")

if not pairs:
    st.warning("Select at least one Y column (or create at least one Y-pair).")
    st.stop()

# Decide layout: 2 columns like PSCAD multi-panel
n = len(pairs)
ncols = 2 if n > 1 else 1
nrows = (n + ncols - 1) // ncols

fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(14, 3.8 * nrows), dpi=120)
if nrows == 1 and ncols == 1:
    axes = [axes]
else:
    axes = axes.flatten()

for i, (y1, y2, title) in enumerate(pairs):
    ax = axes[i]

    x_1, y_1 = aligned_xy(df1, x1, y1)
    x_2, y_2 = aligned_xy(df2, x2, y2)

    ax.plot(x_1, y_1, label=label1, linewidth=1.4)
    ax.plot(x_2, y_2, label=label2, linewidth=1.4, linestyle="--")

    ax.set_title(title if title else f"{y1} vs {y2}")
    ax.set_xlabel(x1 if same_names else f"{x1} / {x2}")
    ax.set_ylabel("Value")
    ax.grid(True, which="both", linestyle=":", linewidth=0.8)
    ax.legend()

# Hide unused panels
for j in range(i + 1, len(axes)):
    axes[j].axis("off")

fig.tight_layout()
st.pyplot(fig)

st.download_button(
    "Download figure (PNG)",
    data=fig_to_png_bytes(fig),
    file_name="overlay_comparison.png",
    mime="image/png",
)

with st.expander("Preview first 5 rows"):
    st.write("File-1 head:")
    st.dataframe(df1.head())
    st.write("File-2 head:")
    st.dataframe(df2.head())