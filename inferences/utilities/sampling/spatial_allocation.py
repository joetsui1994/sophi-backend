import pandas as pd
import numpy as np


def uniform_sample_spatial_allocation(
        case_incidence: dict,
        samples_df: pd.DataFrame,
        target_proportion: float = None,
        target_number: int = None,
        min_number_per_deme: int = 0,
        target_demes: list = None
    ) -> dict:
    """
    Allocate a target number (or proportion) of samples to be drawn from each deme in proportion to
    its total number of samples available across the outbreak.

    Parameters
    ----------
    case_incidence : dict
        Dictionary keyed by integer deme ID. Each value is a list of 
        length >= (max day + 1) giving daily incidence counts, e.g.:
        case_incidence[deme_id][time] => incidence for that deme and day.
        Each list is of the same length (outbreak duration), and the first day is 0.
    samples_df : pd.DataFrame
        A DataFrame of all candidate rows with columns ['sample_id', 'time', 'deme'].
    target_proportion : float, optional
        Fraction of the total filtered rows we want to sample, if `target_number` is None.
    target_number : int, optional
        Desired number of rows to sample. If both are provided and `target_number` is None,
        we use `target_proportion`.
    min_number_per_deme : int, optional
        Minimum number of samples allocated to each deme (applied after rounding).
    target_demes : list, optional
        If provided, only rows whose 'deme' is in this list are considered. Otherwise,
        all demes in `case_incidence`.

    Returns
    -------
    dict
        A dictionary keyed by deme ID, indicating the number of samples allocated 
        to each.
    """

    # Convert deme keys in case_incidence to int if needed
    case_incidence = {int(k): v for k, v in case_incidence.items()}

    # Determine which demes to consider
    if target_demes is None:
        target_demes = list(case_incidence.keys())

    # Filter samples by target_demes if provided
    df = samples_df[samples_df["deme"].isin(target_demes)]

    # Number of total samples available, given the filters
    N = df.shape[0]
    if N == 0:
        return {deme: 0 for deme in target_demes}
    
    # Get number of samples available in each deme
    deme_counts = df["deme"].value_counts().to_dict()

    # Determine final target_number if needed
    if target_proportion is not None and target_number is None:
        target_number = int(target_proportion * N)
    if target_number is None:
        raise ValueError("Either 'target_proportion' or 'target_number' must be specified.")

    # Compute allocations in proportion to each deme's share of total samples
    allocated = {}
    for deme in target_demes:
        deme_alloc_float = (deme_counts.get(deme, 0) / N) * target_number
        allocated[deme] = int(round(deme_alloc_float))

    # Enforce a minimum number per deme if requested
    if min_number_per_deme > 0:
        for deme in allocated:
            if allocated[deme] < min_number_per_deme:
                allocated[deme] = min_number_per_deme

    return allocated


def uniform_case_spatial_allocation(
        case_incidence: dict,
        samples_df: pd.DataFrame,
        target_proportion: float = None,
        target_number: int = None,
        min_number_per_deme: int = 0,
        target_demes: list = None
    ) -> dict:
    """
    Allocate a target number (or proportion) of samples to be drawn from each deme in proportion to
    its total incidence across the outbreak.

    Parameters
    ----------
    case_incidence : dict
        Dictionary keyed by integer deme ID. Each value is a list of 
        length >= (max day + 1) giving daily incidence counts, e.g.:
        case_incidence[deme_id][time] => incidence for that deme and day.
        Each list is of the same length (outbreak duration), and the first day is 0.
    samples_df : pd.DataFrame
        A DataFrame of all candidate rows with columns ['sample_id', 'time', 'deme'].
    target_proportion : float, optional
        Fraction of the total filtered rows we want to sample, if `target_number` is None.
    target_number : int, optional
        Desired number of rows to sample. If both are provided and `target_number` is None,
        we use `target_proportion`.
    min_number_per_deme : int, optional
        Minimum number of samples allocated to each deme (applied after rounding).
    target_demes : list, optional
        If provided, only rows whose 'deme' is in this list are considered. Otherwise,
        all demes in `case_incidence`.

    Returns
    -------
    dict
        A dictionary keyed by deme ID, indicating the number of samples allocated 
        to each.
    """

    # Convert deme keys in case_incidence to int if needed
    case_incidence = {int(k): v for k, v in case_incidence.items()}

    # Determine which demes to consider
    if target_demes is None:
        target_demes = list(case_incidence.keys())

    # Filter case_incidence to target demes
    target_case_incidence = {deme: case_incidence[deme] for deme in target_demes if deme in case_incidence}

    # Sum across all days for each deme
    deme_totals = {}
    for deme, daily_counts in target_case_incidence.items():
        deme_totals[deme] = np.sum(daily_counts)

    # Compute overall total incidence across these demes
    total_incidence = sum(deme_totals.values())

    # If total incidence is zero, allocate 0 to each
    if total_incidence == 0:
        return {deme: 0 for deme in target_demes}
    
    # Filter samples by target_demes if provided
    df = samples_df[samples_df["deme"].isin(target_demes)]

    # Number of total samples available, given the filters
    N = df.shape[0]
    if N == 0:
        return {deme: 0 for deme in target_demes}

    # Determine final target_number if needed
    if target_proportion is not None and target_number is None:
        target_number = int(target_proportion * N)
    if target_number is None:
        raise ValueError("Either 'target_proportion' or 'target_number' must be specified.")

    # Compute allocations in proportion to each deme's share of total incidence
    allocated = {}
    for deme, inc_sum in deme_totals.items():
        fraction = inc_sum / total_incidence
        deme_alloc_float = fraction * target_number
        allocated[deme] = int(round(deme_alloc_float))

    # Enforce a minimum number per deme if requested
    if min_number_per_deme > 0:
        for deme in allocated:
            if allocated[deme] < min_number_per_deme:
                allocated[deme] = min_number_per_deme

    return allocated


