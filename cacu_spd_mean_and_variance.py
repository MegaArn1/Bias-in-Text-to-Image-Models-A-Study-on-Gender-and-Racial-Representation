import pandas as pd
import os

# 1. 读取 Excel 文件
file_path = '统计文件/12-26/spd_metrics_results_4.xlsx'

# 检查文件是否存在
if not os.path.exists(file_path):
    print(f"错误：找不到文件 {file_path}")
else:
    # 读取数据
    df = pd.read_excel(file_path)

    # 2. 定义需要计算的 SPD 列分组
    gender_cols = ['SPD_Male', 'SPD_Female', 'SPD_Gender_Unknown']
    race_cols = ['SPD_White', 'SPD_Black', 'SPD_Asian', 'SPD_Latino', 'SPD_Race_Unknown']
    
    def calculate_stats(df, cols, group_name):
        # 过滤掉不存在的列
        valid_cols = [c for c in cols if c in df.columns]
        if not valid_cols:
            print(f"警告: 在 {group_name} 分组中未找到指定的列。")
            return None
        
        print(f"{group_name} 分组正在处理以下列: {valid_cols}")

        # 3. 数据重塑与预处理
        # 将宽表转换为长表，保留 Disease 列
        melted_df = df.melt(id_vars=['Model', 'Language', 'Disease'], value_vars=valid_cols, var_name='SPD_Metric', value_name='SPD_Value')

        # 过滤掉 0 值 (不包含在过代表或欠代表中)
        melted_df = melted_df[melted_df['SPD_Value'] != 0].copy()

        if melted_df.empty:
            print(f"提示: {group_name} 分组中所有值均为 0，无有效数据。")
            return None

        # 标记 过代表 (1) 和 欠代表 (-1)
        melted_df['Lack/Over_Represent'] = melted_df['SPD_Value'].apply(lambda x: 1 if x > 0 else -1)

        # 计算绝对值用于计算 Mean_Abs
        melted_df['Abs_Value'] = melted_df['SPD_Value'].abs()

        # 4. 分组计算 Mean_Abs, Variance, Count, Diseases
        # 按 Model, Language, SPD_Metric, Lack/Over_Represent 分组
        result = melted_df.groupby(['Model', 'Language', 'SPD_Metric', 'Lack/Over_Represent']).agg(
            Mean_Abs=('Abs_Value', 'mean'),
            Variance=('SPD_Value', 'var'),
            Disease_Count=('Disease', 'count'),
            Diseases=('Disease', lambda x: ', '.join(x.astype(str)))
        ).reset_index()

        # 5. 排序
        # 设置 SPD_Metric 为分类变量以指定排序顺序
        result['SPD_Metric'] = pd.Categorical(result['SPD_Metric'], categories=valid_cols, ordered=True)
        
        # 按 Model -> Language -> SPD_Metric (自定义顺序) -> Lack/Over_Represent 排序
        result = result.sort_values(by=['Model', 'Language', 'SPD_Metric', 'Lack/Over_Represent'])
        
        return result

    print("正在处理性别和种族指标...")
    gender_result = calculate_stats(df, gender_cols, "Gender")
    race_result = calculate_stats(df, race_cols, "Race")

    # 8. 将结果写入新的 Sheet
    try:
        # 使用 openpyxl 引擎以追加模式写入新 sheet
        with pd.ExcelWriter(file_path, mode='a', engine='openpyxl', if_sheet_exists='replace') as writer:
            if gender_result is not None:
                gender_result.to_excel(writer, sheet_name='Gender_Analysis', index=False)
                print(f"成功！性别统计结果已保存到 'Gender_Analysis' 工作表中。")
            
            if race_result is not None:
                race_result.to_excel(writer, sheet_name='Race_Analysis', index=False)
                print(f"成功！种族统计结果已保存到 'Race_Analysis' 工作表中。")
        
        # 打印预览
        if gender_result is not None:
            print("\n性别结果预览:")
            print(gender_result.head())
        if race_result is not None:
            print("\n种族结果预览:")
            print(race_result.head())
        
    except Exception as e:
        print(f"保存文件时出错，请确保 Excel 文件已关闭。错误信息: {e}")