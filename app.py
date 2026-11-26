import streamlit as st
import pandas as pd
import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

# 预定义对数老化模型
def log_aging_model(t, A, B, C):
    return A * np.log(B * t + 1) + C

# 页面配置与标题
st.set_page_config(page_title="OCXO 老化对比系统", layout="wide")
st.title("📈 OCXO 频率老化双轨对比系统")
st.markdown("基于 GJB 1648A-2011 标准 | 采用时间加权最小二乘法 (WLS)")

# 1. 开启多文件上传 (accept_multiple_files=True)
uploaded_files = st.file_uploader("请上传 1 到 2 个 Excel 文件进行单独或对比分析", 
                                  type=["xlsx", "xls"], 
                                  accept_multiple_files=True)

if uploaded_files:
    # 限制最多处理 2 个文件以保证视觉效果
    if len(uploaded_files) > 2:
        st.warning("为保证对比效果，最多支持同时分析 2 个文件，已自动截取前 2 个。")
        uploaded_files = uploaded_files[:2]

    # 初始化图表
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # 预设两组极具区分度的颜色库 (蓝/红配 vs 绿/橙配)
    color_raw = ['#1f77b4', '#2ca02c']  
    color_fit = ['#d62728', '#ff7f0e']
    
    # 用于存储计算结果，方便后续排版
    analysis_results = []

    for idx, file in enumerate(uploaded_files):
            try:
            # 读取数据
            df = pd.read_excel(file, header=None)
            t_days = pd.to_numeric(df.iloc[:, 0], errors='coerce').dropna().values
            y_freq = pd.to_numeric(df.iloc[:, 1], errors='coerce').dropna().values
            
            min_len = min(len(t_days), len(y_freq))
            t_days, y_freq = t_days[:min_len], y_freq[:min_len]

            # === 新增：自动剔除前 48 小时 (2天) 预热数据 ===
            t_zero = t_days[0] # 获取上电瞬间的初始时间戳
            valid_mask = t_days >= (t_zero + 2.0) # 筛选出大于等于2天的数据
            
            t_days = t_days[valid_mask]
            y_freq = y_freq[valid_mask]
            
            if len(t_days) == 0:
                st.error(f"文件 {file.name} 的总测试时长不足 48 小时，剔除后无有效数据！")
                continue # 跳过该文件，继续处理下一个

            # 将剩余有效数据的起点强制平移回 0 
            # (这是对数模型 f(t) = A*ln(B*t+1)+C 在数学上必须的要求)
            t_days = t_days - t_days[0] 
            # =========================================================

            # 时间加权最小二乘法拟合
            weights = t_days + 1.0
            popt, _ = curve_fit(log_aging_model, t_days, y_freq,
                                p0=[1e-9, 1.0, 1e-8], 
                                bounds=([-np.inf, 1e-10, -np.inf], [np.inf, np.inf, np.inf]),
                                sigma=1.0/weights)
            A, B, C = popt
            
            # 指标计算
            T1 = np.max(t_days)
            tangent_slope = (A * B) / (B * T1 + 1)
            aging_T1 = A * np.log(B * T1 + 1)
            month_hybrid = aging_T1 + tangent_slope * (30 - T1)
            year_aging = aging_T1 + tangent_slope * (365 - T1)

            # 保存结果
            analysis_results.append({
                "name": file.name,
                "T1": T1,
                "daily": tangent_slope,
                "monthly": month_hybrid,
                "yearly": year_aging
            })

           # 绘制当前文件的散点与曲线 (全英文标签)
            ax.scatter(t_days, y_freq, s=3, alpha=0.4, color=color_raw[idx], label=f"{file.name} (Raw Data)")
            t_smooth = np.linspace(0, max(T1, 30), 1000)
            ax.plot(t_smooth, log_aging_model(t_smooth, A, B, C), color=color_fit[idx], linewidth=2, label=f"{file.name} (WLS Fit)")

        except Exception as e:
            st.error(f"Error processing {file.name}: {str(e)}")

    # 图表细节修饰 (全英文)
    ax.set_xlabel("Time (Days)", fontsize=12)
    ax.set_ylabel("Relative Frequency Deviation (df/f)", fontsize=12)
    ax.set_title("OCXO Frequency Aging Trend Comparison", fontsize=14, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend(loc='upper left', fontsize=10)
    
    # 渲染图表
    st.pyplot(fig)

    st.markdown("---")

    # 2. 动态分列展示数据面板
    # 几个文件就切分几列
    cols = st.columns(len(analysis_results))
    
    for idx, res in enumerate(analysis_results):
        with cols[idx]:
            # 顶部增加一个小彩条，对应图表里的曲线颜色，方便识别
            st.markdown(f"### <span style='color:{color_fit[idx]}'>■</span> {res['name']}", unsafe_allow_html=True)
            st.caption(f"实测周期终点: 第 {res['T1']:.1f} 天")
            
            # 使用内建的 metric 卡片展示关键指标
            st.metric("终点瞬时日老化", f"{res['daily']:.2e}")
            st.metric("混合外推月老化 (30天)", f"{res['monthly']:.2e}")
            st.metric("预计年老化 (365天)", f"{res['yearly']:.2e}")
