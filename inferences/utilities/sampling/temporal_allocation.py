import pandas as pd
import numpy as np


def uniform_sample_temporal_allocation(
        case_incidence: dict,
        samples_df: pd.DataFrame,
        time_range: tuple = None,
        target_proportion: float = None,
        target_number: int = None,
        target_demes: list = None
    ) -> list:
    """
    Allocate daily sample counts in proportion to the total daily number
    of samples (across specified `target_demes`), restricting to a time window
    [earliest_time, latest_time].

    Parameters
    ----------
    case_incidence : dict
        Dictionary keyed by integer deme ID. Each value is a list of 
        length >= (max day + 1) giving daily incidence counts, e.g.:
        case_incidence[deme_id][time] => incidence for that deme and day.
        Each list is of the same length (outbreak duration), and the first day is 0.
    samples_df : pd.DataFrame
        A DataFrame of all candidate rows with columns ['sample_id', 'time', 'deme'].
    time_range : tuple(int, int), optional
        If provided, only rows with earliest_time <= time <= latest_time are considered.
        If None, we consider all times present in the data.
    target_proportion : float, optional
        Fraction of the total filtered rows we want to sample, if `target_number` is None.
    target_number : int, optional
        Desired number of rows to sample. If both are provided and `target_number` is None,
        we use `target_proportion`.
    target_demes : list, optional
        If provided, only rows whose 'deme' is in this list are considered. Otherwise,
        all demes in `samples_df`.

    Returns
    -------
    np.ndarray
        An integer array of length D (the full outbreak duration). Days outside
        the chosen `time_range` (if specified) are zero.
    """

    # Convert keys in case_incidence to int if needed (to stay consistent)
    case_incidence = {int(deme): cases for deme, cases in case_incidence.items()}

    # Determine the number of days (assuming uniform length)
    D = len(next(iter(case_incidence.values())))

    # If no target_demes specified, consider them all
    if target_demes is None:
        target_demes = list(case_incidence.keys())

    # Filter incidence to target demes
    target_case_incidence = {deme: case_incidence[deme] for deme in target_demes if deme in case_incidence}

    # If no target demes or empty incidence, return empty or zero allocations
    if not target_case_incidence:
        return np.zeros(D, dtype=int)

    # Filter samples by target_demes if provided
    df = samples_df[samples_df["deme"].isin(target_demes)]

    # If time_range is None, use the entire range [0..D-1]
    if time_range is None:
        earliest_time, latest_time = 0, D - 1
    else:
        earliest_time, latest_time = time_range

    # Filter samples by sampling time
    df = df[(df["time"] >= earliest_time) & (df["time"] <= latest_time)]

    # Number of total samples available, given the filters
    N = df.shape[0]
    if N == 0:
        return np.zeros(D, dtype=int)

    # Determine final target_number if needed
    if target_proportion is not None and target_number is None:
        target_number = int(target_proportion * N)
    if target_number is None:
        raise ValueError("Either 'target_proportion' or 'target_number' must be specified.")

    # Compute daily subrange total samples
    daily_sub_samples = np.zeros(D, dtype=float)
    for time, group in df.groupby("time"):
        daily_sub_samples[time] = group.shape[0]

    # Compute total samples across target demes
    total_sub_samples = daily_sub_samples.sum()

    # If total samples for this subrange is 0, the subrange gets all zeros
    if total_sub_samples == 0:
        return np.zeros(D, dtype=int)
    
    # Compute proportional subrange allocation
    frac_subrange = daily_sub_samples / total_sub_samples
    day_alloc_sub = np.round(frac_subrange * target_number).astype(int)

    # Create a full array of length D, fill subrange, zeros outside
    full_allocation = np.zeros(D, dtype=int)
    full_allocation[earliest_time:latest_time + 1] = day_alloc_sub

    return full_allocation
    

