import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
from scipy.stats import chi2_contingency
from statsmodels.stats.proportion import binom_test
import statsmodels.api as sm
import statsmodels.formula.api as smf
import requests
import json
import threading

# 可选：默认 DeepSeek Key（用户告知可写入）
DS_DEFAULT_KEY = "sk-0eb74a0fb9f8473fab620d579fc12530"

# ========== LLM 流式工具 ==========
def deepseek_stream_chat(api_key: str, prompt: str):
    """与 DeepSeek 进行流式对话，逐块返回文本。"""
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "stream": True,
    }
    with requests.post(url, headers=headers, json=payload, stream=True, timeout=120) as r:
        r.raise_for_status()
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("data: "):
                data = line[len("data: "):].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                    delta = obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if delta:
                        yield delta
                except Exception:
                    yield ""
import warnings
warnings.filterwarnings('ignore')

# ========== 页面配置 ==========
st.set_page_config(
    page_title="评测数据相关性分析",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ========== CSS 样式 ==========
CSS = """
<style>
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
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
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
def find_column_name(df, candidates, exact_first=True):
    """容错查找列名，支持大小写、空格、下划线等变体"""
    available_cols = df.columns.tolist()
    
    # 精确匹配（优先级最高）
    for c in candidates:
        if c in available_cols:
            return c
    
    if not exact_first:
        return None
    
    # 近似匹配：忽略大小写、空格、下划线
    import re
    def normalize(s):
        return re.sub(r'[_\s]+', '_', str(s).lower().strip())
    
    norm_available = {normalize(col): col for col in available_cols}
    
    for c in candidates:
        norm_c = normalize(c)
        if norm_c in norm_available:
            return norm_available[norm_c]
        
        # 部分匹配：包含关键词
        for key, val in norm_available.items():
            if norm_c in key or key in norm_c:
                return val
    
    return None

def map_columns(df):
    """字段名映射，支持容错匹配"""
    col_mapping = {}
    
    # 字段名候选列表（常见变体）
    field_map = {
        'evaluator_id': ['evaluator_id', 'evaluatorid', 'user_id', 'userid', 'evaluator'],
        'seq_no': ['seq_no', 'seq', 'sequence', 'seqno'],
        'intent_content': ['intent_content', 'intent', 'query', 'question', 'intentcontent'],
        'left_candidate_content': ['left_candidate_content', 'left_candidate', 'left_content', 'leftcandidatecontent', 'left_candidatecontent'],
        'left_application_name': ['left_application_name', 'left_application', 'left_app', 'leftapplicationname', 'leftapp'],
        'left_application_count': ['left_application_count', 'left_applicationcount', 'left_count', 'left_字数', 'left字数', 'leftapplicationcount'],
        'right_candidate_content': ['right_candidate_content', 'right_candidate', 'right_content', 'rightcandidatecontent', 'right_candidatecontent'],
        'right_application_name': ['right_application_name', 'right_application', 'right_app', 'rightapplicationname', 'rightapp'],
        'right_candidate_count': ['right_candidate_count', 'right_candidatecount', 'right_count', 'right_字数', 'right字数', 'rightcandidatecount'],
        'time_spent_sec': ['time_spent_sec', 'time_spent', 'timespent', 'time', 'time_spe', 'timespe'],
        'winner': ['winner', 'win', 'winner_name', 'win_model']
    }
    
    for target, candidates in field_map.items():
        found = find_column_name(df, candidates)
        if found:
            if found != target:
                col_mapping[found] = target
        else:
            # 如果找不到，返回None表示缺失
            return None, target
    
    # 重命名列
    if col_mapping:
        df_renamed = df.rename(columns=col_mapping)
    else:
        df_renamed = df
    
    return df_renamed, None

def derive_fields(df):
    """派生字段"""
    df2 = df.copy()
    
    # winner_side
    df2['winner_side'] = np.where(
        df2['winner'] == df2['left_application_name'], 'left',
        np.where(df2['winner'] == df2['right_application_name'], 'right', pd.NA)
    )
    
    # loser_application_name
    df2['loser_application_name'] = np.where(
        df2['winner_side'] == 'left', df2['right_application_name'],
        np.where(df2['winner_side'] == 'right', df2['left_application_name'], pd.NA)
    )
    
    # winner_len, loser_len
    df2['winner_len'] = np.where(
        df2['winner_side'] == 'left', df2['left_application_count'],
        np.where(df2['winner_side'] == 'right', df2['right_candidate_count'], pd.NA)
    )
    
    df2['loser_len'] = np.where(
        df2['winner_side'] == 'left', df2['right_candidate_count'],
        np.where(df2['winner_side'] == 'right', df2['left_application_count'], pd.NA)
    )
    
    # len_diff
    df2['len_diff'] = df2['left_application_count'] - df2['right_candidate_count']
    
    # pair_model (按字母顺序)
    df2['pair_model'] = df2.apply(
        lambda r: '|'.join(sorted([str(r['left_application_name']), str(r['right_application_name'])])),
        axis=1
    )
    
    # left_win
    df2['left_win'] = (df2['winner_side'] == 'left').astype('Int64')
    
    # time_bin
    bins = [-np.inf, 3, 8, 20, np.inf]
    labels = ['very_fast', 'fast', 'normal', 'slow']
    df2['time_bin'] = pd.cut(df2['time_spent_sec'], bins=bins, labels=labels)
    
    return df2

def render_llm_analysis(container, title: str, prompt: str, api_key: str):
    """在给定容器下方渲染流式LLM解读（并行线程）。"""
    if not api_key:
        container.info("可在左侧填入 DeepSeek API Key 以生成详细解读")
        return
    placeholder = container.empty()
    placeholder.markdown(f"<div class='insight'><div class='insight-title'>🔍 {title}（生成中…）</div><div class='insight-text'></div></div>", unsafe_allow_html=True)

    def _worker():
        buf = []
        for chunk in deepseek_stream_chat(api_key, prompt):
            buf.append(chunk)
            safe_html = ("".join(buf)).replace("\n", "<br>")
            placeholder.markdown(f"<div class='insight'><div class='insight-title'>🔍 {title}</div><div class='insight-text'>{safe_html}</div></div>", unsafe_allow_html=True)

    threading.Thread(target=_worker, daemon=True).start()

# ========== 主应用 ==========
def main():
    # Header
    st.markdown("""
    <div class="header-card">
        <div class="header-title">
            <span class="header-icon">🧪</span>
            <h1>评测数据相关性分析</h1>
        </div>
        <p class="header-subtitle">
            上传CSV/Excel评测数据，系统将进行完整的统计分析：模型偏好、位置偏好、长度影响、时长影响等
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # 上传区
    st.markdown("""
    <div class="upload-card">
        <div class="upload-card-title">上传数据文件</div>
        <p class="upload-card-desc">支持 .csv, .xlsx, .xls 格式。必需字段：evaluator_id, seq_no, intent_content, left_candidate_content, left_application_name, right_candidate_content, right_application_name, time_spent_sec, winner, left_application_count, right_candidate_count</p>
    </div>
    """, unsafe_allow_html=True)

    # 侧边栏：可选 DeepSeek API Key，用于生成更深入的智能总结
    with st.sidebar:
        st.markdown("**可选：输入 DeepSeek API Key 以生成更深入的智能总结**")
        deepseek_key = st.text_input("DeepSeek API Key", type="password", placeholder="sk-...", value=DS_DEFAULT_KEY)
    
    uploaded_file = st.file_uploader(
        "选择文件",
        type=['csv', 'xlsx', 'xls'],
        label_visibility='collapsed'
    )
    
    if uploaded_file is None:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">📊</div>
            <p class="empty-state-text">请先上传数据文件，系统将为您生成详细的分析报告</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    try:
        # 读取文件
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        # 字段名容错映射
        df_mapped, missing_field = map_columns(df)
        
        if missing_field:
            st.error(f'❌ 无法找到必需的字段：{missing_field}')
            st.info(f'当前文件包含的字段：{", ".join(df.columns.tolist())}')
            st.info('💡 提示：系统会自动尝试匹配字段名变体（大小写、下划线、空格等）')
            return
        
        # 检查映射结果
        required_cols = [
            'evaluator_id', 'seq_no', 'intent_content',
            'left_candidate_content', 'left_application_name', 'left_application_count',
            'right_candidate_content', 'right_application_name', 'right_candidate_count',
            'time_spent_sec', 'winner'
        ]
        df = df_mapped
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            st.error(f'❌ 映射后仍缺少必要字段：{", ".join(missing)}')
            st.info(f'当前文件包含的字段：{", ".join(df.columns.tolist())}')
            return

        # 将数值列强制转换为数值，避免对象类型导致统计报错
        numeric_base_cols = ['left_application_count', 'right_candidate_count', 'time_spent_sec']
        for col in numeric_base_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 派生字段
        with st.spinner('正在处理数据...'):
            df2 = derive_fields(df)
            # 衍生列也转为数值
            for col in ['winner_len', 'loser_len', 'len_diff']:
                if col in df2.columns:
                    df2[col] = pd.to_numeric(df2[col], errors='coerce')
        
        st.success(f'✅ 数据加载成功！共 {len(df2)} 条记录，{df2["evaluator_id"].nunique()} 个评测人')
        
        # ========== 第一部分：基础分析（3项）==========
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 🔹 第一部分：基础分析")
        
        # 1. 模型偏好分析
        st.markdown("""
        <div class="chart-card-title">1️⃣ 模型偏好分析</div>
        <div class="chart-card-desc">分析每个模型的总体胜率，以及评测人是否对某个模型更偏爱</div>
        """, unsafe_allow_html=True)
        
        win_by_model = df2.groupby('winner').size().reset_index(name='wins')
        win_by_model['win_rate'] = win_by_model['wins'] / len(df2)
        win_by_model = win_by_model.sort_values('win_rate', ascending=False)
        
        fig1 = px.bar(win_by_model, x='winner', y='win_rate', 
                      title='模型总体胜率', labels={'winner': '模型', 'win_rate': '胜率'},
                      color='win_rate', color_continuous_scale='Viridis')
        fig1.update_layout(plot_bgcolor='#fafafa', paper_bgcolor='white', height=400)
        st.plotly_chart(fig1, use_container_width=True)
        
        # 业务视角解读：模型偏好（强调数据与方法，不涉及品牌与商业猜测）
        sec1_box = st.container()
        sec1_prompt = f"""
你是数据科学家，请针对“模型偏好分析”做数据驱动的解释与建议。评测用户看不到模型名称，请勿从品牌/商业角度猜测。
已知：各模型总体胜率（Top项）={win_by_model.head(10).to_dict(orient='records')}。
请说明：
- 显著性与稳定性（需要哪些额外检验/分层）；
- 可能的统计偏差（样本量、题目分布、评测人差异、位置效应）与改进；
- 下一步数据与方法（置信区间、Bootstrap、分层/配对分析、贝叶斯估计）。
"""
        render_llm_analysis(sec1_box, "模型偏好·数据解读", sec1_prompt, deepseek_key)
        
        # 评测人偏好热力图
        pref_matrix = df2.groupby(['evaluator_id', 'winner']).size().unstack(fill_value=0)
        pref_matrix_norm = pref_matrix.div(pref_matrix.sum(axis=1), axis=0)
        
        fig2 = px.imshow(pref_matrix_norm.T, 
                        labels=dict(x='评测人ID', y='模型', color='投票比例'),
                        title='各评测人模型偏好热力图',
                        color_continuous_scale='Viridis')
        fig2.update_layout(height=500)
        st.plotly_chart(fig2, use_container_width=True)
        
        st.markdown(f"""
        <div class="insight">
            <div class="insight-title">📊 模型偏好结论</div>
            <div class="insight-text">
                最高胜率模型：<strong>{win_by_model.iloc[0]['winner']}</strong> ({win_by_model.iloc[0]['win_rate']:.2%})<br>
                最低胜率模型：<strong>{win_by_model.iloc[-1]['winner']}</strong> ({win_by_model.iloc[-1]['win_rate']:.2%})
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 2. 位置偏好分析
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div class="chart-card-title">2️⃣ 位置偏好分析（左 vs 右）</div>
        <div class="chart-card-desc">分析整体是否倾向选择左侧或右侧答案</div>
        """, unsafe_allow_html=True)
        
        left_rate = df2['left_win'].mean()
        n_total = int(df2['left_win'].notna().sum())
        k_left = int(df2['left_win'].sum())
        pval_binom = float(binom_test(k_left, n_total, 0.5, alternative='two-sided')) if n_total>0 else 1.0

        fig3 = px.bar(x=['左侧胜出', '右侧胜出'], y=[left_rate, 1-left_rate],
                     title='左/右胜出比例', labels={'x': '', 'y': '比例'},
                     color=['左侧胜出', '右侧胜出'],
                     color_discrete_map={'左侧胜出': '#6366F1', '右侧胜出': '#EC4899'})
        fig3.update_layout(plot_bgcolor='#fafafa', paper_bgcolor='white', height=400)
        st.plotly_chart(fig3, use_container_width=True)
        
        # 数据解读：位置偏好（务实、基于数据）
        sec2_box = st.container()
        sec2_prompt = f"""
请对“位置偏好（左/右）”做数据解读：左胜比例={left_rate:.3f}，二项检验p={pval_binom:.4f}。
要求：
- 判断显著性与效应大小；
- 讨论潜在偏差（顺序、显示、题型分布），提出可验证的改进方案（随机化/对称设计/互换顺序/盲评）；
- 给出进一步统计检验与采集建议。
"""
        render_llm_analysis(sec2_box, "位置偏好·数据解读", sec2_prompt, deepseek_key)
        
        # 每位评测人左/右偏好分布
        eval_pref = df2.groupby('evaluator_id')['left_win'].mean().reset_index()
        eval_pref.columns = ['evaluator_id', 'left_rate']
        
        fig4 = px.histogram(eval_pref, x='left_rate', nbins=30,
                           title='每位评测人左/右偏好分布',
                           labels={'left_rate': '左侧胜出比例', 'count': '评测人数量'})
        fig4.update_layout(plot_bgcolor='#fafafa', paper_bgcolor='white', height=400)
        st.plotly_chart(fig4, use_container_width=True)
        
        # 二项检验
        # n_total = len(df2.dropna(subset=['left_win'])) # Moved up
        # k_left = int(df2['left_win'].sum()) # Moved up
        # pval_binom = binom_test(k_left, n_total, 0.5, alternative='two-sided') # Moved up
        
        st.markdown(f"""
        <div class="insight">
            <div class="insight-title">📊 位置偏好结论</div>
            <div class="insight-text">
                整体左边胜出比例：<strong>{left_rate:.3f}</strong><br>
                二项检验 p-value：<strong>{pval_binom:.4f}</strong><br>
                {'✅ 存在显著位置偏好（p<0.05）' if pval_binom < 0.05 else '❌ 不存在显著位置偏好'}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 3. 答案长度影响分析
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div class="chart-card-title">3️⃣ 答案长度影响分析</div>
        <div class="chart-card-desc">分析胜出答案的字数是否普遍更长</div>
        """, unsafe_allow_html=True)
        
        len_diff_valid = (df2['winner_len'] - df2['loser_len']).dropna()
        mean_diff = len_diff_valid.mean()
        median_diff = len_diff_valid.median()
        
        # 字数差分布直方图
        fig5 = px.histogram(len_diff_valid, nbins=50,
                           title='胜者字数 - 败者字数 分布',
                           labels={'value': '字数差', 'count': '频次'})
        fig5.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="差值=0")
        fig5.update_layout(plot_bgcolor='#fafafa', paper_bgcolor='white', height=400)
        st.plotly_chart(fig5, use_container_width=True)
        
        # 胜者长度 vs 败者长度散点图
        valid_len = df2.dropna(subset=['winner_len', 'loser_len'])
        fig6 = px.scatter(valid_len, x='loser_len', y='winner_len',
                         title='胜者长度 vs 败者长度',
                         labels={'loser_len': '败者字数', 'winner_len': '胜者字数'},
                         trendline='ols')
        fig6.add_trace(go.Scatter(x=[0, valid_len['loser_len'].max()],
                                  y=[0, valid_len['loser_len'].max()],
                                  mode='lines', name='y=x', line=dict(dash='dash', color='red')))
        fig6.update_layout(plot_bgcolor='#fafafa', paper_bgcolor='white', height=400)
        st.plotly_chart(fig6, use_container_width=True)
        
        # 相关性分析
        valid_corr = df2.dropna(subset=['len_diff', 'left_win'])
        pearson_corr = valid_corr['len_diff'].corr(valid_corr['left_win'], method='pearson')
        spearman_corr = valid_corr['len_diff'].corr(valid_corr['left_win'], method='spearman')
        
        # t检验：均值是否显著>0
        t_stat, pval_t = stats.ttest_1samp(len_diff_valid, 0)
        
        sec3_box = st.container()
        sec3_prompt = f"""
请对“答案长度影响”做数据解读，避免商业猜测：
字数差均值={mean_diff:.2f}，中位数={median_diff:.2f}，t检验p={pval_t:.4f}；
相关性：Pearson={pearson_corr:.3f}，Spearman={spearman_corr:.3f}；logit系数={len_diff_coef}，p={len_diff_pval}。
请说明：线性/非线性特征、可能的阈值效应、不同意图的分层假设、进一步验证与采集方案。
"""
        render_llm_analysis(sec3_box, "长度影响·数据解读", sec3_prompt, deepseek_key)
        
        st.markdown(f"""
        <div class="insight">
            <div class="insight-title">📊 长度影响结论</div>
            <div class="insight-text">
                胜者-败者字数差：均值 <strong>{mean_diff:.2f}</strong>，中位数 <strong>{median_diff:.2f}</strong><br>
                t检验 p-value：<strong>{pval_t:.4f}</strong> {'✅ 显著大于0' if pval_t < 0.05 and mean_diff > 0 else '❌ 不显著或为负'}<br>
                Pearson相关系数（字数差 vs 左胜）：<strong>{pearson_corr:.3f}</strong><br>
                Spearman相关系数：<strong>{spearman_corr:.3f}</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # ========== 第二部分：深入分析（6项）==========
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("### 🔸 第二部分：深入分析")
        
        # 4. 评测人偏好诊断
        st.markdown("""
        <div class="chart-card-title">4️⃣ 评测人偏好诊断（个体层面）</div>
        <div class="chart-card-desc">找出明显偏左、偏右或偏向某模型的评测人</div>
        """, unsafe_allow_html=True)
        
        eval_stats = []
        for uid, g in df2.groupby('evaluator_id'):
            n = g['left_win'].notna().sum()
            k = int(g['left_win'].sum())
            left_rate = k/n if n > 0 else 0
            
            # 模型偏好
            model_votes = g['winner'].value_counts()
            top_model_rate = (model_votes.iloc[0] / len(g)) if len(model_votes) > 0 else 0
            
            # 二项检验
            pval = binom_test(k, n, 0.5, alternative='two-sided') if n > 0 else 1
            
            eval_stats.append({
                'evaluator_id': uid,
                'n': n,
                'left_rate': left_rate,
                'top_model': model_votes.index[0] if len(model_votes) > 0 else None,
                'top_model_rate': top_model_rate,
                'p_value': pval,
                'biased': (left_rate < 0.35 or left_rate > 0.65 or top_model_rate > 0.65) and pval < 0.05
            })
        
        eval_df = pd.DataFrame(eval_stats)
        biased_evals = eval_df[eval_df['biased'] == True]
        
        st.dataframe(biased_evals[['evaluator_id', 'n', 'left_rate', 'top_model', 'top_model_rate', 'p_value']].head(20))
        st.info(f'共发现 {len(biased_evals)} 个明显偏好评测人（位置偏好比例<0.35或>0.65，或模型偏好>0.65，且p<0.05）')
        
        # 5. 模型对模型胜率矩阵
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div class="chart-card-title">5️⃣ 模型对模型胜率矩阵（公平对战分析）</div>
        <div class="chart-card-desc">计算每一对模型组合的胜率，排除位置影响</div>
        """, unsafe_allow_html=True)
        
        # 构建模型对矩阵
        models = sorted(df2['left_application_name'].unique().tolist() + df2['right_application_name'].unique().tolist())
        models = sorted(list(set(models)))
        
        win_matrix = np.zeros((len(models), len(models)))
        
        for i, model_a in enumerate(models):
            for j, model_b in enumerate(models):
                if i == j:
                    win_matrix[i, j] = 0.5
                    continue
                
                # 找出model_a在左侧，model_b在右侧的对战
                matches_left = df2[(df2['left_application_name'] == model_a) & (df2['right_application_name'] == model_b)]
                wins_left = (matches_left['winner'] == model_a).sum()
                n_left = len(matches_left)
                
                # 找出model_b在左侧，model_a在右侧的对战
                matches_right = df2[(df2['left_application_name'] == model_b) & (df2['right_application_name'] == model_a)]
                wins_right = (matches_right['winner'] == model_a).sum()
                n_right = len(matches_right)
                
                total_wins = wins_left + wins_right
                total_n = n_left + n_right
                
                if total_n > 0:
                    win_matrix[i, j] = total_wins / total_n
        
        fig7 = px.imshow(win_matrix, x=models, y=models,
                        labels=dict(x='对手模型', y='模型', color='胜率'),
                        title='模型对模型胜率矩阵',
                        color_continuous_scale='RdYlGn',
                        aspect='auto')
        fig7.update_layout(height=600)
        st.plotly_chart(fig7, use_container_width=True)
        
        # 业务视角解读：模型对模型胜率矩阵
        sec5_box = st.container()
        sec5_prompt = f"""
你是数据科学家兼业务负责人，请对“模型对模型胜率矩阵”给出深度解读与建议。
已知：模型对模型胜率矩阵={win_matrix.round(3).to_dict()}。
请用中文分条说明：
1) 哪些模型组合表现稳定/波动；2) 可能的业务原因（模型特性、任务匹配、竞争关系）；
3) 与字数或意图类型的关系的假设；4) 下一步商业决策（采买、路由、提示词策略、质检）。
"""
        render_llm_analysis(sec5_box, "模型对模型胜率矩阵·业务解读", sec5_prompt, deepseek_key)
        
        # 6. 长度与投票结果的多变量分析（逻辑回归）
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div class="chart-card-title">6️⃣ 长度与投票结果的多变量分析</div>
        <div class="chart-card-desc">使用逻辑回归分析字数差对胜负的影响</div>
        """, unsafe_allow_html=True)
        
        logit_df = df2.dropna(subset=['left_win', 'len_diff', 'left_application_name', 'right_application_name']).copy()
        logit_df['left_win'] = logit_df['left_win'].astype(int)
        
        try:
            model_logit = smf.logit(
                'left_win ~ len_diff + C(left_application_name) + C(right_application_name)',
                data=logit_df
            ).fit(disp=False)
            
            st.text(str(model_logit.summary()))
            
            # 系数条形图
            coef_df = pd.DataFrame({
                '变量': model_logit.params.index,
                '系数': model_logit.params.values,
                'p值': model_logit.pvalues.values
            })
            
            fig8 = px.bar(coef_df.head(10), x='变量', y='系数',
                         title='逻辑回归系数（Top 10）',
                         color='p值',
                         color_continuous_scale='RdYlGn_r')
            fig8.update_layout(height=400)
            st.plotly_chart(fig8, use_container_width=True)
            
            len_diff_coef = float(model_logit.params.get('len_diff', float('nan')))
            len_diff_pval = float(model_logit.pvalues.get('len_diff', float('nan')))
            
            st.markdown(f"""
            <div class="insight">
                <div class="insight-title">📊 逻辑回归结论</div>
                <div class="insight-text">
                    字数差（len_diff）系数：<strong>{len_diff_coef:.4f}</strong>，p-value：<strong>{len_diff_pval:.4f}</strong><br>
                    {'✅ 字数差对胜负有显著影响' if len_diff_pval < 0.05 else '❌ 字数差对胜负无显著影响'}
                </div>
            </div>
            """, unsafe_allow_html=True)
        except Exception as e:
            st.warning(f'逻辑回归模型拟合失败：{str(e)}')
            len_diff_coef, len_diff_pval = None, None
        
        # 7. 答题时长的影响分析
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div class="chart-card-title">7️⃣ 答题时长的影响分析</div>
        <div class="chart-card-desc">分析不同答题时长下的左边胜出比例</div>
        """, unsafe_allow_html=True)
        
        by_bin = df2.dropna(subset=['time_bin', 'left_win']).groupby('time_bin')['left_win'].mean()
        by_bin = by_bin.reindex(['very_fast', 'fast', 'normal', 'slow'])
        
        fig9 = px.bar(by_bin, title='不同答题时长下左侧胜率',
                     labels={'index': '时长区间', 'value': '左侧胜率'},
                     color=by_bin.values,
                     color_continuous_scale='Viridis')
        fig9.update_layout(height=400)
        st.plotly_chart(fig9, use_container_width=True)
        
        st.markdown(f"""
        <div class="insight">
            <div class="insight-title">📊 时长影响结论</div>
            <div class="insight-text">
                建议：可考虑过滤 very_fast (<3s) 的记录，以降低偶然偏差影响。
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 业务视角解读：时长影响
        sec7_box = st.container()
        sec7_prompt = f"""
你是数据科学家兼业务负责人，请对“答题时长影响”给出解读：
平均答题时长={df2['time_spent_sec'].mean():.2f}秒，二项检验p={pval_binom:.4f}。
请说明：1) 是否存在显著时长偏好及可能原因（模型性能、任务难度）；
2) 如何在线上AB或采集流程中去偏（随机化、互换顺序、盲评）；
3) 时长偏好的业务影响（胜率评估、模型预算分配）。
"""
        render_llm_analysis(sec7_box, "时长影响·业务解读", sec7_prompt, deepseek_key)
        
        # 8. 数据清洗与可信度提升
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div class="chart-card-title">8️⃣ 数据清洗与可信度提升</div>
        <div class="chart-card-desc">过滤偏好评测人和过短记录，重新计算模型胜率</div>
        """, unsafe_allow_html=True)
        
        # 清洗数据
        clean_df = df2.copy()
        biased_ids = set(biased_evals['evaluator_id'])
        clean_df = clean_df[~clean_df['evaluator_id'].isin(biased_ids)]
        clean_df = clean_df[clean_df['time_spent_sec'] >= 3]
        
        # 对比
        orig_left_rate = df2['left_win'].mean()
        clean_left_rate = clean_df['left_win'].mean()
        
        orig_model_win = df2.groupby('winner').size() / len(df2)
        clean_model_win = clean_df.groupby('winner').size() / len(clean_df)
        
        comparison_df = pd.DataFrame({
            '原始数据': orig_model_win,
            '清洗后': clean_model_win
        }).fillna(0)
        
        fig10 = px.bar(comparison_df, barmode='group',
                      title='清洗前后模型胜率对比',
                      labels={'value': '胜率', 'index': '模型'})
        fig10.update_layout(height=400)
        st.plotly_chart(fig10, use_container_width=True)
        
        st.markdown(f"""
        <div class="insight">
            <div class="insight-title">📊 清洗效果</div>
            <div class="insight-text">
                原始数据：{len(df2)} 条，左边胜率 {orig_left_rate:.3f}<br>
                清洗后：{len(clean_df)} 条，左边胜率 {clean_left_rate:.3f}<br>
                过滤了 {len(biased_evals)} 个偏好评测人和 {len(df2) - len(clean_df) - len(biased_evals)} 条过短记录
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 业务视角解读：清洗效果
        sec8_box = st.container()
        sec8_prompt = f"""
请解读“数据清洗效果”：原始左胜率={orig_left_rate:.3f}，清洗后={clean_left_rate:.3f}。
说明：清洗策略对估计偏差的影响、残留问题与验证方法、进一步数据规范与质检建议。
"""
        render_llm_analysis(sec8_box, "数据清洗·数据解读", sec8_prompt, deepseek_key)
        
        # 9. 按Intent分析模型表现
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div class="chart-card-title">9️⃣ 按Intent（任务类型）分析模型表现</div>
        <div class="chart-card-desc">分析每个模型在不同任务类型下的胜率</div>
        """, unsafe_allow_html=True)
        
        # 计算每个 intent 下各模型的胜率，避免 reset_index 冲突
        intent_counts = df2.groupby(['intent_content', 'winner']).size().reset_index(name='cnt')
        intent_counts['total'] = intent_counts.groupby('intent_content')['cnt'].transform('sum')
        intent_counts['win_rate'] = intent_counts['cnt'] / intent_counts['total']
        intent_model_win = intent_counts[['intent_content', 'winner', 'win_rate']]
        
        # 选出Top intent
        top_intents = df2['intent_content'].value_counts().head(10).index
        intent_model_top = intent_model_win[intent_model_win['intent_content'].isin(top_intents)]
        
        fig11 = px.bar(intent_model_top, x='intent_content', y='win_rate', color='winner',
                      title='Top 10 Intent 下各模型胜率',
                      labels={'intent_content': 'Intent', 'win_rate': '胜率', 'winner': '模型'})
        fig11.update_layout(height=500, xaxis_tickangle=-45)
        st.plotly_chart(fig11, use_container_width=True)
        
        # 业务视角解读：按Intent分析模型表现
        sec9_box = st.container()
        sec9_prompt = f"""
基于“Intent×模型胜率”，请做数据解读：Top Intents={list(map(str, top_intents))}；高胜率组合样例={strong_combos.head(10).to_dict(orient='records')}。
请说明：分层显著性（样本量要求、置信区间）、意图与长度/位置交互的假设、需要的额外检验与数据。
"""
        render_llm_analysis(sec9_box, "Intent 表现·数据解读", sec9_prompt, deepseek_key)
        
        # 找出胜率>0.7的组合
        strong_combos = intent_model_win[intent_model_win['win_rate'] > 0.7].sort_values('win_rate', ascending=False)
        if len(strong_combos) > 0:
            st.dataframe(strong_combos.head(20))

        # —— 扩展指标：各模型平均回答长度（综合左右侧） ——
        left_len = df2[['left_application_name', 'left_application_count']].rename(columns={'left_application_name': 'model', 'left_application_count': 'length'})
        right_len = df2[['right_application_name', 'right_candidate_count']].rename(columns={'right_application_name': 'model', 'right_candidate_count': 'length'})
        model_len = pd.concat([left_len, right_len], ignore_index=True)
        model_len['length'] = pd.to_numeric(model_len['length'], errors='coerce')
        model_len_stats = model_len.groupby('model')['length'].mean().sort_values(ascending=False)

        # —— 扩展指标：按 intent 的“难度”（赢家熵，越高越难） ——
        def entropy(s):
            p = (s / s.sum()).values
            p = p[p > 0]
            return float(-(p * np.log2(p)).sum())
        intent_entropy = df2.groupby('intent_content')['winner'].value_counts().groupby(level=0).apply(entropy).sort_values(ascending=False)

        # —— 扩展指标：强势/弱势模型对 ——
        pair_rows = []
        for i, model_a in enumerate(models):
            for j, model_b in enumerate(models):
                if i >= j:
                    continue
                matches_ab = df2[(df2['left_application_name'] == model_a) & (df2['right_application_name'] == model_b)]
                wins_a_left = (matches_ab['winner'] == model_a).sum()
                n_ab_left = len(matches_ab)
                matches_ba = df2[(df2['left_application_name'] == model_b) & (df2['right_application_name'] == model_a)]
                wins_a_right = (matches_ba['winner'] == model_a).sum()
                n_ab_right = len(matches_ba)
                total_wins = wins_a_left + wins_a_right
                total_n = n_ab_left + n_ab_right
                if total_n > 0:
                    pair_rows.append({'pair': f'{model_a} vs {model_b}', 'a': model_a, 'b': model_b, 'a_win_rate': total_wins/total_n, 'n': total_n})
        pair_summary = pd.DataFrame(pair_rows).sort_values('a_win_rate', ascending=False)
        strong_pairs = pair_summary[(pair_summary['n'] >= 20) & ((pair_summary['a_win_rate'] >= 0.65) | (pair_summary['a_win_rate'] <= 0.35))]
        
        # 10. 时间与质量的联合分析（选做）
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div class="chart-card-title">🔟 时间与质量的联合分析</div>
        <div class="chart-card-desc">分析评测人花费时间与判断结果一致性的关系</div>
        """, unsafe_allow_html=True)
        
        # 计算每位评测人的决策稳定性（left_win的方差）
        eval_stability = df2.groupby('evaluator_id').agg({
            'left_win': 'var',
            'time_spent_sec': 'mean'
        }).reset_index()
        eval_stability = eval_stability.dropna(subset=['left_win'])
        
        fig12 = px.scatter(eval_stability, x='time_spent_sec', y='left_win',
                          title='答题时长 vs 决策稳定性（方差）',
                          labels={'time_spent_sec': '平均答题时长（秒）', 'left_win': 'left_win方差'},
                          trendline='ols')
        fig12.update_layout(height=400)
        st.plotly_chart(fig12, use_container_width=True)
        
        # 业务视角解读：时间与质量的联合分析
        sec10_box = st.container()
        sec10_prompt = f"""
