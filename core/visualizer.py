import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os
import logging

# We set a nice clean look for our charts!
sns.set_theme(style="whitegrid")

def draw_peak_heatmap(data, title, x_label, y_label, day_names, cbar_label="Events", output_path="peak_heatmap.png"):
    """
    This function makes a cool 'heat map' that shows when the server is most busy during the week!
    """
    logging.info(f"Generating peak heatmap at {output_path}")
    # Convert string indices from SQLite strftime to integers
    df = pd.DataFrame(data, columns=['day', 'hour', 'count'])
    df['day'] = df['day'].astype(int)
    df['hour'] = df['hour'].astype(int)
    df['count'] = df['count'].astype(int)
    
    # We add up all the reactions and voice events so we can see the total activity!
    df = df.groupby(['day', 'hour'])['count'].sum().reset_index()
    
    # We make sure we have a spot for every hour of every day, even if no one was active then!
    full_index = pd.MultiIndex.from_product([range(7), range(24)], names=['day', 'hour'])
    df = df.set_index(['day', 'hour']).reindex(full_index, fill_value=0).reset_index()
    
    # Pivot for heatmap
    pivot = df.pivot(index='day', columns='hour', values='count')
    
    # We reorder the days so the week starts on Monday, which is much nicer to look at!
    mon_sun_indices = [1, 2, 3, 4, 5, 6, 0]
    pivot = pivot.reindex(mon_sun_indices)
    pivot.index = [day_names[i] for i in mon_sun_indices]

    plt.figure(figsize=(14, 7))
    # We use a bright and colorful map to show where the 'hot' spots are!
    sns.heatmap(pivot, annot=True, fmt="g", cmap="magma", cbar_kws={'label': cbar_label})
    
    plt.title(title, fontsize=16, pad=20)
    plt.xlabel(x_label, fontsize=12)
    plt.ylabel(y_label, fontsize=12)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    return output_path

def draw_voice_usage_bars(data, title, x_label, y_label, min_suffix="m", output_path="voice_bars.png"):
    """
    This makes a bar chart that shows which voice channels are the most popular!
    """
    if not data:
        return None
        
    logging.info(f"Generating voice usage bars at {output_path}")
    df = pd.DataFrame(data, columns=['channel', 'minutes'])
    df = df.sort_values(by='minutes', ascending=False)
    
    plt.figure(figsize=(12, 6))
    # We draw horizontal bars so the channel names are easy to read on the side.
    ax = sns.barplot(x='minutes', y='channel', data=df, palette='viridis')
    
    # We put the actual numbers at the end of each bar so they are easy to see!
    for p in ax.patches:
        width = p.get_width()
        plt.text(width + 1, p.get_y() + p.get_height()/2, f'{int(width)}{min_suffix}', ha='left', va='center')

    plt.title(title, fontsize=16, pad=20)
    plt.xlabel(x_label, fontsize=12)
    plt.ylabel(y_label, fontsize=12)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    return output_path

def draw_user_activity_chart(data, title, points_label="Points", voice_label="Voice Mins", y_points_label="Activity Points", y_voice_label="Voice Minutes", output_path="activity_chart.png"):
    """
    This makes a pretty line chart that shows your points and voice time for the last few days!
    """
    if not data:
        return None
        
    df = pd.DataFrame(data, columns=['date', 'points', 'voice'])
    # Convert date strings to short format (e.g. 03-31)
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%m-%d')
    
    plt.figure(figsize=(10, 4))
    
    # The blue line shows your activity points each day!
    color_points = "#3498db"
    ax1 = sns.lineplot(x='date', y='points', data=df, marker='o', color=color_points, linewidth=2.5, label=points_label)
    plt.fill_between(df['date'], df['points'], color=color_points, alpha=0.1)
    
    # The yellow dashed line shows how many minutes you spent in voice!
    ax2 = ax1.twinx()
    color_voice = "#f1c40f"
    sns.lineplot(x='date', y='voice', data=df, marker='s', color=color_voice, linewidth=1.5, ls='--', ax=ax2, label=voice_label)
    
    ax1.set_title(title, fontsize=14, pad=15)
    ax1.set_xlabel(None)
    ax1.set_ylabel(y_points_label, color=color_points, fontsize=10)
    ax2.set_ylabel(y_voice_label, color=color_voice, fontsize=10)
    
    # Grid and legend
    ax1.grid(True, alpha=0.3, ls=':')
    ax1.legend(loc='upper left')
    ax2.legend(loc='upper right')
    
    # Remove top spines
    sns.despine(top=True, right=False)
    
    try:
        plt.tight_layout()
        plt.savefig(output_path, dpi=120, transparent=False, facecolor='white')
        plt.close()
    except Exception as e:
        plt.close()
        raise RuntimeError(f"Matplotlib failed to save to {output_path}: {e}")
    return output_path
