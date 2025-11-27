# -*- coding: utf-8 -*-
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Set style for presentation
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 12
plt.rcParams['axes.labelsize'] = 14
plt.rcParams['axes.titlesize'] = 16
plt.rcParams['xtick.labelsize'] = 12
plt.rcParams['ytick.labelsize'] = 12
plt.rcParams['legend.fontsize'] = 12

# Load error data
print("Loading error data...")
nn_errors = pd.read_csv('nn_errors.csv')
rf_errors = pd.read_csv('rf_errors.csv')

print(f"Neural Network errors shape: {nn_errors.shape}")
print(f"Random Forest errors shape: {rf_errors.shape}")

# Calculate summary statistics
nn_stats = {
    'MAE': nn_errors['mae'].mean(),
    'RMSE': nn_errors['rmse'].mean(),
    'R²': nn_errors['r2'].mean() if 'r2' in nn_errors.columns else None
}

rf_stats = {
    'MAE': rf_errors['mae'].mean(),
    'RMSE': rf_errors['rmse'].mean(),
    'R²': rf_errors['r2'].mean() if 'r2' in rf_errors.columns else None
}

print("\n" + "="*60)
print("SUMMARY STATISTICS")
print("="*60)
print(f"\nNeural Network (GRU):")
print(f"  MAE:  {nn_stats['MAE']:.6f}")
print(f"  RMSE: {nn_stats['RMSE']:.6f}")
if nn_stats['R²'] is not None:
    print(f"  R²:   {nn_stats['R²']:.6f}")

print(f"\nRandom Forest:")
print(f"  MAE:  {rf_stats['MAE']:.6f}")
print(f"  RMSE: {rf_stats['RMSE']:.6f}")
if rf_stats['R²'] is not None:
    print(f"  R²:   {rf_stats['R²']:.6f}")

# Plot 1: Simple Bar Chart Comparison
fig1, ax1 = plt.subplots(figsize=(10, 6))
metrics = ['MAE', 'RMSE']
nn_values = [nn_stats['MAE'], nn_stats['RMSE']]
rf_values = [rf_stats['MAE'], rf_stats['RMSE']]

x = np.arange(len(metrics))
width = 0.35

bars1 = ax1.bar(x - width/2, nn_values, width, label='Neural Network', 
                color='#2E86AB', alpha=0.8, edgecolor='black', linewidth=1.5)
bars2 = ax1.bar(x + width/2, rf_values, width, label='Random Forest', 
                color='#A23B72', alpha=0.8, edgecolor='black', linewidth=1.5)

ax1.set_xlabel('Metric', fontweight='bold')
ax1.set_ylabel('Error Value', fontweight='bold')
ax1.set_title('Model Performance Comparison', fontweight='bold', pad=20)
ax1.set_xticks(x)
ax1.set_xticklabels(metrics)
ax1.legend(frameon=True, shadow=True)
ax1.grid(True, alpha=0.3, axis='y', linestyle='--')

# Add value labels on bars
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.4f}',
                ha='center', va='bottom', fontweight='bold', fontsize=11)

plt.tight_layout()
plt.savefig('comparison_metrics.png', dpi=300, bbox_inches='tight', facecolor='white')
print(f"\n✓ Saved 'comparison_metrics.png'")
plt.close()

# Plot 2: MAE Distribution Comparison
fig2, ax2 = plt.subplots(figsize=(10, 6))
ax2.hist(nn_errors['mae'], bins=40, alpha=0.7, label='Neural Network', 
         color='#2E86AB', edgecolor='black', linewidth=1)
ax2.hist(rf_errors['mae'], bins=40, alpha=0.7, label='Random Forest', 
         color='#A23B72', edgecolor='black', linewidth=1)
ax2.set_xlabel('Mean Absolute Error (MAE)', fontweight='bold')
ax2.set_ylabel('Frequency', fontweight='bold')
ax2.set_title('Error Distribution Comparison', fontweight='bold', pad=20)
ax2.legend(frameon=True, shadow=True)
ax2.grid(True, alpha=0.3, linestyle='--')
plt.tight_layout()
plt.savefig('comparison_distribution.png', dpi=300, bbox_inches='tight', facecolor='white')
print(f"✓ Saved 'comparison_distribution.png'")
plt.close()

