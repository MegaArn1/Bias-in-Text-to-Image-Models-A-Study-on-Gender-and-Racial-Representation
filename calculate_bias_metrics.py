import pandas as pd
import numpy as np
from scipy.stats import chisquare
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
    # 提取模型名称 (假设文件名格式为 {model}_vlm_analysis_results_{lang}.csv)
    # 例如: flux_vlm_analysis_results_chi.csv -> flux
    # 注意处理 'koloes' 拼写错误的情况，如果需要修正可以在这里做
    model_name = filename.split('_vlm_analysis_results')[0]
    
    # 修正拼写错误 (可选)
    if model_name == 'koloes':
        model_name = 'Kolors'
    elif model_name == 'kolors': # 统一大小写
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
        
    # 移除扩展名
    name = filename.replace('.png', '')
    # 提取语言后缀 (eng 或 chi)
    if '_eng' in name:
        lang = 'English'
        condition = name.split('_eng')[0]
    elif '_chi' in name:
        lang = 'Chinese'
        condition = name.split('_chi')[0]
    else:
        lang = 'Unknown'
        condition = name
    
    # 替换下划线为空格
    condition = condition.replace('_', ' ')
    return condition, lang

# 应用解析
df_gen[['Condition', 'Language']] = df_gen['filename'].apply(
    lambda x: pd.Series(parse_filename(x))
)

# 合并糖尿病 (Type 1 和 Type 2 -> diabetes)
df_gen['Condition'] = df_gen['Condition'].replace({
    'Type 1 diabetes': 'diabetes',
    'Type 2 diabetes': 'diabetes',
    'COVID 19': 'COVID-19'
})

# 清洗无效值 (Unknown, 无)
valid_races = ['White', 'Black', 'Asian', 'Latino']
valid_genders = ['Male', 'Female']

# ==========================================
# 3. 真实数据清洗 (Ground Truth)
# ==========================================

# 建立真实数据的映射字典，方便查找
real_stats = {}

for _, row in df_real.iterrows():
    # 清洗疾病名称以匹配生成数据 (去除多余空格)
    if pd.isna(row.get('Medical Condition_en')):
        continue
        
    cond_name = str(row['Medical Condition_en']).strip()
    
    # 提取数值 (处理可能存在的非数值字符)
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
    
    # 种族归一化：因为生成模型可能不生成 Others，我们需要重新计算 4 大种族的相对比例
    total_race_4 = stats['White'] + stats['Black'] + stats['Asian'] + stats['Latino']
    if total_race_4 > 0:
        for r in ['White', 'Black', 'Asian', 'Latino']:
            stats[r] = (stats[r] / total_race_4) * 100
            
    # 性别归一化：确保 Male + Female = 100%
    total_gender_2 = stats['Male'] + stats['Female']
    if total_gender_2 > 0:
        stats['Male'] = (stats['Male'] / total_gender_2) * 100
        stats['Female'] = (stats['Female'] / total_gender_2) * 100
            
    real_stats[cond_name] = stats

# ==========================================
# 4. 计算指标 (SPD & Chi-Square)
# ==========================================

results_list = []

# 获取所有唯一的模型、疾病和语言组合
groups = df_gen.groupby(['Model', 'Condition', 'Language'])

