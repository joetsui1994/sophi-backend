from scipy.stats import wasserstein_distance, pearsonr, spearmanr
import numpy as np


def compute_cumulative_area_diff(ts1, ts2):
    """
    Compute the area between the normalized cumulative distributions of two time series.

    Parameters:
        ts1 (array-like): First time series (e.g., counts over time).
        ts2 (array-like): Second time series.
        
    Returns:
        float: The sum of absolute differences between the cumulative distribution functions.
    """
    ts1 = np.asarray(ts1)
    ts2 = np.asarray(ts2)
    
    # Normalize the time series so they sum to 1.
    total1 = np.sum(ts1)
    total2 = np.sum(ts2)
    
    # Avoid division by zero by checking if the total is positive.
    ts1_norm = ts1 / total1 if total1 > 0 else ts1
    ts2_norm = ts2 / total2 if total2 > 0 else ts2
    
    # Compute cumulative sums to obtain the CDFs.
    cdf1 = np.cumsum(ts1_norm)
    cdf2 = np.cumsum(ts2_norm)
    
    # Compute the absolute differences at each time step and sum them up.
    area_diff = np.sum(np.abs(cdf1 - cdf2))
    
    return area_diff


def compute_wasserstein_distance(ts1, ts2):
    """
    Compute the Wasserstein distance between two time series.
    
    Here, we treat the time series as empirical distributions where the count at each 
    time step corresponds to the weight of that point. We assume the time points are 
    equally spaced and use their index positions as the "locations".
    
    Parameters:
        ts1 (array-like): First time series (e.g., counts over time).
        ts2 (array-like): Second time series.
        
    Returns:
        float: The Wasserstein distance between the two distributions.
    """
    ts1 = np.asarray(ts1)
    ts2 = np.asarray(ts2)
    
    # Create positions for each time step.
    positions = np.arange(len(ts1))
    
    # If both series are all zeros, return 0 as there is no difference.
    if np.sum(ts1) == 0 and np.sum(ts2) == 0:
        return 0.0
    
    # Compute the Wasserstein distance using the positions and weights (counts).
    wd = wasserstein_distance(u_values=positions, v_values=positions, 
                              u_weights=ts1, v_weights=ts2)
    
    return wd


def compute_correlations(ts1, ts2):
    """
    Compute the Pearson and Spearman correlation coefficients between two time series.

    Parameters:
        ts1 (array-like): First time series.
        ts2 (array-like): Second time series.
        
    Returns:
        dict: A dictionary containing Pearson and Spearman correlation coefficients and their p-values.
    """
    ts1 = np.asarray(ts1)
    ts2 = np.asarray(ts2)
    
    # Compute Pearson correlation coefficient and p-value.
    pearson_corr, pearson_p = pearsonr(ts1, ts2)
    
    # Compute Spearman correlation coefficient and p-value.
    spearman_corr, spearman_p = spearmanr(ts1, ts2)
    
    return {
        'pearson_correlation': pearson_corr,
        'pearson_p_value': pearson_p,
        'spearman_correlation': spearman_corr,
        'spearman_p_value': spearman_p
    }


def compute_cross_correlation(ts1, ts2):
    """
    Compute the cross-correlation of two time series and return the lag 
    corresponding to the maximum correlation, indicating the time shift.

    Parameters:
        ts1 (array-like): First time series.
        ts2 (array-like): Second time series.

    Returns:
        int: The lag (in time steps) corresponding to the maximum cross-correlation.
    """
    ts1 = np.asarray(ts1)
    ts2 = np.asarray(ts2)
    
    # Center the data by subtracting the mean.
    ts1_centered = ts1 - np.mean(ts1)
    ts2_centered = ts2 - np.mean(ts2)
    
    # Compute full cross-correlation.
    corr = np.correlate(ts1_centered, ts2_centered, mode='full')
    lags = np.arange(-len(ts1) + 1, len(ts1))
    
    # Find the lag where the correlation is maximized.
    max_corr_index = np.argmax(corr)
    time_shift = lags[max_corr_index]
    
    return time_shift, lags, corr