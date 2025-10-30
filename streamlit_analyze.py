import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats

# ========== 页面配置 ==========
st.set_page_config(
    page_title="Query评分与字数关系分析",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ========== CSS 样式 ==========
CSS = """
<style>
    /* ========== 设计变量 ========== */
    :root {
        --primary-gradient: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%);
        --primary-color: #6366F1;
        --bg-gradient: linear-gradient(160deg, #4f46e5 0%, #8b5cf6 50%, #ec4899 120%);
        --text-primary: #1f2937;
        --text-secondary: #4b5563;
        --text-tertiary: #9ca3af;
        --bg-white: #ffffff;
        --border-color: #e5e7eb;
        --shadow-md: 0 10px 30px rgba(15, 23, 42, 0.08);
        --shadow-hover: 0 15px 40px rgba(15, 23, 42, 0.15);
        --radius-lg: 16px;
        --radius-md: 12px;
    }

    /* ========== 全局样式 ========== */
    .stApp {
        background: var(--bg-gradient);
    }
    
    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(255, 255, 255, 0.7);
        pointer-events: none;
        z-index: 0;
    }
    
    .main > div {
        position: relative;
        z-index: 1;
    }
    
    /* 隐藏 Streamlit 默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* ========== 自定义卡片样式 ========== */
    .custom-card {
        background: var(--bg-white);
        border-radius: var(--radius-lg);
        padding: 32px;
        box-shadow: var(--shadow-md);
        margin-bottom: 24px;
        transition: all 0.3s ease;
    }
    
    .custom-card:hover {
        box-shadow: var(--shadow-hover);
        transform: translateY(-2px);
    }
    
    /* ========== Header 样式 ========== */
    .header-card {
        background: var(--bg-white);
        border-radius: var(--radius-lg);
        padding: 40px;
        box-shadow: var(--shadow-md);
        margin-bottom: 24px;
        animation: slideDown 0.5s ease-out;
    }
    
    .header-title {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 12px;
    }
    
    .header-icon {
        font-size: 36px;
        line-height: 1;
    }
    
    .header-title h1 {
        color: var(--text-primary);
        font-size: 32px;
        font-weight: 700;
        margin: 0;
    }
    
    .header-subtitle {
        color: var(--text-tertiary);
        font-size: 15px;
        line-height: 1.6;
        margin-top: 8px;
    }
    
    /* ========== 上传区样式 ========== */
    .upload-card {
        background: var(--bg-white);
        border-radius: var(--radius-lg);
        padding: 32px;
        box-shadow: var(--shadow-md);
        margin-bottom: 24px;
        animation: slideUp 0.5s ease-out 0.1s backwards;
    }
    
    .upload-card-title {
        color: var(--text-primary);
        font-size: 18px;
        font-weight: 600;
        margin-bottom: 8px;
    }
    
    .upload-card-desc {
        color: var(--text-tertiary);
        font-size: 14px;
        line-height: 1.5;
        margin-bottom: 20px;
    }
    
    /* Streamlit 文件上传器样式优化 */
    .stFileUploader > div > div {
        background: var(--primary-gradient);
        border-radius: 9999px;
        padding: 12px 28px;
        border: none;
    }
    
    .stFileUploader label {
        color: white !important;
        font-weight: 600 !important;
        font-size: 15px !important;
    }
    
    /* ========== 统计卡片样式 ========== */
    .stat-card {
        background: var(--bg-white);
        border-radius: var(--radius-lg);
        padding: 24px;
        box-shadow: var(--shadow-md);
        transition: all 0.3s ease;
    }
    
    .stat-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-hover);
    }
    
    .stat-card-title {
        color: var(--text-primary);
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .stat-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 0;
        border-bottom: 1px solid var(--border-color);
    }
    
    .stat-item:last-child {
        border-bottom: none;
    }
    
    .stat-label {
        color: var(--text-secondary);
        font-size: 14px;
    }
    
    .stat-value {
        color: var(--text-primary);
        font-weight: 600;
        font-size: 14px;
    }
    
    /* ========== 图表卡片样式 ========== */
    .chart-card {
        background: var(--bg-white);
        border-radius: var(--radius-lg);
        padding: 32px;
        margin-bottom: 32px;
        box-shadow: var(--shadow-md);
        transition: all 0.3s ease;
    }
    
    .chart-card:hover {
        box-shadow: var(--shadow-hover);
    }
    
    .chart-card-title {
        color: var(--text-primary);
        font-size: 20px;
        font-weight: 600;
        margin-bottom: 8px;
    }
    
    .chart-card-desc {
        color: var(--text-tertiary);
        font-size: 13px;
        line-height: 1.5;
        margin-bottom: 24px;
    }
    
    /* ========== 洞察卡片样式 ========== */
    .insight {
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
        border-left: 3px solid var(--primary-color);
        padding: 16px 20px;
        border-radius: var(--radius-md);
        margin-top: 16px;
    }
    
    .insight-title {
        color: var(--primary-color);
        font-weight: 600;
        font-size: 14px;
        margin-bottom: 8px;
    }
    
    .insight-text {
        color: var(--text-secondary);
        line-height: 1.6;
        font-size: 14px;
    }
    
    /* ========== 空状态样式 ========== */
    .empty-state {
        text-align: center;
        padding: 80px 32px;
        background: var(--bg-white);
        border-radius: var(--radius-lg);
        box-shadow: var(--shadow-md);
    }
    
    .empty-state-icon {
        font-size: 64px;
        margin-bottom: 16px;
        opacity: 0.5;
    }
    
    .empty-state-text {
        color: var(--text-tertiary);
        font-size: 15px;
        line-height: 1.6;
    }
    
    /* ========== 动画 ========== */
    @keyframes slideDown {
        from {
            opacity: 0;
            transform: translateY(-20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes slideUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* ========== 响应式 ========== */
    @media (max-width: 768px) {
        .header-card, .upload-card, .chart-card {
            padding: 20px;
        }
        
        .header-title h1 {
            font-size: 24px;
        }
        
        .header-icon {
            font-size: 28px;
        }
    }
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

# ========== 辅助函数 ==========
def parse_win_rate(win_rate_str):
    """解析胜率字符串，提取百分比数值"""
    if pd.isna(win_rate_str):
        return None
    import re
    match = re.search(r'(\d+\.?\d*)%', str(win_rate_str))
    return float(match.group(1)) if match else None

def convert_to_tidy_format(char_count_df, win_rate_df):
    """将宽格式数据转换为长格式（tidy format）"""
    data_list = []
    
    # 获取模型列（第一列是query编号，从第二列开始是模型）
    models = char_count_df.columns[1:]
    
    for idx in range(len(char_count_df)):
        query_id = char_count_df.iloc[idx, 0]
        
        for model in models:
            word_count = char_count_df.loc[idx, model] if model in char_count_df.columns else None
            win_rate_str = win_rate_df.loc[idx, model] if idx < len(win_rate_df) and model in win_rate_df.columns else None
            
            # 只添加有数据的记录
            if pd.notna(word_count) or pd.notna(win_rate_str):
                rating = parse_win_rate(win_rate_str)
                
                data_list.append({
                    'query': query_id,
                    'model': model,
                    'word_count': int(word_count) if pd.notna(word_count) else None,
                    'rating': rating
                })
    
    return pd.DataFrame(data_list)

def display_stats_cards(df):
    """展示统计卡片"""
    valid_df = df.dropna(subset=['word_count', 'rating'])
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-title">📝 字数统计</div>
            <div class="stat-item">
                <span class="stat-label">均值</span>
                <span class="stat-value">{valid_df['word_count'].mean():.2f}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">中位数</span>
                <span class="stat-value">{valid_df['word_count'].median():.2f}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">标准差</span>
                <span class="stat-value">{valid_df['word_count'].std():.2f}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">最小值</span>
                <span class="stat-value">{valid_df['word_count'].min():.0f}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">最大值</span>
                <span class="stat-value">{valid_df['word_count'].max():.0f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-title">🎯 胜率统计</div>
            <div class="stat-item">
                <span class="stat-label">均值</span>
                <span class="stat-value">{valid_df['rating'].mean():.2f}%</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">中位数</span>
                <span class="stat-value">{valid_df['rating'].median():.2f}%</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">标准差</span>
                <span class="stat-value">{valid_df['rating'].std():.2f}%</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">最小值</span>
                <span class="stat-value">{valid_df['rating'].min():.2f}%</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">最大值</span>
                <span class="stat-value">{valid_df['rating'].max():.2f}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-title">📊 数据概览</div>
            <div class="stat-item">
                <span class="stat-label">总样本数</span>
                <span class="stat-value">{len(valid_df)}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">模型数量</span>
                <span class="stat-value">{valid_df['model'].nunique()}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Query数量</span>
                <span class="stat-value">{valid_df['query'].nunique()}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">数据完整率</span>
                <span class="stat-value">{len(valid_df)/len(df)*100:.1f}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

def create_scatter_plot(df):
    """创建散点图 + 回归线（按模型区分颜色）"""
    valid_df = df.dropna(subset=['word_count', 'rating'])
    
    # 计算皮尔逊相关系数（线性相关）
    pearson_corr = valid_df['word_count'].corr(valid_df['rating'], method='pearson')
    
    # 计算斯皮尔曼相关系数（单调相关）
    spearman_corr = valid_df['word_count'].corr(valid_df['rating'], method='spearman')
    
    # 线性回归
    slope, intercept, r_value, p_value, std_err = stats.linregress(
        valid_df['word_count'], 
        valid_df['rating']
    )
    
    # 创建散点图 - 按模型区分颜色
    fig = px.scatter(
        valid_df,
        x='word_count',
        y='rating',
        color='model',  # 按模型区分颜色
        hover_data=['query'],
        labels={'word_count': '字数', 'rating': '胜率 (%)', 'model': '模型'},
        color_discrete_sequence=px.colors.qualitative.Set2  # 使用柔和的配色
    )
    
    # 添加回归线
    x_range = np.array([valid_df['word_count'].min(), valid_df['word_count'].max()])
    y_range = slope * x_range + intercept
    
    fig.add_trace(
        go.Scatter(
            x=x_range,
            y=y_range,
            mode='lines',
            name='回归线',
            line=dict(color='#ef4444', width=3, dash='dash'),
            showlegend=True
        )
    )
    
    fig.update_traces(
        marker=dict(
            size=10,
            line=dict(width=1, color='white')  # 给点加白色边框
        ),
        selector=dict(mode='markers')
    )
    
    fig.update_layout(
        plot_bgcolor='#fafafa',
        paper_bgcolor='white',
        font=dict(family='-apple-system, BlinkMacSystemFont, "Segoe UI"'),
        height=450,
        margin=dict(t=10, b=10, l=10, r=10),
        legend=dict(
            title=dict(text='模型', font=dict(weight='bold')),
            orientation='v',
            yanchor='top',
            y=1,
            xanchor='left',
            x=1.02,
            bgcolor='rgba(255, 255, 255, 0.9)',
            bordercolor='#e5e7eb',
            borderwidth=1
        )
    )
    
    return fig, pearson_corr, spearman_corr

def create_box_plot(df):
    """创建箱线图（按字数区间分组）"""
    valid_df = df.dropna(subset=['word_count', 'rating']).copy()
    
    # 将字数分为5档
    valid_df['word_count_bin'] = pd.cut(valid_df['word_count'], bins=5)
    valid_df['word_count_bin_label'] = valid_df['word_count_bin'].astype(str)
    
    fig = px.box(
        valid_df,
        x='word_count_bin_label',
        y='rating',
        labels={'word_count_bin_label': '字数区间', 'rating': '胜率 (%)'},
        color='word_count_bin_label',
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    
    fig.update_layout(
        plot_bgcolor='#fafafa',
        paper_bgcolor='white',
        font=dict(family='-apple-system, BlinkMacSystemFont, "Segoe UI"'),
        height=450,
        showlegend=False,
        margin=dict(t=10, b=10, l=10, r=10)
    )
    
    return fig

def create_heatmap(df):
    """创建相关性热力图"""
    valid_df = df.dropna(subset=['word_count', 'rating'])
    
    # 计算相关性矩阵
    corr_matrix = valid_df[['word_count', 'rating']].corr()
    
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=['字数', '胜率'],
        y=['字数', '胜率'],
        colorscale='RdBu',
        zmid=0,
        text=corr_matrix.values.round(3),
        texttemplate='%{text}',
        textfont={"size": 18}
    ))
    
    fig.update_layout(
        paper_bgcolor='white',
        font=dict(family='-apple-system, BlinkMacSystemFont, "Segoe UI"'),
        height=400,
        margin=dict(t=10, b=10, l=10, r=10)
    )
    
    return fig

def create_model_comparison(df):
    """创建模型对比图"""
    valid_df = df.dropna(subset=['word_count', 'rating'])
    
    # 按模型分组统计
    model_stats = valid_df.groupby('model').agg({
        'word_count': 'mean',
        'rating': 'mean'
    }).reset_index()
    
    # 创建双Y轴图表
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(
        go.Bar(
            x=model_stats['model'],
            y=model_stats['word_count'],
            name='平均字数',
            marker_color='#6366f1'
        ),
        secondary_y=False
    )
    
    fig.add_trace(
        go.Bar(
            x=model_stats['model'],
            y=model_stats['rating'],
            name='平均胜率',
            marker_color='#ec4899'
        ),
        secondary_y=True
    )
    
    fig.update_xaxes(title_text="模型")
    fig.update_yaxes(title_text="平均字数", secondary_y=False)
    fig.update_yaxes(title_text="平均胜率 (%)", secondary_y=True)
    
    fig.update_layout(
        plot_bgcolor='#fafafa',
        paper_bgcolor='white',
        font=dict(family='-apple-system, BlinkMacSystemFont, "Segoe UI"'),
        height=450,
        barmode='group',
        margin=dict(t=10, b=10, l=10, r=10)
    )
    
    # 找出最佳模型
    best_model = model_stats.loc[model_stats['rating'].idxmax(), 'model']
    best_rating = model_stats['rating'].max()
    most_verbose = model_stats.loc[model_stats['word_count'].idxmax(), 'model']
    max_words = model_stats['word_count'].max()
    
    return fig, best_model, best_rating, most_verbose, max_words

# ========== 主应用 ==========
def main():
    # Header
    st.markdown("""
    <div class="header-card">
        <div class="header-title">
            <span class="header-icon">📊</span>
            <h1>Query评分与字数关系分析</h1>
        </div>
        <p class="header-subtitle">
            上传包含"字数统计"和"胜率"两个sheet的Excel文件，系统将自动进行数据分析和可视化展示
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # 上传区
    st.markdown("""
    <div class="upload-card">
        <div class="upload-card-title">上传数据文件</div>
        <p class="upload-card-desc">请上传 Excel 文件，支持 .xlsx 和 .xls 格式</p>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "选择文件",
        type=['xlsx', 'xls'],
        label_visibility='collapsed'
    )
    
    if uploaded_file is None:
        # 空状态
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">📈</div>
            <p class="empty-state-text">请先上传数据文件，系统将为您生成详细的分析报告</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    try:
        # 读取Excel文件
        excel_file = pd.ExcelFile(uploaded_file)
        
        # 检查必需的sheet
        if '字数统计' not in excel_file.sheet_names or '胜率' not in excel_file.sheet_names:
            st.error("❌ Excel文件必须包含"字数统计"和"胜率"两个sheet")
            return
        
        # 读取数据
        char_count_df = pd.read_excel(excel_file, sheet_name='字数统计')
        win_rate_df = pd.read_excel(excel_file, sheet_name='胜率')
        
        # 转换为长格式
        with st.spinner('正在处理数据...'):
            tidy_df = convert_to_tidy_format(char_count_df, win_rate_df)
        
        # 显示统计卡片
        st.markdown("<br>", unsafe_allow_html=True)
        display_stats_cards(tidy_df)
        
        # 散点图
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div class="chart-card-title">📈 字数与胜率关系分析</div>
        <div class="chart-card-desc">通过散点图和回归线展示两个变量之间的相关性</div>
        """, unsafe_allow_html=True)
        
        fig_scatter, pearson_corr, spearman_corr = create_scatter_plot(tidy_df)
        st.plotly_chart(fig_scatter, use_container_width=True)
        
        # 相关性洞察 - 对比两种系数
        pearson_strength = '强' if abs(pearson_corr) > 0.7 else ('中等' if abs(pearson_corr) > 0.4 else '弱')
        spearman_strength = '强' if abs(spearman_corr) > 0.7 else ('中等' if abs(spearman_corr) > 0.4 else '弱')
        corr_direction = '正' if pearson_corr > 0 else '负'
        
        # 判断关系类型
        diff = abs(spearman_corr - pearson_corr)
        if diff < 0.1:
            relationship_type = "接近线性关系"
            relationship_desc = "两个系数非常接近，说明字数与胜率之间的关系接近线性。"
        elif spearman_corr > pearson_corr + 0.1:
            relationship_type = "非线性单调关系"
            relationship_desc = "斯皮尔曼系数明显高于皮尔逊系数，说明存在非线性但单调的关系（如对数、指数关系）。"
        else:
            relationship_type = "复杂非线性关系"
            relationship_desc = "两个系数差异较大，说明关系较为复杂，可能存在非单调或分段的模式。"
        
        corr_interpretation = (
            '这表明字数越多，胜率往往越高。' if pearson_corr > 0.3 else
            '这表明字数越多，胜率反而越低。' if pearson_corr < -0.3 else
            '字数与胜率之间的关系不明显。'
        )
        
        st.markdown(f"""
        <div class="insight">
            <div class="insight-title">📊 双重相关性分析</div>
            <div class="insight-text">
                <p style="margin-bottom: 12px;">
                    <strong>皮尔逊相关系数 (Pearson)：</strong>{pearson_corr:.3f} 
                    <span style="color: #6b7280;">（衡量线性相关性）</span><br>
                    存在<strong>{pearson_strength}</strong>{corr_direction}相关关系。
                </p>
                <p style="margin-bottom: 12px;">
                    <strong>斯皮尔曼相关系数 (Spearman)：</strong>{spearman_corr:.3f}
                    <span style="color: #6b7280;">（衡量单调相关性）</span><br>
                    存在<strong>{spearman_strength}</strong>{corr_direction}相关关系。
                </p>
                <p style="margin-bottom: 12px;">
                    <strong>关系类型判断：</strong>{relationship_type}<br>
                    <span style="color: #6b7280;">{relationship_desc}</span>
                </p>
                <p>
                    <strong>结论：</strong>{corr_interpretation}
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 箱线图
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div class="chart-card-title">📦 按字数区间的胜率分布</div>
        <div class="chart-card-desc">将字数分为5个区间，展示每个区间的胜率分布情况</div>
        """, unsafe_allow_html=True)
        
        fig_box = create_box_plot(tidy_df)
        st.plotly_chart(fig_box, use_container_width=True)
        
        st.markdown("""
        <div class="insight">
            <div class="insight-title">📦 分布分析</div>
            <div class="insight-text">
                箱线图展示了不同字数区间的胜率分布情况。箱体表示四分位距（IQR），中间的线表示中位数。
                可以观察到不同字数区间的胜率中位数和离散程度。
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 热力图
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div class="chart-card-title">🔥 变量相关性热力图</div>
        <div class="chart-card-desc">通过颜色深浅展示变量之间的相关性强度</div>
        """, unsafe_allow_html=True)
        
        fig_heatmap = create_heatmap(tidy_df)
        st.plotly_chart(fig_heatmap, use_container_width=True)
        
        st.markdown("""
        <div class="insight">
            <div class="insight-title">🔥 相关性矩阵</div>
            <div class="insight-text">
                热力图显示了变量之间的相关性强度。颜色越红表示正相关越强，越蓝表示负相关越强。
                对角线为1表示变量与自身完全相关。
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 模型对比
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div class="chart-card-title">🏆 不同模型的平均表现对比</div>
        <div class="chart-card-desc">对比各模型的平均字数和平均胜率</div>
        """, unsafe_allow_html=True)
        
        fig_comparison, best_model, best_rating, most_verbose, max_words = create_model_comparison(tidy_df)
        st.plotly_chart(fig_comparison, use_container_width=True)
        
        st.markdown(f"""
        <div class="insight">
            <div class="insight-title">🏆 模型表现</div>
            <div class="insight-text">
                <strong>{best_model}</strong> 的平均胜率最高（{best_rating:.2f}%），
                <strong>{most_verbose}</strong> 的平均字数最多（{max_words:.0f}字）。
                {'最佳模型同时也是最详细的模型。' if best_model == most_verbose else ''}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"❌ 处理文件时出错：{str(e)}")
        st.exception(e)

if __name__ == "__main__":
    main()