# Plot 3: Box Plot Comparison
fig3, ax3 = plt.subplots(figsize=(10, 6))
data_to_plot = [nn_errors['mae'], rf_errors['mae']]
bp = ax3.boxplot(data_to_plot, labels=['Neural Network', 'Random Forest'],
                 patch_artist=True, widths=0.6,
                 medianprops=dict(color='red', linewidth=2),
                 boxprops=dict(facecolor='lightblue', edgecolor='black', linewidth=1.5),
                 whiskerprops=dict(color='black', linewidth=1.5),
                 capprops=dict(color='black', linewidth=1.5))

# Color the boxes differently
colors = ['#2E86AB', '#A23B72']
for patch, color in zip(bp['boxes'], colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)

# Add labels for the bottom whisker (minimum values - best case)
min_nn = nn_errors['mae'].min()
min_rf = rf_errors['mae'].min()
ax3.text(1, min_nn, f'Min: {min_nn:.4f}', ha='center', va='top', 
         fontweight='bold', fontsize=10, bbox=dict(boxstyle='round,pad=0.3', 
         facecolor='#2E86AB', alpha=0.7, edgecolor='black'))
ax3.text(2, min_rf, f'Min: {min_rf:.4f}', ha='center', va='top', 
         fontweight='bold', fontsize=10, bbox=dict(boxstyle='round,pad=0.3', 
         facecolor='#A23B72', alpha=0.7, edgecolor='black'))

ax3.set_ylabel('Mean Absolute Error (MAE)', fontweight='bold')
ax3.set_title('MAE Distribution by Model', fontweight='bold', pad=20)
ax3.grid(True, alpha=0.3, axis='y', linestyle='--')
plt.tight_layout()
plt.savefig('comparison_boxplot.png', dpi=300, bbox_inches='tight', facecolor='white')
print(f"✓ Saved 'comparison_boxplot.png'")
plt.close()

# Plot 4: Performance Improvement
fig4, ax4 = plt.subplots(figsize=(10, 6))
improvements = {
    'MAE': ((rf_stats['MAE'] - nn_stats['MAE']) / nn_stats['MAE'] * 100),
    'RMSE': ((rf_stats['RMSE'] - nn_stats['RMSE']) / nn_stats['RMSE'] * 100)
}

metrics_names = list(improvements.keys())
improvement_values = list(improvements.values())
colors_imp = ['#DC3545' if v < 0 else '#28A745' for v in improvement_values]

bars = ax4.barh(metrics_names, improvement_values, color=colors_imp, 
                alpha=0.8, edgecolor='black', linewidth=1.5)
ax4.set_xlabel('Random Forest Error vs Neural Network (%)', fontweight='bold')
ax4.set_title('How much worse is Random Forest?\n(Positive = RF has higher error, Negative = RF has lower error)', 
              fontweight='bold', pad=20)
ax4.axvline(x=0, color='black', linestyle='-', linewidth=2)
ax4.grid(True, alpha=0.3, axis='x', linestyle='--')

# Add value labels
for bar, val in zip(bars, improvement_values):
    label_x = val + (2 if val > 0 else -2)
    ax4.text(label_x, bar.get_y() + bar.get_height()/2,
            f'{val:.2f}%',
            ha='left' if val > 0 else 'right',
            va='center',
            fontweight='bold', fontsize=12)

plt.tight_layout()
plt.savefig('comparison_improvement.png', dpi=300, bbox_inches='tight', facecolor='white')
print(f"✓ Saved 'comparison_improvement.png'")
plt.close()

# Print comparison summary
print("\n" + "="*60)
print("PERFORMANCE COMPARISON")
print("="*60)
for metric, improvement in improvements.items():
    if improvement > 0:
        print(f"{metric}: Random Forest error is {improvement:.2f}% HIGHER (worse)")
    else:
        print(f"{metric}: Random Forest error is {abs(improvement):.2f}% LOWER (better)")

print("\n✓ Analysis complete! Generated 4 presentation-ready plots:")
print("  - comparison_metrics.png (Bar chart)")
print("  - comparison_distribution.png (Histogram)")
print("  - comparison_boxplot.png (Box plot)")
print("  - comparison_improvement.png (Improvement %)")

