from inferences.utilities.sampling.temporal_allocation import uniform_case_temporal_allocation, even_temporal_allocation
from inferences.utilities.sampling.spatial_sampling import weighted_spatial_sampling
import pandas as pd


# (Temporal, Spatial) = (UC, UC)
def tUC_sUC_draw(
        case_incidence: dict,
        samples_df: pd.DataFrame,
        time_range: tuple = None,
        target_proportion: float = None,
        target_number: int = None,
        min_number_per_day: int = 0,
        target_demes: list = None,
        random_state: int = 42
    ) -> pd.DataFrame:

    # Temporal allocation by UC
    temporal_allocation = uniform_case_temporal_allocation(
        case_incidence,
        samples_df,
        time_range=time_range,
        target_proportion=target_proportion,
        target_number=target_number,
        min_number_per_day=min_number_per_day,
        target_demes=target_demes
    )

    # Spatial sampling by UC
    samples_drawn_df = weighted_spatial_sampling(
        temporal_allocation,
        samples_df,
        case_incidence=case_incidence,
        target_demes=target_demes,
        weighting_strategy="cases",
        random_state=random_state
    )

    return samples_drawn_df


# (Temporal, Spatial) = (UC, UP)
def tUC_sUP_draw(
        case_incidence: dict,
        samples_df: pd.DataFrame,
        population_sizes: dict,
        time_range: tuple = None,
        target_proportion: float = None,
        target_number: int = None,
        min_number_per_day: int = 0,
        target_demes: list = None,
        random_state: int = 42
    ) -> pd.DataFrame:

    # Temporal allocation by UC
    temporal_allocation = uniform_case_temporal_allocation(
        case_incidence,
        samples_df,
        time_range=time_range,
        target_proportion=target_proportion,
        target_number=target_number,
        min_number_per_day=min_number_per_day,
        target_demes=target_demes
    )

    # Spatial sampling by UP
    samples_drawn_df = weighted_spatial_sampling(
        temporal_allocation,
        samples_df,
        population_sizes=population_sizes,
        target_demes=target_demes,
        weighting_strategy="population",
        random_state=random_state
    )

    return samples_drawn_df


# (Temporal, Spatial) = (UC, EV)
def tUC_sEV_draw(
        case_incidence: dict,
        samples_df: pd.DataFrame,
        time_range: tuple = None,
        target_proportion: float = None,
        target_number: int = None,
        min_number_per_day: int = 0,
        target_demes: list = None,
        random_state: int = 42
    ) -> pd.DataFrame:

    # Temporal allocation by UC
    temporal_allocation = uniform_case_temporal_allocation(
        case_incidence,
        samples_df,
        time_range=time_range,
        target_proportion=target_proportion,
        target_number=target_number,
        min_number_per_day=min_number_per_day,
        target_demes=target_demes
    )

    # Spatial sampling by EV
    samples_drawn_df = weighted_spatial_sampling(
        temporal_allocation,
        samples_df,
        target_demes=target_demes,
        weighting_strategy="even",
        random_state=random_state
    )

    return samples_drawn_df


# (Temporal, Spatial) = (EV, UC)
def tEV_sUC_draw(
        case_incidence: dict,
        samples_df: pd.DataFrame,
        time_range: tuple = None,
        target_proportion: float = None,
        target_number: int = None,
        min_number_per_day: int = 0,
        target_demes: list = None,
        random_state: int = 42
    ) -> pd.DataFrame:

    # Temporal allocation by EV
    temporal_allocation = even_temporal_allocation(
        case_incidence,
        samples_df,
        time_range=time_range,
        target_proportion=target_proportion,
        target_number=target_number,
        min_number_per_day=min_number_per_day,
        target_demes=target_demes
    )

    # Spatial sampling by UC
    samples_drawn_df = weighted_spatial_sampling(
        temporal_allocation,
        samples_df,
        case_incidence=case_incidence,
        target_demes=target_demes,
        weighting_strategy="cases",
        random_state=random_state
    )

    return samples_drawn_df


# (Temporal, Spatial) = (EV, UP)
def tEV_sUP_draw(
        case_incidence: dict,
        samples_df: pd.DataFrame,
        population_sizes: dict,
        time_range: tuple = None,
        target_proportion: float = None,
        target_number: int = None,
        min_number_per_day: int = 0,
        target_demes: list = None,
        random_state: int = 42
    ) -> pd.DataFrame:

    # Temporal allocation by EV
    temporal_allocation = even_temporal_allocation(
        case_incidence,
        samples_df,
        time_range=time_range,
        target_proportion=target_proportion,
        target_number=target_number,
        min_number_per_day=min_number_per_day,
        target_demes=target_demes
    )

    # Spatial sampling by UP
    samples_drawn_df = weighted_spatial_sampling(
        temporal_allocation,
        samples_df,
        population_sizes=population_sizes,
        target_demes=target_demes,
        weighting_strategy="population",
        random_state=random_state
    )

    return samples_drawn_df


# (Temporal, Spatial) = (EV, EV)
def tEV_sEV_draw(
        case_incidence: dict,
        samples_df: pd.DataFrame,
        time_range: tuple = None,
        target_proportion: float = None,
        target_number: int = None,
        min_number_per_day: int = 0,
        target_demes: list = None,
        random_state: int = 42
    ) -> pd.DataFrame:

    # Temporal allocation by EV
    temporal_allocation = even_temporal_allocation(
        case_incidence,
        samples_df,
        time_range=time_range,
        target_proportion=target_proportion,
        target_number=target_number,
        min_number_per_day=min_number_per_day,
        target_demes=target_demes
    )

    # Spatial sampling by EV
    samples_drawn_df = weighted_spatial_sampling(
        temporal_allocation,
        samples_df,
        target_demes=target_demes,
        weighting_strategy="even",
        random_state=random_state
    )

    return samples_drawn_df