def uniform_case_temporal_allocation(
        case_incidence: dict,
        samples_df: pd.DataFrame,
        time_range: tuple = None,
        target_proportion: float = None,
        target_number: int = None,
        min_number_per_day: int = 0,
        target_demes: list = None
    ) -> list:
    """
    Allocate daily sample counts in proportion to the total daily incidence 
    (across specified `target_demes`), restricting to a time window 
    [earliest_time, latest_time].

    Parameters
    ----------
    case_incidence : dict
        Dictionary keyed by integer deme ID. Each value is a list of 
        length >= (max day + 1) giving daily incidence counts, e.g.:
        case_incidence[deme_id][time] => incidence for that deme and day.
        Each list is of the same length (outbreak duration), and the first day is 0.
    samples_df : pd.DataFrame
        A DataFrame of all candidate rows with columns ['sample_id', 'time', 'deme'].
    time_range : tuple(int, int), optional
        If provided, only rows with earliest_time <= time <= latest_time are considered.
        If None, we consider all times present in the data.
    target_proportion : float, optional
        Fraction of the total filtered rows we want to sample, if `target_number` is None.
    target_number : int, optional
        Desired number of rows to sample. If both are provided and `target_number` is None,
        we use `target_proportion`.
    min_number_per_day : int, optional
        Minimum number of samples allocated per day (applied after rounding).
    target_demes : list, optional
        If provided, only rows whose 'deme' is in this list are considered. Otherwise,
        all demes in `case_incidence`.

    Returns
    -------
    np.ndarray
        An integer array of length D (the full outbreak duration). Days outside 
        the chosen `time_range` (if specified) are zero.
    """

    # Convert keys in case_incidence to int if needed (to stay consistent)
    case_incidence = {int(deme): cases for deme, cases in case_incidence.items()}

    # Determine the number of days (assuming uniform length)
    D = len(next(iter(case_incidence.values())))

    # If no target_demes specified, consider them all
    if target_demes is None:
        target_demes = list(case_incidence.keys())

    # Filter incidence to target demes
    target_case_incidence = {deme: case_incidence[deme] for deme in target_demes if deme in case_incidence}

    # If no target demes or empty incidence, return empty or zero allocations
    if not target_case_incidence:
        return np.zeros(D, dtype=int)

    # Filter samples by target_demes if provided
    df = samples_df[samples_df["deme"].isin(target_demes)]

    # If time_range is None, use the entire range [0..D-1]
    if time_range is None:
        earliest_time, latest_time = 0, D - 1
    else:
        earliest_time, latest_time = time_range

    # Filter samples by sampling time
    df = df[(df["time"] >= earliest_time) & (df["time"] <= latest_time)]

    # Number of total samples available, given the filters
    N = df.shape[0]
    if N == 0:
        return np.zeros(D, dtype=int)

    # Build subrange for incidence: earliest_time..latest_time
    subrange_length = latest_time - earliest_time + 1

    # Compute daily subrange total incidence
    daily_sub_incidence = np.zeros(subrange_length, dtype=float)
    for deme_cases in target_case_incidence.values():
        slice_ = deme_cases[earliest_time:latest_time + 1]
        daily_sub_incidence += np.array(slice_, dtype=float)

    # Compute total incidence across target demes
    total_sub_incidence = daily_sub_incidence.sum()

    # If total incidence for this subrange is 0, the subrange gets all zeros
    if total_sub_incidence == 0:
        return np.zeros(D, dtype=int)

    # Determine final target_number if needed
    if target_proportion is not None and target_number is None:
        target_number = int(target_proportion * N)
    if target_number is None:
        raise ValueError("Either 'target_proportion' or 'target_number' must be specified.")

    # Compute proportional subrange allocation
    frac_subrange = daily_sub_incidence / total_sub_incidence
    day_alloc_sub = np.round(frac_subrange * target_number).astype(int)

    # Enforce minimum per day (only in the selected subrange)
    if min_number_per_day > 0:
        day_alloc_sub = np.maximum(day_alloc_sub, min_number_per_day)

    # Create a full array of length D, fill subrange, zeros outside
    full_allocation = np.zeros(D, dtype=int)
    full_allocation[earliest_time:latest_time + 1] = day_alloc_sub

    return full_allocation


