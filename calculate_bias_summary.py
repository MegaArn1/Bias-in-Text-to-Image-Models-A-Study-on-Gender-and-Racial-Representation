import pandas as pd
import os

# 1. 读取 Excel 文件
file_path = '统计文件/12-26/t2p_bias_analysis_results_3.xlsx'

if not os.path.exists(file_path):
    print(f"错误：找不到文件 {file_path}")
    exit()

df = pd.read_excel(file_path)

# 2. 定义分析函数
def analyze_bias(df, p_value_col, bias_type_name, output_col_name):
    results = []
    
    # 按 Model 和 Language 分组
    grouped = df.groupby(['Model', 'Language'])
    
    for (model, language), group in grouped:
        # 统计有偏见的疾病数量 (P < 0.05)
        biased_df = group[group[p_value_col] < 0.05]
        biased_count = biased_df.shape[0]
        
        # 获取有偏见的疾病列表
        biased_diseases = biased_df['Condition'].tolist()
        biased_diseases_str = ", ".join(biased_diseases) if biased_diseases else "None"
        
        # 获取无偏见的疾病列表 (P >= 0.05)
        unbiased_diseases = group[group[p_value_col] >= 0.05]['Condition'].tolist()
        unbiased_diseases_str = ", ".join(unbiased_diseases) if unbiased_diseases else "None"
        
        results.append({
            'Model': model,
            'Language': language,
            bias_type_name: bias_type_name, # 填充 Gender 或 Race
            f'Number of diseases with {output_col_name} bias': biased_count,
            f'Diseases with {output_col_name} bias': biased_diseases_str,
            f'Diseases without {output_col_name} bias': unbiased_diseases_str
        })
        
    return pd.DataFrame(results)

# 3. 执行分析
print("正在分析性别偏见...")
gender_summary = analyze_bias(df, 'Gender_Chi2_P_Value', 'Gender', 'gender')

print("正在分析种族偏见...")
race_summary = analyze_bias(df, 'Race_Chi2_P_Value', 'Race', 'race') # 注意：用户示例中种族表头也写了 gender bias，这里我改为 race bias 以防万一，或者保持一致？用户示例：Number of diseases with gender bias (在种族表中)。通常应该是 race bias。我会用 race bias。

# 4. 写入 Excel
try:
    with pd.ExcelWriter(file_path, mode='a', engine='openpyxl', if_sheet_exists='replace') as writer:
        gender_summary.to_excel(writer, sheet_name='Gender_Bias_Summary', index=False)
        print("性别偏见统计已保存到 'Gender_Bias_Summary'")
        
        race_summary.to_excel(writer, sheet_name='Race_Bias_Summary', index=False)
        print("种族偏见统计已保存到 'Race_Bias_Summary'")
        
    print("\n性别结果预览:")
    print(gender_summary.head())
    print("\n种族结果预览:")
    print(race_summary.head())

except Exception as e:
    print(f"保存文件时出错: {e}")