def uniform_population_spatial_allocation(
        population_sizes: dict,
        samples_df: pd.DataFrame,
        target_proportion: float = None,
        target_number: int = None,
        min_number_per_deme: int = 0,
        target_demes: list = None
    ) -> dict:
    """
    Allocate a target number (or proportion) of samples to be drawn from each deme in proportion to
    its initial population size.

    Parameters
    ----------
    population_sizes : dict, optional
        Dictionary keyed by integer deme ID. Each value is the population size for that deme.
        Required if weighting_strategy='population'.
    samples_df : pd.DataFrame
        A DataFrame of all candidate rows with columns ['sample_id', 'time', 'deme'].
    target_proportion : float, optional
        Fraction of the total filtered rows we want to sample, if `target_number` is None.
    target_number : int, optional
        Desired number of rows to sample. If both are provided and `target_number` is None,
        we use `target_proportion`.
    min_number_per_deme : int, optional
        Minimum number of samples allocated to each deme (applied after rounding).
    target_demes : list, optional
        If provided, only rows whose 'deme' is in this list are considered. Otherwise,
        all demes in `population_sizes`.

    Returns
    -------
    dict
        A dictionary keyed by deme ID, indicating the number of samples allocated 
        to each.
    """

    # Convert deme keys in population_sizes to int if needed
    population_sizes = {int(k): v for k, v in population_sizes.items()}

    # Determine which demes to consider
    if target_demes is None:
        target_demes = list(population_sizes.keys())

    # Filter population_sizes to target_demes
    target_pop_sizes = {deme: population_sizes[deme] for deme in target_demes if deme in population_sizes}

    # Sum population for these demes
    total_population = sum(target_pop_sizes.values())

    # Filter samples by target_demes
    df = samples_df[samples_df["deme"].isin(target_demes)]

    # Number of total samples available, given the filters
    N = df.shape[0]
    if N == 0:
        return {deme: 0 for deme in target_demes}

    # Determine final target_number if needed
    if target_proportion is not None and target_number is None:
        target_number = int(target_proportion * N)
    if target_number is None:
        raise ValueError("Either 'target_proportion' or 'target_number' must be specified.")

    # Compute allocations in proportion to each deme's population
    allocated = {}
    for deme, pop_size in target_pop_sizes.items():
        fraction = pop_size / total_population
        deme_alloc_float = fraction * target_number
        allocated[deme] = int(round(deme_alloc_float))

    # Enforce a minimum number per deme if requested
    if min_number_per_deme > 0:
        for deme in allocated:
            if allocated[deme] < min_number_per_deme:
                allocated[deme] = min_number_per_deme

    return allocated


def even_spatial_allocation(
        samples_df: pd.DataFrame,
        target_proportion: float = None,
        target_number: int = None,
        min_number_per_deme: int = 0,
        target_demes: list = None
    ) -> dict:
    """
    Allocate a target number (or proportion) of samples across demes evenly.

    Parameters
    ----------
    samples_df : pd.DataFrame
        A DataFrame of all candidate rows with columns ['sample_id', 'time', 'deme'].
    target_proportion : float, optional
        Fraction of the total filtered rows we want to sample, if `target_number` is None.
    target_number : int, optional
        Desired number of rows to sample. If both are provided and `target_number` is None,
        we use `target_proportion`.
    min_number_per_deme : int, optional
        Minimum number of samples allocated to each deme (applied after rounding).
    target_demes : list, optional
        If provided, only rows whose 'deme' is in this list are considered. Otherwise,
        all demes in `samples_df`.

    Returns
    -------
    dict
        A dictionary keyed by deme ID, indicating the number of samples allocated 
        to each.
    """

    # Determine which demes to consider
    if target_demes is None:
        target_demes = samples_df["deme"].unique()

    # Filter samples_df to target_demes
    df = samples_df[samples_df["deme"].isin(target_demes)]

    # Number of total samples available, given the filters
    N = df.shape[0]
    if N == 0:
        return {deme: 0 for deme in target_demes}
    
    # Determine final target_number if needed
    if target_proportion is not None and target_number is None:
        target_number = int(target_proportion * N)
    if target_number is None:
        raise ValueError("Either 'target_proportion' or 'target_number' must be specified.")
    
    # Compute allocations evenly across target demes
    n_target_demes = len(target_demes)
    even_alloc = target_number // n_target_demes
    allocated = {deme: even_alloc for deme in target_demes}

    # Enforce a minimum number per deme if requested
    if min_number_per_deme > 0:
        for deme in allocated:
            if allocated[deme] < min_number_per_deme:
                allocated[deme] = min_number_per_deme

    return allocated