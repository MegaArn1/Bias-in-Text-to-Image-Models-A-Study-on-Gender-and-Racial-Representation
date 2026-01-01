import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
import numpy as np

# Configuration
INPUT_RACE = Path("demographics_status_race_1.csv")
INPUT_GENDER = Path("demographics_status_gender_1.csv")
OUTPUT_RACE_IMG_CHI = Path("heatmap_race_chi.png")
OUTPUT_RACE_IMG_ENG = Path("heatmap_race_eng.png")
OUTPUT_GENDER_IMG_CHI = Path("heatmap_gender_chi.png")
OUTPUT_GENDER_IMG_ENG = Path("heatmap_gender_eng.png")

# Plotting Configuration
FIG_SIZE_RACE = (24, 12)
FIG_SIZE_GENDER = (18, 12)
CMAP = "YlGnBu" # Yellow to Blue

def parse_model_columns(df, lang_filter=None):
    """Identify model percentage columns, optionally filtered by language."""
    # Columns ending with _p are percentages
    # e.g. flux_eng_p
    cols = [c for c in df.columns if c.endswith('_p')]
    
    if lang_filter:
        # Filter for specific language (e.g., '_chi_p' or '_eng_p')
        suffix = f"_{lang_filter}_p"
        cols = [c for c in cols if c.endswith(suffix)]
        
    return cols

def format_model_name(col_name):
    """Convert 'flux_eng_p' to 'Flux' (since lang is separate now)"""
    # Remove _p
    base = col_name[:-2]
    # Split by last underscore to separate lang
    parts = base.split('_')
    # lang = parts[-1] # Not needed for display if we separate plots
    model = "_".join(parts[:-1])
    
    # Capitalize
    model_display = model.replace("stable_diffusion_3.5_large_turbo", "SD").replace("Qwen-Image", "Qwen")
    
    return model_display

