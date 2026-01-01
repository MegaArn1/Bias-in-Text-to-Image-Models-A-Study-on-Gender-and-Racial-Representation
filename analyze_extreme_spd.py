import pandas as pd
import os

# 1. 读取 Excel 文件
file_path = '统计文件/12-26/spd_metrics_results_4.xlsx'

if not os.path.exists(file_path):
    print(f"错误：找不到文件 {file_path}")
    exit()

# 读取 Sheet1
try:
    df = pd.read_excel(file_path, sheet_name='Sheet1')
except ValueError:
    print("错误：找不到 'Sheet1'，尝试读取第一个 Sheet")
    df = pd.read_excel(file_path)

# 2. 定义 SPD 列
spd_cols = [
    'SPD_Male', 'SPD_Female', 'SPD_Gender_Unknown',
    'SPD_White', 'SPD_Black', 'SPD_Asian', 'SPD_Latino', 'SPD_Race_Unknown'
]

# 检查列是否存在
valid_cols = [c for c in spd_cols if c in df.columns]
if len(valid_cols) != len(spd_cols):
    print(f"警告: 部分 SPD 列未找到。找到的列: {valid_cols}")
    spd_cols = valid_cols

# 3. 分析函数
def analyze_extreme_spd(df, cols):
    results = []
    
    # 按 Model 和 Language 分组
    grouped = df.groupby(['Model', 'Language'])
    
    for (model, language), group in grouped:
        # --- 第一行：大于 10 的情况 ---
        row_over = {
            'Model': model,
            'Language': language,
            'Extreme_Condition': '> 10'
        }
        
        # --- 第二行：小于 -10 的情况 ---
        row_under = {
            'Model': model,
            'Language': language,
            'Extreme_Condition': '< -10'
        }
        
        for col in cols:
            # 1. 处理 > 10
            over_values = group[group[col] > 10][col]
            row_over[f'{col}_Extreme_Count'] = over_values.count()
            row_over[f'{col}_Extreme_Mean'] = over_values.mean() if not over_values.empty else None
            
            # 2. 处理 < -10
            under_values = group[group[col] < -10][col]
            row_under[f'{col}_Extreme_Count'] = under_values.count()
            row_under[f'{col}_Extreme_Mean'] = under_values.mean() if not under_values.empty else None
            
        results.append(row_over)
        results.append(row_under)
        
    return pd.DataFrame(results)

# 4. 执行分析
print("正在统计极端 SPD 值 (>10 或 <-10)...")
analysis_result = analyze_extreme_spd(df, spd_cols)

# 5. 写入 Excel
try:
    with pd.ExcelWriter(file_path, mode='a', engine='openpyxl', if_sheet_exists='replace') as writer:
        analysis_result.to_excel(writer, sheet_name='Extreme_SPD_Analysis', index=False)
        print(f"成功！极端 SPD 统计结果已保存到 'Extreme_SPD_Analysis' 工作表中。")
        
    print("\n结果预览:")
    print(analysis_result.head())

except Exception as e:
    print(f"保存文件时出错: {e}")