请解读“时间与质量的联合分析”：答题时长 vs 决策稳定性（方差）={eval_stability.to_dict(orient='records')}。
讨论：极短时长样本质量、过滤阈值的依据、敏感性分析设计、线上监控指标。
"""
        render_llm_analysis(sec10_box, "时间与质量联合分析·数据解读", sec10_prompt, deepseek_key)
        
        # ========== 总结 ==========
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("### 📋 总体分析总结")
        
        summary = f"""
        <div class="insight">
            <div class="insight-title">📊 分析总结</div>
            <div class="insight-text">
                <strong>主要偏好趋势：</strong><br>
                - 最高胜率模型：{win_by_model.iloc[0]['winner']} ({win_by_model.iloc[0]['win_rate']:.2%})<br>
                - 左侧胜出比例：{left_rate:.3f}{'（显著偏好）' if pval_binom < 0.05 else '（无显著偏好）'}<br><br>
                
                <strong>显著偏差的评测人数量：</strong>{len(biased_evals)}<br><br>
                
                <strong>字数与胜负的相关性：</strong><br>
                - Pearson相关系数：{pearson_corr:.3f}<br>
                - Spearman相关系数：{spearman_corr:.3f}<br><br>
                
                <strong>清洗后 vs 原始数据：</strong><br>
                - 过滤了 {len(df2) - len(clean_df)} 条记录（{len(biased_evals)} 个偏好评测人 + {len(df2) - len(clean_df) - len(biased_evals)} 条过短记录）<br>
                - 左边胜率从 {orig_left_rate:.3f} 变为 {clean_left_rate:.3f}<br><br>
                
                <strong>各Intent的强弱领域：</strong><br>
                - 发现 {len(strong_combos)} 个模型-Intent组合胜率>0.7
            </div>
        </div>
        """
        st.markdown(summary, unsafe_allow_html=True)
        # 扩展要点（内置文字总结）
        bullet_html = "<ul>"
        if len(win_by_model) > 0:
            bullet_html += f"<li>模型整体胜率排名前1：{str(win_by_model.iloc[0]['winner'])}（{float(win_by_model.iloc[0]['win_rate']):.2%}）</li>"
        if not model_len_stats.empty:
            bullet_html += f"<li>平均回答更长的模型：{model_len_stats.index[0]}（{model_len_stats.iloc[0]:.0f}字）</li>"
        if len(strong_pairs) > 0:
            sp = strong_pairs.iloc[0]
            bullet_html += f"<li>显著强势的模型对：{sp['a']} 对 {sp['b']}（样本 {int(sp['n'])}，{sp['a']} 胜率 {float(sp['a_win_rate']):.1%}）</li>"
        if len(intent_entropy) > 0:
            bullet_html += f"<li>最“困难”的任务类型（赢家分散度最高）：{intent_entropy.index[0]}</li>"
        bullet_html += "</ul>"
        st.markdown(f"<div class='insight'><div class='insight-title'>📌 扩展要点</div><div class='insight-text'>{bullet_html}</div></div>", unsafe_allow_html=True)

        # ========== LLM 智能总结（可选） ==========
        if deepseek_key:
            st.markdown("<br>", unsafe_allow_html=True)
            llm_box = st.container()
            if st.button('🚀 使用 DeepSeek 生成更深入的智能总结'):
                try:
                    # 组织关键信息供模型参考
                    metrics = {
                        'top_model': str(win_by_model.iloc[0]['winner']) if len(win_by_model)>0 else 'N/A',
                        'top_model_rate': float(win_by_model.iloc[0]['win_rate']) if len(win_by_model)>0 else None,
                        'left_rate': float(left_rate),
                        'pval_binom': float(pval_binom),
                        'len_diff_mean': float(mean_diff),
                        'len_diff_median': float(median_diff),
                        'pearson_corr': float(pearson_corr),
                        'spearman_corr': float(spearman_corr),
                        'len_diff_coef': None if len_diff_coef is None else float(len_diff_coef),
                        'len_diff_pval': None if len_diff_pval is None else float(len_diff_pval),
                        'top_intents': list(map(str, list(top_intents))),
                        'strong_pairs_sample': strong_pairs.head(10).to_dict(orient='records'),
                        'model_avg_length_top': model_len_stats.head(10).round(1).to_dict(),
                        'intent_entropy_top': intent_entropy.head(10).round(3).to_dict(),
                        'time_bin': by_bin.round(3).to_dict()
                    }
                    prompt = f"""
