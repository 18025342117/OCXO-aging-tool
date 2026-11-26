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
            t_days, y_freq = t_days[:min_len], y_freq[:min_len]

            # 根据复选框状态决定是否切除
            if do_truncate[file.name]:
                t_zero = t_days[0]
                valid_mask = t_days >= (t_zero + 2.0) 
                t_days = t_days[valid_mask]
                y_freq = y_freq[valid_mask]
                status_text = "(48h Excluded)"
            else:
                status_text = "(Raw Uncut)"
                
            if len(t_days) == 0:
                st.error(f"Error: [{file.name}] total duration is less than 48 hours. Please uncheck exclusion.")
                continue

            # 强制绝对时间归零
            t_days = t_days - t_days[0] 

            # WLS 拟合
            weights = t_days + 1.0
            popt, _ = curve_fit(log_aging_model, t_days, y_freq, 
                                p0=[1e-9, 1.0, 1e-8], 
                                bounds=([-np.inf, 1e-10, -np.inf], [np.inf, np.inf, np.inf]),
                                sigma=1.0/weights)
            A, B, C = popt
            
            T1 = np.max(t_days)
            tangent_slope = (A * B) / (B * T1 + 1)
            aging_T1 = A * np.log(B * T1 + 1)
            month_hybrid = aging_T1 + tangent_slope * (30 - T1)
            year_aging = aging_T1 + tangent_slope * (365 - T1)

            analysis_results.append({
                "name": file.name,
                "T1": T1,
                "daily": tangent_slope,
                "monthly": month_hybrid,
                "yearly": year_aging,
                "status": status_text
            })

            # 纯英文图例绘制
            ax.scatter(t_days, y_freq, s=3, alpha=0.4, color=color_raw[idx], label=f"{file.name} (Raw Data)")
            t_smooth = np.linspace(0, max(T1, 30), 1000)
            ax.plot(t_smooth, log_aging_model(t_smooth, A, B, C), color=color_fit[idx], linewidth=2, label=f"{file.name} (WLS Fit)")

        except Exception as e:
            st.error(f"Error processing {file.name}: {str(e)}")

    # 纯英文图表属性
    ax.set_xlabel("Time (Days)", fontsize=12)
    ax.set_ylabel("Relative Frequency Deviation (df/f)", fontsize=12)
    ax.set_title("OCXO Frequency Aging Trend Comparison", fontsize=14, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend(loc='upper left', fontsize=10)
    
    st.pyplot(fig)

    st.markdown("---")

    # 纯英文数据仪表盘
    cols = st.columns(len(analysis_results))
    
    for idx, res in enumerate(analysis_results):
        with cols[idx]:
            st.markdown(f"### <span style='color:{color_fit[idx]}'>■</span> {res['name']}", unsafe_allow_html=True)
            st.caption(f"Valid Duration: {res['T1']:.1f} Days {res['status']}")
            st.metric("Daily Aging (End Tangent)", f"{res['daily']:.2e}")
            st.metric("Monthly Aging (30 Days)", f"{res['monthly']:.2e}")
            st.metric("Yearly Aging (365 Days)", f"{res['yearly']:.2e}")
