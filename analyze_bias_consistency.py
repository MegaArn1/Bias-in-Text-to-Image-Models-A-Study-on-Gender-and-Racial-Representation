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
valid_spd_cols = [c for c in spd_cols if c in df.columns]
if not valid_spd_cols:
    print("错误：未找到任何 SPD 列")
    exit()

# 3. 数据预处理：分离中文和英文数据
# 假设 'Disease' 是疾病列，'Model' 是模型列，'Language' 是语言列
required_cols = ['Model', 'Disease', 'Language'] + valid_spd_cols
missing_cols = [c for c in required_cols if c not in df.columns]
if missing_cols:
    print(f"错误：缺少必要列: {missing_cols}")
    exit()

df_subset = df[required_cols]

# 分离中英文
df_chi = df_subset[df_subset['Language'] == 'Chinese'].copy()
df_eng = df_subset[df_subset['Language'] == 'English'].copy()

# 重命名 SPD 列以区分语言
rename_dict_chi = {col: f"{col}_Chi" for col in valid_spd_cols}
rename_dict_eng = {col: f"{col}_Eng" for col in valid_spd_cols}

df_chi = df_chi.rename(columns=rename_dict_chi).drop(columns=['Language'])
df_eng = df_eng.rename(columns=rename_dict_eng).drop(columns=['Language'])

# 4. 合并数据
# 按 Model 和 Disease 合并
merged_df = pd.merge(df_chi, df_eng, on=['Model', 'Disease'], how='inner')

# 5. 偏见一致性判断逻辑
results = []

for index, row in merged_df.iterrows():
    model = row['Model']
    disease = row['Disease']
    
    for col in valid_spd_cols:
        val_chi = row[f"{col}_Chi"]
        val_eng = row[f"{col}_Eng"]
        
        status = "Reserved" # 默认为保留观点
        
        # 判断逻辑
        # 阈值 10
        threshold = 10
        
        is_chi_significant = abs(val_chi) > threshold
        is_eng_significant = abs(val_eng) > threshold
        
        if is_chi_significant and is_eng_significant:
            if (val_chi > threshold and val_eng > threshold) or \
               (val_chi < -threshold and val_eng < -threshold):
                status = "Consistent" # 方向一致
            elif (val_chi > threshold and val_eng < -threshold) or \
                 (val_chi < -threshold and val_eng > threshold):
                status = "Inconsistent" # 方向不一致
        
        # 如果有一项绝对值 <= 10，保持 Reserved
        
        results.append({
            'Model': model,
            'Disease': disease,
            'SPD_Metric': col,
            'Chinese_Value': val_chi,
            'English_Value': val_eng,
            'Consistency_Status': status
        })

results_df = pd.DataFrame(results)

# 6. 写入 Excel
try:
    with pd.ExcelWriter(file_path, mode='a', engine='openpyxl', if_sheet_exists='replace') as writer:
        results_df.to_excel(writer, sheet_name='Bias_Consistency_Analysis', index=False)
        print(f"成功！偏见一致性分析结果已保存到 'Bias_Consistency_Analysis' 工作表中。")
        
    print("\n结果预览:")
    print(results_df.head())
    
    # 简单统计
    print("\n一致性状态统计:")
    print(results_df['Consistency_Status'].value_counts())

except Exception as e:
    print(f"保存文件时出错: {e}")