def even_temporal_allocation(
        case_incidence: dict,
        samples_df: pd.DataFrame,
        time_range: tuple = None,
        target_proportion: float = None,
        target_number: int = None,
        min_number_per_day: int = 0,
        target_demes: list = None
    ) -> np.ndarray:
    """
    Allocate daily sample counts evenly (across specified `target_demes`),
    restricting to a time window [earliest_time, latest_time].
    Each day receives approximately the same number of samples.

    Parameters
    ----------
    case_incidence : dict
        Dictionary keyed by integer deme ID. Each value is a list of 
        length >= (max day + 1) giving daily incidence counts, e.g.:
        case_incidence[deme_id][time] => incidence for that deme and day.
        Each list is of the same length (outbreak duration), and the first day is 0.
    samples_df : pd.DataFrame
        A DataFrame of all candidate rows with columns ['sample_id', 'time', 'deme'].
    time_range : tuple(int, int), optional
        A tuple `(earliest_time, latest_time)`. Samples are allocated evenly over 
        `[earliest_time..latest_time]`. Days outside this range receive zero.
        If `None`, the entire range `[0..D-1]` is used.
    time_range : tuple(int, int), optional
        If provided, only rows with earliest_time <= time <= latest_time are considered.
        If None, we consider all times present in the data.
    target_proportion : float, optional
        Fraction of the total filtered rows we want to sample, if `target_number` is None.
    target_number : int, optional
        Desired number of rows to sample. If both are provided and `target_number` is None,
        we use `target_proportion`.
    min_number_per_day : int, optional
        Minimum number of samples allocated per day (applied after rounding).
    target_demes : list, optional
        If provided, only rows whose 'deme' is in this list are considered. Otherwise,
        all demes in `case_incidence`.

    Returns
    -------
    np.ndarray
        An integer array of length D (the full outbreak duration). Days outside 
        the chosen `time_range` (if specified) are zero.

    Notes
    -----
    - If the total incidence is zero (across `target_demes`), this returns zeros
      for all days, just like the proportional function.
    - Because we split `target_number` evenly, the sum of the final daily allocations
      might not exactly equal `target_number` if `min_number_per_day` pushes the
      total above it, or due to rounding.
    """

    # Convert keys in case_incidence to int if needed (to stay consistent)
    case_incidence = {int(deme): cases for deme, cases in case_incidence.items()}

    # If no target_demes specified, consider them all
    if target_demes is None:
        target_demes = list(case_incidence.keys())

    # Filter incidence to target demes
    target_case_incidence = {deme: case_incidence[deme] for deme in target_demes if deme in case_incidence}

    # Determine the number of days (assuming uniform length)
    D = len(next(iter(target_case_incidence.values())))

  # If no target demes or empty incidence, return empty or zero allocations
    if not target_case_incidence:
        return np.zeros(D, dtype=int)

    # Filter samples by target_demes if provided
    df = samples_df[samples_df["deme"].isin(target_demes)]

    # If time_range is None, use the entire range [0..D-1]
    if time_range is None:
        earliest_time, latest_time = 0, D - 1
    else:
        earliest_time, latest_time = time_range

    # Filter samples by sampling time
    df = df[(df["time"] >= earliest_time) & (df["time"] <= latest_time)]

    # Number of total samples available, given the filters
    N = df.shape[0]
    if N == 0:
        return np.zeros(D, dtype=int)

    # Build subrange for incidence: earliest_time..latest_time
    subrange_length = latest_time - earliest_time + 1

    # Compute daily subrange total incidence
    daily_sub_incidence = np.zeros(subrange_length, dtype=float)
    for deme_cases in target_case_incidence.values():
        slice_ = deme_cases[earliest_time:latest_time + 1]
        daily_sub_incidence += np.array(slice_, dtype=float)

    # Compute total incidence across target demes
    total_sub_incidence = daily_sub_incidence.sum()

    # If total incidence for this subrange is 0, the subrange gets all zeros
    if total_sub_incidence == 0:
        return np.zeros(D, dtype=int)

    # Determine final target_number if needed
    if target_proportion is not None and target_number is None:
        target_number = int(target_proportion * N)
    if target_number is None:
        raise ValueError("Either 'target_proportion' or 'target_number' must be specified.")

    # Create a full allocation array of length D (initialized to 0)
    full_allocation = np.zeros(D, dtype=int)

    # Evenly distribute among [earliest_time..latest_time]
    per_day_float = target_number / subrange_length
    day_alloc_floats = np.full(subrange_length, per_day_float)
    day_allocation_int = np.round(day_alloc_floats).astype(int)

    # Enforce minimum per day (only in the selected subrange)
    if min_number_per_day > 0:
        day_allocation_int = np.maximum(day_allocation_int, min_number_per_day)

    # Create a full array of length D, fill subrange, zeros outside
    full_allocation = np.zeros(D, dtype=int)
    full_allocation[earliest_time:latest_time + 1] = day_allocation_int

    return full_allocation