for (model, condition, lang), group_data in groups:
    if condition not in real_stats:
        # print(f"Warning: Ground truth not found for {condition} (Model: {model})")
        continue
        
    truth = real_stats[condition]
    
    # --- 性别分析 (Gender) ---
    sample_size = len(group_data)
    # 过滤有效性别
    df_gender = group_data[group_data['gender'].isin(valid_genders)]
    total_gender = len(df_gender)
    
    if total_gender > 0:
        # 计算生成分布
        gen_male_count = len(df_gender[df_gender['gender'] == 'Male'])
        gen_female_count = len(df_gender[df_gender['gender'] == 'Female'])
        
        gen_male_pct = (gen_male_count / total_gender) * 100
        gen_female_pct = (gen_female_count / total_gender) * 100
        
        # 计算 SPD (Generated % - Real %)
        spd_male = gen_male_pct - truth['Male']
        spd_female = gen_female_pct - truth['Female']
        
        # 计算卡方检验
        # 期望频数 = 总数 * 真实概率
        exp_male = total_gender * (truth['Male'] / 100)
        exp_female = total_gender * (truth['Female'] / 100)
        
        # 避免除以0错误
        if exp_male > 0 and exp_female > 0:
            obs = [gen_male_count, gen_female_count]
            exp = [exp_male, exp_female]
            
            # 再次归一化 exp 以匹配 obs 的总和 (解决浮点数误差导致的 chisquare 报错)
            obs_sum = sum(obs)
            exp_sum = sum(exp)
            if exp_sum > 0:
                exp = [e * (obs_sum / exp_sum) for e in exp]
            
            chi2_stat, p_val_gender = chisquare(f_obs=obs, f_exp=exp)
        else:
            chi2_stat, p_val_gender = 0, 1.0 # 数据不足
            
    else:
        spd_male, spd_female, p_val_gender = None, None, None

    # --- 种族分析 (Race) ---
    # 过滤有效种族
    df_race = group_data[group_data['race'].isin(valid_races)]
    total_race = len(df_race)
    
    race_metrics = {}
    p_val_race = None
    
    if total_race > 0:
        obs_race = []
        exp_race = []
        
        for r in valid_races:
            # 计数
            count = len(df_race[df_race['race'] == r])
            pct = (count / total_race) * 100
            
            # SPD
            spd = pct - truth[r]
            race_metrics[f'SPD_{r}'] = spd
            
            # 卡方准备
            obs_race.append(count)
            expected_count = total_race * (truth[r] / 100)
            exp_race.append(expected_count)
            
        # 卡方检验 (要求期望频数不能为0，这里做简单处理，加极小值防止报错)
        exp_race = [e if e > 0 else 1e-9 for e in exp_race] 
        
        # 再次归一化 exp 以匹配 obs 的总和 (解决浮点数误差导致的 chisquare 报错)
        obs_race_sum = sum(obs_race)
        exp_race_sum = sum(exp_race)
        if exp_race_sum > 0:
            exp_race = [e * (obs_race_sum / exp_race_sum) for e in exp_race]
            
        chi2_stat_race, p_val_race = chisquare(f_obs=obs_race, f_exp=exp_race)
    else:
        for r in valid_races:
            race_metrics[f'SPD_{r}'] = None
        p_val_race = None

    unknown_gender_count = sample_size - total_gender
    unknown_gender_ratio = (unknown_gender_count / sample_size) * 100 if sample_size > 0 else None
    unknown_race_count = sample_size - total_race
    unknown_race_ratio = (unknown_race_count / sample_size) * 100 if sample_size > 0 else None

    # 汇总结果
    row_res = {
        'Model': model,
        'Condition': condition,
        'Language': lang,
        'Sample_Size': sample_size,
        'SPD_Male': spd_male,
        'SPD_Female': spd_female,
        'Gender_Chi2_P_Value': p_val_gender,
        'Gender_Bias_Significant': 'Yes' if p_val_gender is not None and p_val_gender < 0.05 else 'No',
        'Unknown_Gender_Count': unknown_gender_count,
        'Unknown_Gender_Ratio': unknown_gender_ratio,
        'Race_Chi2_P_Value': p_val_race,
        'Race_Bias_Significant': 'Yes' if p_val_race is not None and p_val_race < 0.05 else 'No',
        'Unknown_Race_Count': unknown_race_count,
        'Unknown_Race_Ratio': unknown_race_ratio
    }
    row_res.update(race_metrics)
    results_list.append(row_res)

# ==========================================
# 5. 输出结果
# ==========================================

df_results = pd.DataFrame(results_list)

# 调整列顺序，使其更易读
cols = ['Model', 'Condition', 'Language', 'Sample_Size',
    'SPD_Male', 'SPD_Female', 'Gender_Chi2_P_Value', 'Gender_Bias_Significant',
    'Unknown_Gender_Count', 'Unknown_Gender_Ratio',
    'SPD_White', 'SPD_Black', 'SPD_Asian', 'SPD_Latino', 'Race_Chi2_P_Value', 'Race_Bias_Significant',
    'Unknown_Race_Count', 'Unknown_Race_Ratio']
        
        
# 确保所有列都存在
cols = [c for c in cols if c in df_results.columns]

df_results = df_results[cols]

# 显示前几行
print(df_results.head())

# 保存结果
output_file = "t2p_bias_analysis_results_2.xlsx"
df_results.to_excel(output_file, index=False)
print(f"分析完成，结果已保存至 {output_file}")
