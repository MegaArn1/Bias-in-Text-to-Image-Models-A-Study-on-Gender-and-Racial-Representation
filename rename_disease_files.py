import os
import shutil

# Paths
base_path = "/home/ubuntu/personal_Profiles/day251024--bias/outputs/Kolors"
eng_path = os.path.join(base_path, "20251213_150334")
chi_path = os.path.join(base_path, "20251213_150414")

# Mapping (Chinese -> English)
mapping_raw = """
Hypertension	高血压
Type 1 diabetes	1型糖尿病
Type 2 diabetes	2型糖尿病
Preeclampsia	子痫前期
HIV	HIV
Tuberculosis	结核病
Sarcoidosis	肺结节病
Syphilis	梅毒
Prostate Cancer	前列腺癌
Lupus	红斑狼疮
Tricuspid Endocarditis	三尖瓣心内膜炎
Colon cancer	结肠癌
Bacterial Pneumonia	细菌性肺炎
Rheumatoid Arthritis	类风湿关节炎
Multiple Sclerosis	多发性硬化
Multiple Myeloma	多发性骨髓瘤
Takotsubo cardiomyopathy	Takotsubo 心肌病
Hepatitis B	乙型肝炎
COVID-19	COVID-19
Major Depressive Disorder	抑郁症
Huntington Disease	亨廷顿病
Amyotrophic Lateral Sclerosis	肌萎缩侧索硬化
"""

# Parse mapping
chi_to_eng = {}
for line in mapping_raw.strip().split('\n'):
    if not line.strip(): continue
    parts = line.split('\t')
    if len(parts) < 2: continue
    eng_name = parts[0].strip()
    chi_name = parts[1].strip()
    
    # Normalize English name: replace spaces and hyphens with underscores
    eng_name_normalized = eng_name.replace(' ', '_').replace('-', '_')
    
    # Store mapping
    chi_to_eng[chi_name] = eng_name_normalized
    # Handle potential space/underscore variations in Chinese folder names
    chi_to_eng[chi_name.replace(' ', '_')] = eng_name_normalized
    # Handle COVID-19 vs COVID_19 specific case
    if "COVID-19" in chi_name:
        chi_to_eng[chi_name.replace('-', '_')] = eng_name_normalized

def process_eng_folder():
    if not os.path.exists(eng_path):
        print(f"Path not found: {eng_path}")
        return

    print(f"Processing English folder: {eng_path}")
    for item in os.listdir(eng_path):
        item_path = os.path.join(eng_path, item)
        if os.path.isdir(item_path):
            disease_name = item
            # Skip if already renamed (contains _eng suffix) to avoid double processing if run multiple times
            if disease_name.endswith("_eng"):
                continue

            new_disease_name = disease_name + "_eng"
            new_item_path = os.path.join(eng_path, new_disease_name)
            
            # Rename files inside first
            for filename in os.listdir(item_path):
                if filename.endswith(".png"):
                    # Check if file is already renamed
                    if "_eng_" in filename:
                        continue
                        
                    if filename.startswith(disease_name):
                        # Replace the first occurrence of disease_name with new_disease_name
                        new_filename = filename.replace(disease_name, new_disease_name, 1)
                        old_file_path = os.path.join(item_path, filename)
                        new_file_path = os.path.join(item_path, new_filename)
                        os.rename(old_file_path, new_file_path)
                        print(f"Renamed file: {filename} -> {new_filename}")
            
            # Rename directory
            os.rename(item_path, new_item_path)
            print(f"Renamed folder: {disease_name} -> {new_disease_name}")

def process_chi_folder():
    if not os.path.exists(chi_path):
        print(f"Path not found: {chi_path}")
        return

    print(f"Processing Chinese folder: {chi_path}")
    for item in os.listdir(chi_path):
        item_path = os.path.join(chi_path, item)
        if os.path.isdir(item_path):
            chi_name = item
            
            # Skip if already processed (ends with _chi)
            if chi_name.endswith("_chi"):
                continue

            # Lookup English name
            eng_name = chi_to_eng.get(chi_name)
            
            # Fallback: try replacing underscores with spaces (e.g. Takotsubo_心肌病 -> Takotsubo 心肌病)
            if not eng_name:
                 eng_name = chi_to_eng.get(chi_name.replace('_', ' '))
            
            # Fallback: try replacing underscores with hyphens (e.g. COVID_19 -> COVID-19)
            if not eng_name:
                eng_name = chi_to_eng.get(chi_name.replace('_', '-'))

            if not eng_name:
                print(f"Warning: No mapping found for folder '{chi_name}', skipping.")
                continue
                
            new_folder_name = eng_name + "_chi"
            new_item_path = os.path.join(chi_path, new_folder_name)
            
            # Rename files inside
            for filename in os.listdir(item_path):
                if filename.endswith(".png"):
                    # Check if file is already renamed
                    if "_chi_" in filename:
                        continue

                    if filename.startswith(chi_name):
                        # Extract the suffix (e.g., _01.png)
                        suffix = filename[len(chi_name):]
                        new_filename = new_folder_name + suffix
                        
                        old_file_path = os.path.join(item_path, filename)
                        new_file_path = os.path.join(item_path, new_filename)
                        os.rename(old_file_path, new_file_path)
                        print(f"Renamed file: {filename} -> {new_filename}")
            
            # Rename directory
            os.rename(item_path, new_item_path)
            print(f"Renamed folder: {chi_name} -> {new_folder_name}")

if __name__ == "__main__":
    process_eng_folder()
    process_chi_folder()
