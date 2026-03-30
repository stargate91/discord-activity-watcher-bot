import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os

# Set a clean style for charts
sns.set_theme(style="whitegrid")

def draw_peak_heatmap(data, title, x_label, y_label, day_names, output_path="peak_heatmap.png"):
    """
    Creates a heatmap showing server activity by day of week and hour of day.
    data: list of tuples (day_index_str, hour_index_str, count)
    day_names: list of day names starting from Sunday (0) to Saturday (6)
    """
    # Convert string indices from SQLite strftime to integers
    df = pd.DataFrame(data, columns=['day', 'hour', 'count'])
    df['day'] = df['day'].astype(int)
    df['hour'] = df['hour'].astype(int)
    df['count'] = df['count'].astype(int)
    
    # Aggregate counts (reactions + voice start events)
    df = df.groupby(['day', 'hour'])['count'].sum().reset_index()
    
    # Ensure all 24x7 slots exist
    full_index = pd.MultiIndex.from_product([range(7), range(24)], names=['day', 'hour'])
    df = df.set_index(['day', 'hour']).reindex(full_index, fill_value=0).reset_index()
    
    # Pivot for heatmap
    pivot = df.pivot(index='day', columns='hour', values='count')
    
    # Reorder to Mon (1) -> Sun (0)
    mon_sun_indices = [1, 2, 3, 4, 5, 6, 0]
    pivot = pivot.reindex(mon_sun_indices)
    pivot.index = [day_names[i] for i in mon_sun_indices]

    plt.figure(figsize=(14, 7))
    # Use a vibrant color map (magma or YlGnBu)
    sns.heatmap(pivot, annot=True, fmt="g", cmap="magma", cbar_kws={'label': 'Events'})
    
    plt.title(title, fontsize=16, pad=20)
    plt.xlabel(x_label, fontsize=12)
    plt.ylabel(y_label, fontsize=12)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    return output_path

def draw_voice_usage_bars(data, title, x_label, y_label, output_path="voice_bars.png"):
    """
    Creates a bar chart showing voice usage duration per channel.
    data: list of tuples (channel_name, minutes)
    """
    if not data:
        return None
        
    df = pd.DataFrame(data, columns=['channel', 'minutes'])
    df = df.sort_values(by='minutes', ascending=False)
    
    plt.figure(figsize=(12, 6))
    # Create horizontal bar chart
    ax = sns.barplot(x='minutes', y='channel', data=df, palette='viridis')
    
    # Add values at the end of bars
    for p in ax.patches:
        width = p.get_width()
        plt.text(width + 1, p.get_y() + p.get_height()/2, f'{int(width)}m', ha='left', va='center')

    plt.title(title, fontsize=16, pad=20)
    plt.xlabel(x_label, fontsize=12)
    plt.ylabel(y_label, fontsize=12)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    return output_path
