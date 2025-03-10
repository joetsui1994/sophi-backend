import numpy as np
import pandas as pd


def weighted_spatial_sampling(
        allocation: np.ndarray,
        samples_df: pd.DataFrame,
        case_incidence: dict = None,
        target_demes: list = None,
        population_sizes: dict = None,
        weighting_strategy: str = "cases",
        random_state: int = 42
    ) -> pd.DataFrame:
    """
    Perform spatial weighted sampling from `samples_df` given a target number for each day,
    using one of three strategies:

      1) 'cases': weight = case_incidence[deme][time] / (# samples in that bin)
      2) 'even': weight = 1 / (# samples in that bin)
      3) 'population': weight = population_sizes[deme] / (# samples in that bin)

    Then we draw up to 'day_allocation[day]' samples without replacement, with probability
    proportional to these weights.

    Parameters
    ----------
    allocation : np.ndarray
        A 1D array of length D. allocation[d] = total number of samples to draw on day d.
    samples_df : pd.DataFrame
        A DataFrame of all candidate rows with columns ['sample_id', 'time', 'deme'].
    case_incidence : dict, optional
        Dictionary keyed by integer deme ID. Each value is a list of 
        length >= (max day + 1) giving daily incidence counts, e.g.:
        case_incidence[deme_id][time] => incidence for that deme and day.
        Each list is of the same length (outbreak duration), and the first day is 0.
    target_demes : list, optional
        If provided, only rows whose 'deme' is in this list are considered. Otherwise,
        all demes in `samples_df`.
    population_sizes : dict, optional
        Dictionary keyed by integer deme ID. Each value is the population size for that deme.
        Required if weighting_strategy='population'.
    weighting_strategy : {'cases', 'even', 'population}, optional; default='cases'
        - 'cases': weight = case_incidence[deme][time] / (# samples in that bin)
        - 'even': weight = 1 / (# samples in that bin)
        - 'population': weight = population_sizes[deme] / (# samples in that bin)
    random_state : int, optional
        Seed for reproducible sampling. Default=42.

    Returns
    -------
    pd.DataFrame
        A DataFrame of the selected samples, up to `target_number` (or derived from
        `target_proportion`).
    
    Notes
    -----
    - If `allocation[d]` >= number of available samples (after filtering),
      all samples are taken for that day.
    - If weighting_strategy='cases' but a day's total incidence is 0 (or none 
      of the target demes have incidence for day d), then no samples will be 
      drawn for that day (unless `allocation[d]` is 0 anyway).
    """

    # Check for case_incidence if needed
    if weighting_strategy == "cases" and case_incidence is None:
        raise ValueError("Must provide `case_incidence` when weighting_strategy='cases'.")

    # Check for population_sizes if needed
    if weighting_strategy == "population" and population_sizes is None:
        raise ValueError("Must provide `population_sizes` when weighting_strategy='population'.")

    # Convert deme keys in case_incidence to int if needed
    if case_incidence is not None:
        case_incidence = {int(k): v for k, v in case_incidence.items()}

    # Convert deme keys in population_sizes to int if needed
    if population_sizes is not None:
        population_sizes = {int(k): v for k, v in population_sizes.items()}

    # Filter to target demes if provided
    if target_demes is not None:
        samples_df = samples_df[samples_df["deme"].isin(target_demes)]

    # Determine outbreak duration
    D = len(allocation)

    # Main loop over days
    selected_list = []
    for d in range(D):
        target_n = allocation[d]
        if target_n <= 0:
            continue

        # Subset to day d
        day_subset = samples_df[samples_df["time"] == d].copy()
        if day_subset.empty:
            continue

        # Group by deme to figure out how many samples each has
        day_subset["deme_count"] = day_subset.groupby("deme")["deme"].transform("count")

        # Compute the weight for each row, depending on weighting_strategy
        if weighting_strategy == "even":
            # 1 / bin_count
            day_subset["weight"] = 1.0 / day_subset["deme_count"]

        elif weighting_strategy == "cases":
            # case_incidence[deme_id][day] / bin_count
            def get_incidence(row):
                deme_id = row["deme"]
                return case_incidence[deme_id][d]

            # Incidence for each sample
            day_subset["deme_incidence"] = day_subset.apply(get_incidence, axis=1)

            # Weight per sample = incidence / number_of_samples_in_that_deme
            day_subset["weight"] = day_subset["deme_incidence"] / day_subset["deme_count"]

        elif weighting_strategy == "population":
            # population_sizes[deme_id] / bin_count
            def get_population(row):
                deme_id = row["deme"]
                return population_sizes[deme_id]
            
            # population for each sample
            day_subset["deme_population"] = day_subset.apply(get_population, axis=1)

            # Weight per sample = population / number_of_samples_in_that_deme
            day_subset["weight"] = day_subset["deme_population"] / day_subset["deme_count"]

        # Sum of weights
        total_weight = day_subset["weight"].sum()
        if total_weight == 0: # if no valid weights, return empty DataFrame
            continue

        # If allocation is >= total available, take them all
        if target_n >= len(day_subset):
            selected = day_subset
        else:
            # Weighted sampling without replacement
            selected = day_subset.sample(
                n=target_n,
                replace=False,
                weights="weight",
                random_state=random_state
            )
        
        selected_list.append(selected)

    # Concatenate all selected samples
    if selected_list:
        final_samples = pd.concat(selected_list, ignore_index=True)
    else:
        final_samples = pd.DataFrame(columns=samples_df.columns)

    return final_samples