你是资深数据科学负责人。请将下面“自动统计结果”整合成一份结构化、可执行的《分析与行动建议报告》，输出包含：
1) 高层摘要（3-6 条）；2) 关键发现（数据证据+解释）；3) 偏差来源与风险；4) 具体行动建议（按优先级排序）；5) 需要的后续实验与数据；6) 附注（口径/注意事项）。
自动统计结果如下：
{json.dumps(metrics, ensure_ascii=False)}
"""
                    # 流式输出
                    placeholder = llm_box.empty()
                    placeholder.markdown("<div class='insight'><div class='insight-title'>🤝 DeepSeek 智能总结（生成中…）</div><div class='insight-text' id='llm_out'></div></div>", unsafe_allow_html=True)
                    buf = []
                    for chunk in deepseek_stream_chat(deepseek_key, prompt):
                        buf.append(chunk)
                        safe_html = ("".join(buf)).replace("\n", "<br>")
                        placeholder.markdown(f"<div class='insight'><div class='insight-title'>🤝 DeepSeek 智能总结</div><div class='insight-text'>{safe_html}</div></div>", unsafe_allow_html=True)
                except Exception as e:
                    st.warning(f"DeepSeek 生成失败：{str(e)}")
        
    except Exception as e:
        st.error(f"❌ 处理文件时出错：{str(e)}")
        st.exception(e)

if __name__ == "__main__":
    main()

