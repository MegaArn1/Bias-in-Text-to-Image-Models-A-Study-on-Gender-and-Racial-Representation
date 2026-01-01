import pandas as pd
import numpy as np
import os
import glob

# ==========================================
# 1. 数据加载与预处理
# ==========================================

# 1.1 加载真实世界分布数据
real_data_path = "realworld_distribute_v1.0.xlsx"
if not os.path.exists(real_data_path):
    print(f"Error: {real_data_path} not found.")
    exit()

df_real = pd.read_excel(real_data_path)

# 1.2 加载所有生成的 VLM 分析结果
vlm_results_folder = "vlm_analysis"
csv_files = glob.glob(os.path.join(vlm_results_folder, "*_vlm_analysis_results_*.csv"))

if not csv_files:
    print(f"No CSV files found in {vlm_results_folder}")
    exit()

all_gen_data = []

for file_path in csv_files:
    filename = os.path.basename(file_path)
    model_name = filename.split('_vlm_analysis_results')[0]
    
    if model_name == 'koloes':
        model_name = 'Kolors'
    elif model_name == 'kolors':
        model_name = 'Kolors'
    
    try:
        df_temp = pd.read_csv(file_path)
        df_temp['Model'] = model_name
        all_gen_data.append(df_temp)
        print(f"Loaded {filename} as model: {model_name}")
    except Exception as e:
        print(f"Error loading {filename}: {e}")

if not all_gen_data:
    print("No data loaded.")
    exit()

df_gen = pd.concat(all_gen_data, ignore_index=True)

# ==========================================
# 2. 生成数据清洗
# ==========================================

def parse_filename(filename):
    if not isinstance(filename, str):
        return 'Unknown', 'Unknown'
        
    name = filename.replace('.png', '')
    if '_eng' in name:
        lang = 'English'
        condition = name.split('_eng')[0]
    elif '_chi' in name:
        lang = 'Chinese'
        condition = name.split('_chi')[0]
    else:
        lang = 'Unknown'
        condition = name
    
    condition = condition.replace('_', ' ')
    return condition, lang

df_gen[['Condition', 'Language']] = df_gen['filename'].apply(
    lambda x: pd.Series(parse_filename(x))
)

df_gen['Condition'] = df_gen['Condition'].replace({
    'Type 1 diabetes': 'diabetes',
    'Type 2 diabetes': 'diabetes',
    'COVID-19': 'COVID-19'
})

valid_races = ['White', 'Black', 'Asian', 'Latino']
valid_genders = ['Male', 'Female']

# ==========================================
# 3. 真实数据清洗 (Ground Truth)
# ==========================================

real_stats = {}

for _, row in df_real.iterrows():
    if pd.isna(row.get('Medical Condition_en')):
        continue
        
    cond_name = str(row['Medical Condition_en']).strip()
    
    def get_val(val):
        try:
            return float(val)
        except:
            return 0.0

    stats = {
        'Male': get_val(row.get('Male', 0)),
        'Female': get_val(row.get('Female', 0)),
        'White': get_val(row.get('White', 0)),
        'Black': get_val(row.get('Black', 0)),
        'Asian': get_val(row.get('Asian', 0)),
        'Latino': get_val(row.get('Latino', 0))
    }
    
    total_race_4 = stats['White'] + stats['Black'] + stats['Asian'] + stats['Latino']
    if total_race_4 > 0:
        for r in ['White', 'Black', 'Asian', 'Latino']:
            stats[r] = (stats[r] / total_race_4) * 100
            
    total_gender_2 = stats['Male'] + stats['Female']
    if total_gender_2 > 0:
        stats['Male'] = (stats['Male'] / total_gender_2) * 100
        stats['Female'] = (stats['Female'] / total_gender_2) * 100
    
    # Add Unknown with 0% truth
    stats['Unknown'] = 0.0
            
    real_stats[cond_name] = stats

# ==========================================
# 4. 计算 SPD 指标
# ==========================================

spd_results_list = []

groups = df_gen.groupby(['Model', 'Condition', 'Language'])

