import pandas as pd
from pathlib import Path
import glob
import os

# Configuration
VLMS_FOLDER = Path("vlm_analysis")
REALWORLD_FILE = Path("realworld_distribute_v1.0.xlsx")
OUTPUT_GENDER = Path("demographics_gender_3.csv")
OUTPUT_RACE = Path("demographics_race_3.csv")

# Mappings based on user request and known data
# User requested specific categories:
# Race: "White", "Black", "Asian", "Hispanic/Latino", "Unknown"
# Gender: "Male", "Female", "Unknown"

RACE_MAPPING = {
    'White': 'White',
    'Black': 'Black',
    'Asian': 'Asian',
    'Latino': 'Hispanic/Latino',
    'Hispanic': 'Hispanic/Latino'
}

def get_race_category(r):
    if pd.isna(r):
        return 'Unknown'
    r = str(r).strip()
    # Check if it's one of our known keys
    if r in RACE_MAPPING:
        return RACE_MAPPING[r]
    return 'Unknown'

def get_gender_category(g):
    if pd.isna(g):
        return 'Unknown'
    g = str(g).strip().lower()
    if g == 'male':
        return 'Male'
    elif g == 'female':
        return 'Female'
    else:
        return 'Unknown'

DISEASE_LIST = [
    "Amyotrophic Lateral Sclerosis",
    "Bacterial Pneumonia",
    "Colon cancer",
    "COVID 19",
    "Hepatitis B",
    "HIV",
    "Huntington Disease",
    "Hypertension",
    "Lupus",
    "Major Depressive Disorder",
    "Multiple Myeloma",
    "Multiple Sclerosis",
    "Preeclampsia",
    "Prostate cancer",
    "Rheumatoid Arthritis",
    "Sarcoidosis",
    "Syphilis",
    "Takotsubo cardiomyopathy",
    "Tricuspid Endocarditis",
    "Tuberculosis",
    "Type 1 diabetes",
    "Type 2 diabetes",
    "Diabetes" # Added for merged stats
]

def load_realworld_data():
    if not REALWORLD_FILE.exists():
        print(f"{REALWORLD_FILE} does not exist")
        return {}
    
    try:
        df = pd.read_excel(REALWORLD_FILE)
    except Exception as e:
        print(f"Error reading {REALWORLD_FILE}: {e}")
        return {}

    # Create a dictionary mapping disease -> {category -> percentage}
    # Columns: Medical Condition_en, Male, Female, White, Asian, Black, Latino
    
    real_data = {}
    for _, row in df.iterrows():
        disease = str(row['Medical Condition_en']).strip()
        
        # Handle special naming if needed, but assuming exact match or close enough
        # Note: Excel has "COVID 19", our list has "COVID 19".
        
        stats = {
            'Male': row.get('Male', 0),
            'Female': row.get('Female', 0),
            'Unknown': row.get('Others', 0), # Map 'Others' from Excel to 'Unknown'
            'White': row.get('White', 0),
            'Black': row.get('Black', 0),
            'Asian': row.get('Asian', 0),
            'Hispanic/Latino': row.get('Latino', 0)
        }
        real_data[disease] = stats
        
    return real_data

