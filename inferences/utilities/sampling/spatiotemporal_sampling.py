import pandas as pd


def weighted_spatiotemporal_sampling(
        samples_df: pd.DataFrame,
        weighting_strategy: str = "cases",
        case_incidence: dict = None,
        time_range: tuple = None,
        target_proportion: float = None,
        target_number: int = None,
        target_demes: list = None,
        random_state: int = 42
    ) -> pd.DataFrame:
    """
    Perform a single-pass spatiotemporal weighted sampling from `samples_df`.
    Weight for each sample depends on (deme, time) using one of two strategies:

      1) 'cases': weight = case_incidence[deme][time] / (# samples in that bin)
      2) 'even': weight = 1 / (# samples in that bin)
      3) 'samples': weight = 1

    Then we draw up to 'target_number' samples without replacement, with probability
    proportional to these weights.

    Parameters
    ----------
    samples_df : pd.DataFrame
        A DataFrame of all candidate rows with columns ['sample_id', 'time', 'deme'].
    weighting_strategy : {'cases', 'even'}, optional; default='cases'
        - 'cases': weight = case_incidence[deme][time] / (# samples in that bin)
        - 'even': weight = 1 / (# samples in that bin)
        - 'samples': weight = 1
    case_incidence : dict
        Dictionary keyed by integer deme ID. Each value is a list of 
        length >= (max day + 1) giving daily incidence counts, e.g.:
        case_incidence[deme_id][time] => incidence for that deme and day.
        Each list is of the same length (outbreak duration), and the first day is 0.
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
    random_state : int, optional
        Seed for reproducible sampling. Default=42.

    Returns
    -------
    pd.DataFrame
        A DataFrame of the selected samples, up to `target_number` (or derived from
        `target_proportion`).
    """

    # Check for case_incidence if needed
    if weighting_strategy == "cases" and case_incidence is None:
        raise ValueError("Must provide `case_incidence` when weighting_strategy='cases'.")

    # Filter samples by target_demes if provided
    if target_demes is not None:
        df = samples_df[samples_df["deme"].isin(target_demes)].copy()
    else:
        df = samples_df.copy()

    # Filter by time_range if provided
    if time_range is not None:
        earliest_time, latest_time = time_range
        df = df[(df["time"] >= earliest_time) & (df["time"] <= latest_time)]
    
    # If nothing left, return empty DataFrame
    if df.empty:
        return df
    
    # Figure out target_number if needed
    total_filtered = len(df)
    if target_proportion is not None and target_number is None:
        target_number = int(target_proportion * total_filtered)
    if target_number is None:
        raise ValueError("Either 'target_proportion' or 'target_number' must be specified.")
    
    # If the request is >= total filtered, return everything
    if target_number >= total_filtered:
        return df

    # Convert deme keys in case_incidence to int if needed
    if case_incidence is not None:
        case_incidence = {int(k): v for k, v in case_incidence.items()}

    # Group by (deme, time) to find how many rows in each bin
    df["bin_count"] = df.groupby(["deme", "time"])["deme"].transform("count")

    # Compute each row's incidence-based or even-based weight
    def row_weight(row):
        # Incidence for (deme, time) if we have it
        deme_id = int(row["deme"])
        day = int(row["time"])

        if weighting_strategy == "cases":
            # case_incidence[deme_id][day] / bin_count
            inc = case_incidence[deme_id][day]
            return inc / row["bin_count"] if row["bin_count"] > 0 else 0.0

        elif weighting_strategy == "even":
            # 1 / bin_count
            return 1.0 / row["bin_count"] if row["bin_count"] > 0 else 0.0
        
        elif weighting_strategy == "samples":
            # 1
            return 1.0

    df["weight"] = df.apply(row_weight, axis=1)

    # Sum of weights
    total_weight = df["weight"].sum()
    if total_weight == 0: # if no valid weights, return empty DataFrame
        return df.iloc[0:0]

    # Sample without replacement
    selected_samples = df.sample(n=target_number, weights="weight", replace=False, random_state=random_state)

    return selected_samples


def stUC_draw(
        samples_df: pd.DataFrame,
        case_incidence: dict,
        time_range: tuple = None,
        target_proportion: float = None,
        target_number: int = None,
        target_demes: list = None,
        random_state: int = 42
    ) -> pd.DataFrame:

    samples_drawn_df = weighted_spatiotemporal_sampling(
        samples_df,
        weighting_strategy="cases",
        case_incidence=case_incidence,
        time_range=time_range,
        target_proportion=target_proportion,
        target_number=target_number,
        target_demes=target_demes,
        random_state=random_state
    )

    return samples_drawn_df


def stEV_draw(
        samples_df: pd.DataFrame,
        time_range: tuple = None,
        target_proportion: float = None,
        target_number: int = None,
        target_demes: list = None,
        random_state: int = 42
    ) -> pd.DataFrame:

    samples_drawn_df = weighted_spatiotemporal_sampling(
        samples_df,
        weighting_strategy="even",
        time_range=time_range,
        target_proportion=target_proportion,
        target_number=target_number,
        target_demes=target_demes,
        random_state=random_state
    )

    return samples_drawn_df


def stUS_draw(
        samples_df: pd.DataFrame,
        time_range: tuple = None,
        target_proportion: float = None,
        target_number: int = None,
        target_demes: list = None,
        random_state: int = 42
    ) -> pd.DataFrame:

    samples_drawn_df = weighted_spatiotemporal_sampling(
        samples_df,
        weighting_strategy="samples",
        time_range=time_range,
        target_proportion=target_proportion,
        target_number=target_number,
        target_demes=target_demes,
        random_state=random_state
    )

    return samples_drawn_df