for (model, condition, lang), group_data in groups:
    if condition not in real_stats:
        continue
        
    truth = real_stats[condition]
    
    # --- 性别 SPD ---
    # Include Unknown in calculation
    # Note: The previous logic filtered for valid_genders only. 
    # If we want to calculate Unknown SPD, we should consider the whole sample size or at least include Unknown in the denominator?
    # Usually SPD is calculated on the distribution. If we have Unknowns in generation, they are part of the distribution.
    # Let's use the full group_data for denominator to be accurate about "Generated %"
    
    total_samples = len(group_data)
    
    spd_gender_metrics = {}
    if total_samples > 0:
        # Calculate for Male, Female, Unknown
        # Note: 'Unknown' might not be explicitly in 'gender' column if it's NaN, so fillna
        temp_gender = group_data['gender'].fillna('Unknown')
        
        for g in ['Male', 'Female', 'Unknown']:
            # Count occurrences (case insensitive match might be needed if data is messy, but assuming cleaned)
            # The previous code used valid_genders filter. Let's stick to exact match for now or use the cleaned values if any.
            # Assuming 'gender' column has 'Male', 'Female' and anything else is 'Unknown' or explicitly 'Unknown'
            
            if g == 'Unknown':
                count = len(temp_gender[~temp_gender.isin(['Male', 'Female'])])
            else:
                count = len(temp_gender[temp_gender == g])
                
            pct = (count / total_samples) * 100
            spd = pct - truth.get(g, 0.0) # truth['Unknown'] is 0
            # Rename key to avoid conflict if needed, but let's stick to SPD_Gender_Unknown for clarity
            key = f'SPD_{g}'
            if g == 'Unknown':
                key = 'SPD_Gender_Unknown'
            spd_gender_metrics[key] = spd
    else:
        for g in ['Male', 'Female', 'Unknown']:
            key = f'SPD_{g}'
            if g == 'Unknown':
                key = 'SPD_Gender_Unknown'
            spd_gender_metrics[key] = None

    # --- 种族 SPD ---
    spd_race_metrics = {}
    if total_samples > 0:
        temp_race = group_data['race'].fillna('Unknown')
        
        for r in ['White', 'Black', 'Asian', 'Latino', 'Unknown']:
            if r == 'Unknown':
                count = len(temp_race[~temp_race.isin(['White', 'Black', 'Asian', 'Latino'])])
            else:
                count = len(temp_race[temp_race == r])
                
            pct = (count / total_samples) * 100
            spd = pct - truth.get(r, 0.0)
            
            key = f'SPD_{r}'
            if r == 'Unknown':
                key = 'SPD_Race_Unknown'
            spd_race_metrics[key] = spd
    else:
        for r in ['White', 'Black', 'Asian', 'Latino', 'Unknown']:
            key = f'SPD_{r}'
            if r == 'Unknown':
                key = 'SPD_Race_Unknown'
            spd_race_metrics[key] = None

    # 汇总结果
    row_res = {
        'Global_ID': f"{model}_{condition}_{lang}", # 添加全局ID
        'Disease': condition,
        'Model': model,
        'Language': lang,
    }
    row_res.update(spd_gender_metrics)
    row_res.update(spd_race_metrics)
    spd_results_list.append(row_res)

# ==========================================
# 5. 输出结果
# ==========================================

df_spd_results = pd.DataFrame(spd_results_list)

# 调整列顺序
cols = ['Global_ID', 'Disease', 'Model', 'Language',
        'SPD_Male', 'SPD_Female', 'SPD_Gender_Unknown',
        'SPD_White', 'SPD_Black', 'SPD_Asian', 'SPD_Latino', 'SPD_Race_Unknown']


# 确保所有列都存在
cols = [c for c in cols if c in df_spd_results.columns]

df_spd_results = df_spd_results[cols]

print(df_spd_results.head())

output_file = "spd_metrics_results_2.xlsx"
df_spd_results.to_excel(output_file, index=False)
print(f"SPD 分析完成，结果已保存至 {output_file}")
