import streamlit as st
import pandas as pd
import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

def log_aging_model(t, A, B, C):
    return A * np.log(B * t + 1) + C

st.title("📈 OCXO 频率老化分析系统")
st.markdown("基于 GJB 1648A-2011 标准 | 采用时间加权最小二乘法 (WLS)")

uploaded_file = st.file_uploader("请上传有效数据的 Excel 文件", type=["xlsx", "xls"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file, header=None)
    t_days = pd.to_numeric(df.iloc[:, 0], errors='coerce').dropna().values
    y_freq = pd.to_numeric(df.iloc[:, 1], errors='coerce').dropna().values
    min_len = min(len(t_days), len(y_freq))
    t_days, y_freq = t_days[:min_len], y_freq[:min_len]

    popt, _ = curve_fit(log_aging_model, t_days, y_freq, p0=[1e-9, 1.0, 1e-8], 
                        bounds=([-np.inf, 1e-10, -np.inf], [np.inf, np.inf, np.inf]),
                        sigma=1.0/(t_days + 1.0))
    A, B, C = popt
    T1 = np.max(t_days)
    tangent_slope = (A * B) / (B * T1 + 1)
    aging_T1 = A * np.log(B * T1 + 1)

    # 网页中的数据仪表盘组件
    col1, col2, col3 = st.columns(3)
    col1.metric("当前日老化", f"{tangent_slope:.2e}")
    col2.metric("混合月老化 (30天)", f"{aging_T1 + tangent_slope * (30 - T1):.2e}")
    col3.metric("预计年老化 (365天)", f"{aging_T1 + tangent_slope * (365 - T1):.2e}")

    # 绘制并展示到网页
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.scatter(t_days, y_freq, s=2, alpha=0.5, label="Raw Data")
    t_smooth = np.linspace(0, T1, 500)
    ax.plot(t_smooth, log_aging_model(t_smooth, A, B, C), color='red', label="WLS Fit")
    ax.legend()
    st.pyplot(fig)