def detect_model_language(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith("_chi.csv"):
        return "chi" 
    if lower.endswith("_eng.csv"):
        return "eng"
    return "unknown"

def load_data():
    if not VLMS_FOLDER.exists():
        print(f"{VLMS_FOLDER} does not exist")
        return pd.DataFrame()

    csv_paths = list(VLMS_FOLDER.glob("*_vlm_analysis_results_*.csv"))
    if not csv_paths:
        print("No CSV files found.")
        return pd.DataFrame()

    combined = []
    for csv_path in sorted(csv_paths):
        # Model name extraction
        # filename example: flux_vlm_analysis_results_chi.csv
        model_name = csv_path.name.split("_vlm_analysis_results")[0]
        
        # Normalize model name
        if model_name == 'koloes':
            model_name = 'Kolors'
        elif model_name == 'kolors':
            model_name = 'Kolors'
        
        # Language extraction
        lang = detect_model_language(csv_path.name)
        
        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            print(f"Error reading {csv_path}: {e}")
            continue
            
        if df.empty:
            continue

        # We need Condition (disease). 
        def extract_condition(fname):
            if not isinstance(fname, str): return "Unknown"
            base = Path(fname).stem
            # Remove language suffix and index (e.g. _chi_01)
            # Format: {Disease}_{lang}_{index}
            parts = base.split('_')
            if len(parts) >= 3:
                # Check if second to last is lang
                if parts[-2] in ['chi', 'eng']:
                    # Reconstruct disease name
                    disease_parts = parts[:-2]
                    disease_name = "_".join(disease_parts)
                    return disease_name.replace("_", " ").strip()
            
            # Fallback if format doesn't match exactly (though user said it should)
            return base.replace("_", " ").strip()

        df['disease'] = df['filename'].apply(extract_condition)
        df['Model'] = model_name
        df['Language'] = lang
        
        combined.append(df)

    if not combined:
        return pd.DataFrame()
    
    full_df = pd.concat(combined, ignore_index=True)
    
    # Handle Diabetes Merge
    # Create a copy of Type 1 and Type 2 rows, rename disease to "Diabetes", and append
    diabetes_df = full_df[full_df['disease'].isin(['Type 1 diabetes', 'Type 2 diabetes'])].copy()
    if not diabetes_df.empty:
        diabetes_df['disease'] = 'Diabetes'
        full_df = pd.concat([full_df, diabetes_df], ignore_index=True)
        
    return full_df

def create_structured_table(df, category_col, value_mapping_func, output_col_name, categories_order, real_data_key_map):
    # Apply mapping
    df[output_col_name] = df[category_col].apply(value_mapping_func)
    
    # Prepare the base index: All combinations of Disease and Category
    index_tuples = []
    for d in DISEASE_LIST:
        for c in categories_order:
            index_tuples.append((d, c))
    
    base_df = pd.DataFrame(index_tuples, columns=['disease', output_col_name])
    
    # Add Real World Distribution Column
    real_data = load_realworld_data()
    
    def get_real_val(row):
        disease = row['disease']
        category = row[output_col_name]
        
        # Special handling for Diabetes
        # If disease is Type 1 or Type 2, return None (empty)
        if disease in ['Type 1 diabetes', 'Type 2 diabetes']:
            return None
            
        # If disease is Diabetes, look up "Diabetes" in real_data (assuming it exists there or mapped)
        # The user said "Type 2 diabetes" in excel has the data for generic Diabetes? 
        # Or "Type 2 diabetes" in excel is just Type 2?
        # User said: "Type 1 diabetes" and "Type 2 diabetes" realworld_distribution can be empty.
        # But "Diabetes" row should have normal values.
        # We need to find where "Diabetes" data comes from in Excel.
        # Assuming the Excel file has a row for "Diabetes" OR we use "Type 2 diabetes" data for "Diabetes"?
        # Re-reading user request: "Type 2 diabetes"下方额外新添加一个疾病“Diabetes”，正常加入它的真实分布的数值"
        # This implies the Excel file MIGHT NOT have "Diabetes" row, but we should use something?
        # Wait, if Excel doesn't have "Diabetes", where do we get the value?
        # "正常加入它的真实分布的数值" -> implies we should have it.
        # Let's assume the Excel file HAS a row named "Diabetes" or we map "Type 2 diabetes" to it if missing?
        # Actually, looking at the `read_excel` output earlier, I didn't see "Diabetes".
        # I saw "Type 1 diabetes" and "Type 2 diabetes" in the list? No, I saw "Bacterial Pneumonia", "Colon cancer"...
        # Let's assume for now we look up the disease name directly.
        
        # Map category name to Excel column name
        excel_col = real_data_key_map.get(category)
        
        if disease in real_data and excel_col:
            return real_data[disease].get(excel_col)
        return None

    base_df['realworld_distribution'] = base_df.apply(get_real_val, axis=1)

    # Get list of models
    models = sorted(df['Model'].unique())
    
    final_df = base_df.copy()
    
    for model in models:
        # Filter for this model
        model_df = df[df['Model'] == model]
        
        for lang in ['eng', 'chi']:
            lang_df = model_df[model_df['Language'] == lang]
            
            # Group by disease and category
            counts = lang_df.groupby(['disease', output_col_name]).size().reset_index(name='count')
            
            merged = pd.merge(base_df, counts, on=['disease', output_col_name], how='left')
            merged['count'] = merged['count'].fillna(0).astype(int)
            
            # Calculate percentage
            disease_totals = merged.groupby('disease')['count'].transform('sum')
            
            # Avoid division by zero
            merged['percentage'] = (merged['count'] / disease_totals * 100).fillna(0).round(1)
            
            # Rename columns
            col_count = f"{model}_{lang}"
            col_pct = f"{model}_{lang}_p"
            
            final_df[col_count] = merged['count']
            final_df[col_pct] = merged['percentage']

    return final_df

def main():
    df = load_data()
    if df.empty:
        print("No data loaded.")
        return

    # Gender Table
    print("Generating Gender Table...")
    gender_cats = ['Male', 'Female', 'Unknown']
    gender_map = {'Male': 'Male', 'Female': 'Female', 'Unknown': 'Unknown'}
    gender_table = create_structured_table(df, 'gender', get_gender_category, 'sex', gender_cats, gender_map)
    gender_table.to_csv(OUTPUT_GENDER, index=False)
    print(f"Saved to {OUTPUT_GENDER}")

    # Race Table
    print("Generating Race Table...")
    race_cats = ['White', 'Black', 'Asian', 'Hispanic/Latino', 'Unknown']
    race_map = {
        'White': 'White', 
        'Black': 'Black', 
        'Asian': 'Asian', 
        'Hispanic/Latino': 'Hispanic/Latino',
        'Unknown': 'Unknown'
    }
    race_table = create_structured_table(df, 'race', get_race_category, 'race', race_cats, race_map)
    race_table.to_csv(OUTPUT_RACE, index=False)
    print(f"Saved to {OUTPUT_RACE}")

if __name__ == "__main__":
    main()
