import numpy as np
import pandas as pd


def weighted_temporal_sampling(
        allocation: dict,
        samples_df: pd.DataFrame,
        weighting_strategy: str = "cases",
        case_incidence: dict = None,
        random_state: int = 42
    ) -> pd.DataFrame:
    """
    Perform temporal weighted sampling from `samples_df` given a target number for each deme,
    using one of two strategies:

      1) 'cases': weight = case_incidence[deme][time] / (# samples in that bin)
      2) 'even': weight = 1 / (# samples in that bin)
      3) 'samples': weight = 1

    Then we draw up to 'allocation[deme]' samples without replacement, with probability
    proportional to these weights.

    Parameters
    ----------
    allocation : dict
        A dictionary keyed by deme ID, where each value is an integer specifying how many
        samples we want to allocate (and hence draw) for that deme. e.g.:
        { 0: 50, 1: 30, 2: 20, ... }
    samples_df : pd.DataFrame
        A DataFrame of all candidate rows with columns ['sample_id', 'time', 'deme'].
        We will ignore samples whose deme is not in `allocation`.
    weighting_strategy : {'cases', 'even'}, optional; default='cases'
        - 'cases': weight = case_incidence[deme][time] / (# samples in that bin)
        - 'even': weight = 1 / (# samples in that bin)
        - 'samples': weight = 1
    case_incidence : dict
        Dictionary keyed by integer deme ID. Each value is a list of 
        length >= (max day + 1) giving daily incidence counts, e.g.:
        case_incidence[deme_id][time] => incidence for that deme and day.
        Each list is of the same length (outbreak duration), and the first day is 0.
    random_state : int, optional
        Seed for reproducible sampling. Default=42.
    
    Returns
    -------
    pd.DataFrame
        A DataFrame of the selected samples, up to `target_number` (or derived from
        `target_proportion`).

    Notes
    -----
    - If `allocation[deme]` is larger than the total number of available samples
      for that deme, we take all of them (no re‐allocation).
    - This approach is probabilistic when 'cases' or 'even' weighting is used; the actual
      number of picks per day may vary from run to run.
    - If a deme has zero incidence on all days but you still set a positive allocation,
      those samples will effectively get zero weights (unless you choose 'even').
    """

    # Check for case_incidence if needed
    if weighting_strategy == "cases" and case_incidence is None:
        raise ValueError("Must provide `case_incidence` when weighting_strategy='cases'.")

    # Filter samples_df to only those demes mentioned in allocation
    allocation = {int(deme): n for deme, n in allocation.items()}
    considered_demes = set(allocation.keys())
    working_df = samples_df[samples_df["deme"].isin(considered_demes)]

    # Convert deme keys in case_incidence to int if needed
    if case_incidence is not None:
        case_incidence = {int(deme): cases for deme, cases in case_incidence.items()}

    # Loop over the demes in the allocation dictionary
    selected_list = []
    for deme_id, target_n in allocation.items():
        if target_n <= 0:
            continue

        # Subset to just this deme
        deme_subset = working_df[working_df["deme"] == deme_id].copy()
        if deme_subset.empty:
            # If there are no samples for this deme, skip
            continue

        # Count how many samples each day has (for this deme)
        deme_subset["day_count"] = deme_subset.groupby("time")["time"].transform("count")

        if weighting_strategy == "cases":
            # case_incidence[deme_id][day] / bin_count
            def get_day_incidence(row):
                day = row["time"]
                return case_incidence[deme_id][day]

            deme_subset["deme_incidence"] = deme_subset.apply(get_day_incidence, axis=1)
            deme_subset["weight"] = deme_subset["deme_incidence"] / deme_subset["day_count"]

        elif weighting_strategy == "even":
            # 1 / bin_count
            deme_subset["weight"] = 1.0 / deme_subset["day_count"]

        elif weighting_strategy == "samples":
            # 1
            deme_subset["weight"] = 1.0

        # Sum of weights
        total_weight = deme_subset["weight"].sum()
        if total_weight == 0:
            continue

        # If target_n >= total available for that deme, take them all
        if target_n >= len(deme_subset):
            selected_samples = deme_subset
        else:
            # Weighted sampling without replacement
            selected_samples = deme_subset.sample(
                n=target_n,
                replace=False,
                weights="weight",
                random_state=random_state
            )
        
        selected_list.append(selected_samples)

    # Concatenate all selected samples
    if selected_list:
        final_samples = pd.concat(selected_list, ignore_index=True)
    else:
        final_samples = pd.DataFrame(columns=working_df.columns)

    return final_samples