def plot_heatmap(df, category_col, categories, output_path, figsize, lang_filter):
    if not df_exists(df):
        return

    # Prepare data for heatmap
    # We want a DataFrame where:
    # Index = Disease
    # Columns = MultiIndex (Category, Source)
    
    heatmap_data = pd.DataFrame()
    
    # Define sources order: Real World, then Models
    model_cols = parse_model_columns(df, lang_filter)
    # Sort model cols if needed, or keep as is
    model_cols.sort()
    
    # Build the matrix
    # We iterate through categories and build columns
    
    dfs_to_concat = []
    
    # Store locations of "Real World" columns for highlighting
    rw_col_indices = []
    current_col_idx = 0
    
    # Categories to display
    # Filter categories that exist in data
    available_cats = df[category_col].unique()
    cats_to_plot = [c for c in categories if c in available_cats]
    
    # Create a list of (Category, Source, Series)
    
    for cat in cats_to_plot:
        cat_df = df[df[category_col] == cat].set_index('disease')
        
        # Real World
        rw_series = cat_df['realworld_distribution']
        rw_series.name = (cat, "True prevalence")
        dfs_to_concat.append(rw_series)
        
        # Mark this column index for highlighting
        rw_col_indices.append(current_col_idx)
        current_col_idx += 1
        
        # Models
        for m_col in model_cols:
            m_series = cat_df[m_col]
            m_name = format_model_name(m_col)
            m_series.name = (cat, m_name)
            dfs_to_concat.append(m_series)
            current_col_idx += 1
            
    if not dfs_to_concat:
        print(f"No data to plot for {output_path}")
        return

    heatmap_df = pd.concat(dfs_to_concat, axis=1)
    
    # Handle NaN
    heatmap_df = heatmap_df.fillna(0)
    
    # Plotting
    plt.figure(figsize=figsize)
    
    # Create annotation matrix (formatted strings)
    annot_df = heatmap_df.applymap(lambda x: f"{x:.1f}" if pd.notnull(x) else "N/A")
    
    # Create heatmap
    # We use the raw values for color mapping
    ax = sns.heatmap(heatmap_df, annot=annot_df, fmt="", cmap=CMAP, 
                     cbar_kws={'label': 'Proportion (%)'},
                     linewidths=0.5, linecolor='white')
    
    # Customize X-axis labels
    # The columns are MultiIndex (Category, Source)
    # We want to show Source at the bottom, and Category at the top
    
    # Current x-labels are tuples like ('White', 'True prevalence')
    # We can set the labels to just the Source part
    x_labels = [label[1] for label in heatmap_df.columns]
    ax.set_xticklabels(x_labels, rotation=45, ha="right")
    ax.set_xlabel("Data source/Model name", fontsize=14, fontweight='bold')
    
    # Add Category Group Labels on top
    # We need to draw text or lines
    # Calculate positions
    # Each category has (1 + num_models) columns
    num_models = len(model_cols)
    cols_per_cat = 1 + num_models
    
    # Get the axis width in data coordinates
    # x limits are (0, total_cols)
    
    # Add group labels
    ax_top = ax.twiny()
    ax_top.set_xlim(ax.get_xlim())
    ax_top.set_xticks([]) # Hide ticks
    
    # Draw text for categories
    for i, cat in enumerate(cats_to_plot):
        # Center of the group
        # Start index = i * cols_per_cat
        # End index = (i + 1) * cols_per_cat
        # Center = Start + cols_per_cat / 2
        start = i * cols_per_cat
        center = start + cols_per_cat / 2
        
        # Use ax_top to place text at the top
        # y=1.01 is slightly above the top spine
        ax_top.text(center, 1.01, f"{cat} group", 
                 transform=ax_top.get_xaxis_transform(),
                 ha='center', va='bottom', fontweight='bold', fontsize=14)
        
        # Optional: Add vertical lines to separate groups

        if i > 0:
            ax.vlines(start, *ax.get_ylim(), colors='black', linewidth=2)

    # Highlight Real World columns with red rectangles
    # rw_col_indices contains the x-indices (0, cols_per_cat, ...)
    # We need to draw a rectangle for the full height
    ylim = ax.get_ylim() # (n_diseases, 0) usually
    height = abs(ylim[0] - ylim[1])
    
    for x_idx in rw_col_indices:
        # Create a Rectangle patch
        # (x, y), width, height
        # x is x_idx
        # y is 0 (top) or max (bottom)? Heatmap coords: y=0 is top row usually?
        # Actually seaborn heatmap y-axis goes from 0 to N.
        # We want to cover x_idx to x_idx+1
        rect = patches.Rectangle((x_idx, 0), 1, height, linewidth=3, edgecolor='red', facecolor='none')
        ax.add_patch(rect)

    lang_title = "Chinese Prompts" if lang_filter == "chi" else "English Prompts"
    plt.title(f"Demographic Distribution Analysis ({category_col.capitalize()}) - {lang_title}", pad=40, fontsize=16)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved heatmap to {output_path}")
    plt.close()

def df_exists(df):
    return df is not None and not df.empty

def main():
    # Load Race Data
    if INPUT_RACE.exists():
        print(f"Loading {INPUT_RACE}...")
        df_race = pd.read_csv(INPUT_RACE)
        # Categories order
        race_cats = ['White', 'Black', 'Asian', 'Hispanic/Latino', 'Unknown']
        plot_heatmap(df_race, 'race', race_cats, OUTPUT_RACE_IMG_CHI, FIG_SIZE_RACE, 'chi')
        plot_heatmap(df_race, 'race', race_cats, OUTPUT_RACE_IMG_ENG, FIG_SIZE_RACE, 'eng')
    else:
        print(f"File not found: {INPUT_RACE}")

    # Load Gender Data
    if INPUT_GENDER.exists():
        print(f"Loading {INPUT_GENDER}...")
        df_gender = pd.read_csv(INPUT_GENDER)
        # Categories order
        gender_cats = ['Male', 'Female', 'Unknown']
        plot_heatmap(df_gender, 'gender', gender_cats, OUTPUT_GENDER_IMG_CHI, FIG_SIZE_GENDER, 'chi')
        plot_heatmap(df_gender, 'gender', gender_cats, OUTPUT_GENDER_IMG_ENG, FIG_SIZE_GENDER, 'eng')
    else:
        print(f"File not found: {INPUT_GENDER}")

if __name__ == "__main__":
    main()
