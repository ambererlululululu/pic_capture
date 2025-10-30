import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
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

def find_sheet_name(excel_file: pd.ExcelFile, candidates):
    """在Excel文件中查找最匹配的sheet名，容错大小写/空格/全角半角等。
    返回实际sheet名或None。
    """
    import re
    all_sheets = excel_file.sheet_names
    norm = lambda s: re.sub(r"\s+", "", str(s)).strip().lower()
    normalized_map = {norm(name): name for name in all_sheets}
    for c in candidates:
        key = norm(c)
        if key in normalized_map:
            return normalized_map[key]
    # 近似匹配：包含关键词
    for c in candidates:
        ck = norm(c)
        for k, v in normalized_map.items():
            if ck in k or k in ck:
                return v
    return None

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
                
                # 安全转换字数为整数
                try:
                    word_count_val = int(float(word_count)) if pd.notna(word_count) else None
                except (ValueError, TypeError):
                    word_count_val = None  # 如果转换失败，设为None
                
                data_list.append({
                    'query': query_id,
                    'model': model,
                    'word_count': word_count_val,
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

    

# ========== 主应用 ==========
def main():
    # 顶部说明
    st.markdown("""
    <div class=\"header-card\">
        <div class=\"header-title\"><span class=\"header-icon\">📊</span><h1>评测数据分析</h1></div>
        <p class=\"header-subtitle\">支持两种模式：Excel（字数统计/胜率）与 CSV（评测对战记录）。</p>
    </div>
    """, unsafe_allow_html=True)

    tab_excel, tab_csv = st.tabs(["Excel 分析（字数统计/胜率）", "CSV 评测分析"])

    # Excel 模式
    with tab_excel:
        st.markdown("""
        <div class=\"upload-card\"><div class=\"upload-card-title\">上传 Excel</div><p class=\"upload-card-desc\">需要包含“字数统计”和“胜率”两个 sheet</p></div>
        """, unsafe_allow_html=True)
        uploaded_file = st.file_uploader("选择 Excel 文件", type=['xlsx','xls'], key='excel_uploader', label_visibility='collapsed')
        if uploaded_file is None:
            st.markdown("""
            <div class=\"empty-state\"><div class=\"empty-state-icon\">📈</div><p class=\"empty-state-text\">请上传 Excel 文件</p></div>
            """, unsafe_allow_html=True)
        else:
            try:
                excel_file = pd.ExcelFile(uploaded_file)
                char_sheet = find_sheet_name(excel_file, ['字数统计', '字数', 'count'])
                rate_sheet = find_sheet_name(excel_file, ['胜率', 'win', '评分'])
                if not char_sheet or not rate_sheet:
                    st.error('❌ 未找到所需的sheet。需要："字数统计" 与 "胜率"。')
                    st.info('当前Excel包含的sheet：' + ', '.join(excel_file.sheet_names))
                else:
                    char_count_df = pd.read_excel(excel_file, sheet_name=char_sheet)
                    win_rate_df = pd.read_excel(excel_file, sheet_name=rate_sheet)
                    with st.spinner('正在处理数据...'):
                        tidy_df = convert_to_tidy_format(char_count_df, win_rate_df)
                    st.markdown("<br>", unsafe_allow_html=True)
                    display_stats_cards(tidy_df)
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("""
                    <div class=\"chart-card-title\">📈 字数与胜率关系分析</div>
                    <div class=\"chart-card-desc\">散点+回归线，按模型着色</div>
                    """, unsafe_allow_html=True)
                    fig_scatter, pearson_corr, spearman_corr = create_scatter_plot(tidy_df)
                    st.plotly_chart(fig_scatter, use_container_width=True)
                    st.markdown("<br><br>", unsafe_allow_html=True)
                    st.markdown("""
                    <div class=\"chart-card-title\">📦 按字数区间的胜率分布</div>
                    """, unsafe_allow_html=True)
                    fig_box = create_box_plot(tidy_df)
                    st.plotly_chart(fig_box, use_container_width=True)
            except Exception as e:
                st.error(f"❌ 处理Excel出错：{str(e)}")
                st.exception(e)

    # CSV 模式
    with tab_csv:
        st.markdown("""
        <div class=\"upload-card\"><div class=\"upload-card-title\">上传 CSV</div><p class=\"upload-card-desc\">字段需包含：evaluator_id, seq_no, intent_content, left_candidate_content, left_application_name, right_candidate_content, right_application_name, time_spent_sec, winner, left_application_count, right_candidate_count</p></div>
        """, unsafe_allow_html=True)
        csv_file = st.file_uploader("选择 CSV 文件", type=['csv'], key='csv_uploader', label_visibility='collapsed')
        if csv_file is None:
            st.markdown("""
            <div class=\"empty-state\"><div class=\"empty-state-icon\">🧪</div><p class=\"empty-state-text\">请上传 CSV 评测数据</p></div>
            """, unsafe_allow_html=True)
        else:
            try:
                usecols = ['evaluator_id','seq_no','intent_content','left_candidate_content','left_application_name','left_application_count','right_candidate_content','right_application_name','right_candidate_count','time_spent_sec','winner']
                df = pd.read_csv(csv_file)
                missing = [c for c in usecols if c not in df.columns]
                if missing:
                    st.error('❌ 缺少必要字段：' + ', '.join(missing))
                else:
                    df2 = df.copy()
                    df2['winner_side'] = np.where(df2['winner'].eq(df2['left_application_name']), 'left', np.where(df2['winner'].eq(df2['right_application_name']), 'right', pd.NA))
                    df2['left_win'] = (df2['winner_side'] == 'left').astype('Int64')
                    df2['winner_len'] = np.where(df2['winner_side'].eq('left'), df2['left_application_count'], np.where(df2['winner_side'].eq('right'), df2['right_candidate_count'], pd.NA))
                    df2['loser_len'] = np.where(df2['winner_side'].eq('left'), df2['right_candidate_count'], np.where(df2['winner_side'].eq('right'), df2['left_application_count'], pd.NA))
                    df2['len_diff'] = df2['left_application_count'] - df2['right_candidate_count']
                    bins = [-np.inf, 3, 8, 20, np.inf]
                    labels = ['very_fast','fast','normal','slow']
                    df2['time_bin'] = pd.cut(df2['time_spent_sec'], bins=bins, labels=labels)

                    win_by_model = df2.groupby('winner')[['seq_no']].count().rename(columns={'seq_no':'wins'}).reset_index()
                    win_by_model['win_rate'] = win_by_model['wins'] / len(df2)
                    fig1 = px.bar(win_by_model, x='winner', y='win_rate', title='模型总体胜率', labels={'winner':'模型','win_rate':'胜率'})
                    st.plotly_chart(fig1, use_container_width=True)

                    left_rate = float(df2['left_win'].mean()) if df2['left_win'].notna().any() else 0
                    st.markdown(f"**整体左边胜出比例：{left_rate:.3f}**")

                    len_diff_valid = (df2['winner_len'] - df2['loser_len']).dropna()
                    if not len_diff_valid.empty:
                        fig2 = px.histogram(len_diff_valid, nbins=40, title='胜者字数 - 败者字数 分布')
                        st.plotly_chart(fig2, use_container_width=True)

                    by_bin = df2.dropna(subset=['time_bin','left_win']).groupby('time_bin')['left_win'].mean().reindex(labels)
                    fig3 = px.bar(by_bin, title='不同答题时长下左侧胜率')
                    st.plotly_chart(fig3, use_container_width=True)
            except Exception as e:
                st.error(f"❌ 处理CSV出错：{str(e)}")
                st.exception(e)

if __name__ == "__main__":
    main()

