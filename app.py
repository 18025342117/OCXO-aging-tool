import streamlit as st
import pandas as pd
import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

# 预定义对数老化模型
def log_aging_model(t, A, B, C):
    return A * np.log(B * t + 1) + C

# 页面配置 (纯英文)
st.set_page_config(page_title="OCXO Aging Analysis", layout="wide")
st.title("📈 OCXO Frequency Aging Dual-Track Analysis")
st.markdown("Based on GJB 1648A-2011 Standard | Weighted Least Squares (WLS)")

# 文件上传
uploaded_files = st.file_uploader("Upload 1 or 2 Excel files for analysis or comparison", 
                                  type=["xlsx", "xls"], 
                                  accept_multiple_files=True)

if uploaded_files:
    if len(uploaded_files) > 2:
        st.warning("To ensure optimal visualization, only the first 2 files are processed.")
        uploaded_files = uploaded_files[:2]

    # ================= 动态数据处理设置面板 =================
    st.markdown("#### ⚙️ Data Preprocessing Options")
    setting_cols = st.columns(len(uploaded_files))
    
    do_truncate = {}
    for idx, file in enumerate(uploaded_files):
        with setting_cols[idx]:
            # 动态生成每个文件的剔除勾选项
            do_truncate[file.name] = st.checkbox(f"Exclude first 48h warm-up for [{file.name}]", 
                                                 value=True, 
                                                 key=f"chk_{idx}")
    st.markdown("---")
    # =======================================================

    fig, ax = plt.subplots(figsize=(12, 6))
    
    color_raw = ['#1f77b4', '#2ca02c']  
    color_fit = ['#d62728', '#ff7f0e']
    analysis_results = []

    for idx, file in enumerate(uploaded_files):
        try:
            df = pd.read_excel(file, header=None)
            t_days = pd.to_numeric(df.iloc[:, 0], errors='coerce').dropna().values
            y_freq = pd.to_numeric(df.iloc[:, 1], errors='coerce').dropna().values
            
            min_len = min(len(t_days), len(y_freq))
            t_days, y_freq = t_days[:min_len], y_freq