def earliest_N_by_deme_sampling(
        allocation: dict,
        samples_df: pd.DataFrame,
        random_state: int = 42
    ) -> pd.DataFrame:
    """
    For each deme in `allocation`, collect its samples from earliest to latest
    (ascending time) until we reach the desired count. If a deme does not have enough
    samples, take all available.

    Parameters
    ----------
    allocation : dict
        A dictionary keyed by deme ID, where each value is an integer specifying how many
        samples we want to allocate (and hence draw) for that deme. e.g.:
        { 0: 50, 1: 30, 2: 20, ... }
    samples_df : pd.DataFrame
        A DataFrame of all candidate rows with columns ['sample_id', 'time', 'deme'].
        We will ignore samples whose deme is not in `allocation`.

    Returns
    -------
    pd.DataFrame
        A DataFrame of the selected samples, up to `target_number` (or derived from
        `target_proportion`).
    """

    # Filter samples_df to only those demes mentioned in allocation (first convert to integers)
    allocation = {int(deme): n for deme, n in allocation.items()}
    considered_demes = set(allocation.keys())
    working_df = samples_df[samples_df["deme"].isin(considered_demes)].copy()

    # Add a random column to shuffle within ties
    working_df["random"] = np.random.default_rng(random_state).random(size=len(working_df))

    # Sort by deme, time, and random (to break ties randomly)
    working_df.sort_values(by=["deme", "time", "random"], ascending=[True, True, True], inplace=True)
    working_df.drop(columns=["random"], inplace=True)

    # Loop over the demes in the allocation dictionary
    selected_list = []
    for deme_id, target_n in allocation.items():
        if target_n <= 0:
            continue

        # Subset to just this deme
        deme_subset = working_df[working_df["deme"] == deme_id]
        if deme_subset.empty:
            # If there are no samples for this deme, skip
            continue

        # If the deme has fewer samples than target_n, take them all
        if target_n >= len(deme_subset):
            selected_samples = deme_subset
        else:
            # Just take the earliest (by time) 'target_n' samples
            selected_samples = deme_subset.iloc[:target_n]

        selected_list.append(selected_samples)

    # Concatenate all selected samples
    if selected_list:
        final_samples = pd.concat(selected_list, ignore_index=True)
    else:
        final_samples = pd.DataFrame(columns=working_df.columns)

    return final_samples


def earliest_N_temporal_sampling(
        samples_df: pd.DataFrame,
        time_range: tuple = None,
        target_proportion: float = None,
        target_number: int = None,
        target_demes: list = None,
        random_state: int = 42
    ) -> pd.DataFrame:
    """
    Select up to a target number of samples (either from 'target_number' or derived
    from 'target_proportion') in ascending temporal order, from day=time_range[0]
    to day=time_range[1]. If adding all samples on a particular day would exceed
    the target, randomly choose only the needed subset from that day, and stop.

    Parameters
    ----------
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
        If provided, only rows whose 'deme' is in this list are considered.
    random_state : int, optional
        Seed for reproducible sampling. Default=42.

    Returns
    -------
    pd.DataFrame
        A DataFrame of the selected samples, up to `target_number` (or derived from
        `target_proportion`).
    """

    # Filter samples by samapling time if time_range is provided
    if time_range is not None:
        earliest_time, latest_time = time_range
        df = samples_df[(samples_df["time"] >= earliest_time) & (samples_df["time"] <= latest_time)]
    else:
        df = samples_df

    # Filter samples by target_demes if provided
    if target_demes is not None:
        df = df[df["deme"].isin(target_demes)]

    # If nothing left, return empty DataFrame
    if df.empty:
        return df

    # Determine the total available samples (post-filter)
    N = df.shape[0]

    # Determine final target_number if needed
    if target_proportion is not None and target_number is None:
        target_number = int(target_proportion * N)
    if target_number is None:
        raise ValueError("Either 'target_proportion' or 'target_number' must be specified.")

    # If N < target_number, take them all
    if N <= target_number:
        return df

    # Sort by time (ascending)
    df_sorted = df.sort_values(by="time", ascending=True).copy()
    df_sorted.reset_index(drop=True, inplace=True)
    
    # Collect earliest samples day by day until we reach target_number
    selected_list = []
    current_count = 0
    for day, day_group in df_sorted.groupby("time", sort=True):
        quota = target_number - current_count
        if quota <= 0:
            break

        if len(day_group) <= quota:
            # Take all from this day
            selected_list.append(day_group)
            current_count += len(day_group)
        else:
            # Randomly select only 'needed' from this day
            selected = day_group.sample(n=quota, random_state=random_state)
            selected_list.append(selected)
            current_count += quota
            break  # We've reached the target

    # Concatenate results
    final_df = pd.concat(selected_list, ignore_index=True) if selected_list else pd.DataFrame(columns=df.columns)
    
    return final_df