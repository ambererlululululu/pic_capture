import pandas as pd
import os


def load_excel_and_compute(file_path=None, file_obj=None):
    """
    读取Excel并计算模型统计
    
    参数:
        file_path: Excel文件路径（可选）
        file_obj: 文件对象（可选，如上传的文件）
    
    返回:
        {
            'summary': [模型统计数据列表],
            'heatmap': {
                'models': [模型名列表],
                'matrix': [[胜率矩阵]]
            },
            'file_info': {'filename': ..., 'rows': ..., 'models': ...}
        }
    """
    # 读取Excel
    if file_obj:
        df = pd.read_excel(file_obj, engine='openpyxl')
    elif file_path and os.path.exists(file_path):
        df = pd.read_excel(file_path, engine='openpyxl')
    else:
        raise ValueError("请提供有效的文件路径或文件对象")
    
    # 检查必需列
    required_cols = ['model_a', 'model_b', 'a_win_cnt', 'draw_cnt', 'a_lose_cnt']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"缺少必需列：{', '.join(missing)}")
    
    # 初始化模型统计字典
    model_stats = {}
    
    # 遍历每一行，双向记账
    for _, row in df.iterrows():
        model_a = str(row['model_a']).strip()
        model_b = str(row['model_b']).strip()
        a_win = int(row['a_win_cnt'])
        draw = int(row['draw_cnt'])
        a_lose = int(row['a_lose_cnt'])
        
        total = a_win + draw + a_lose
        
        if total == 0:
            continue
        
        # 为 model_a 记账
        if model_a not in model_stats:
            model_stats[model_a] = {'win': 0, 'draw': 0, 'lose': 0, 'games': 0}
        model_stats[model_a]['win'] += a_win
        model_stats[model_a]['draw'] += draw
        model_stats[model_a]['lose'] += a_lose
        model_stats[model_a]['games'] += total
        
        # 为 model_b 记账（对称）
        if model_b not in model_stats:
            model_stats[model_b] = {'win': 0, 'draw': 0, 'lose': 0, 'games': 0}
        model_stats[model_b]['win'] += a_lose  # B赢 = A输
        model_stats[model_b]['draw'] += draw
        model_stats[model_b]['lose'] += a_win  # B输 = A赢
        model_stats[model_b]['games'] += total
    
    # 计算胜率等
    summary = []
    for model, stats in model_stats.items():
        games = stats['games']
        if games > 0:
            win_rate = stats['win'] / games
            draw_rate = stats['draw'] / games
            lose_rate = stats['lose'] / games
            summary.append({
                'model': model,
                'win': int(stats['win']),
                'draw': int(stats['draw']),
                'lose': int(stats['lose']),
                'games': int(games),
                'win_rate': win_rate,
                'draw_rate': draw_rate,
                'lose_rate': lose_rate
            })
    
    # 按胜率排序
    summary.sort(key=lambda x: x['win_rate'], reverse=True)
    
    # 生成热力图矩阵
    models = sorted(list(model_stats.keys()))
    n = len(models)
    matrix = [[None] * n for _ in range(n)]
    
    # 构建 model -> index 映射
    model_to_idx = {m: i for i, m in enumerate(models)}
    
    # 遍历Excel，填充矩阵
    for _, row in df.iterrows():
        model_a = str(row['model_a']).strip()
        model_b = str(row['model_b']).strip()
        a_win = int(row['a_win_cnt'])
        draw = int(row['draw_cnt'])
        a_lose = int(row['a_lose_cnt'])
        
        total = a_win + draw + a_lose
        if total == 0:
            continue
        
        if model_a in model_to_idx and model_b in model_to_idx:
            i = model_to_idx[model_a]
            j = model_to_idx[model_b]
            
            # A打B的胜率 = a_win / total
            matrix[i][j] = a_win / total
            
            # B打A的胜率 = a_lose / total（如果还没填）
            if matrix[j][i] is None:
                matrix[j][i] = a_lose / total
    
    # 填充对角线为 None（自己打自己）
    for i in range(n):
        matrix[i][i] = None
    
    file_info = {
        'filename': file_obj.filename if file_obj else os.path.basename(file_path) if file_path else 'unknown.xlsx',
        'rows': len(df),
        'models': len(models)
    }
    
    return {
        'summary': summary,
        'heatmap': {
            'models': models,
            'matrix': matrix
        },
        'file_info': file_info
    }

