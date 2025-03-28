import pandas as pd

from inferences.utilities.sampling.temporal_sampling import weighted_temporal_sampling, earliest_N_by_deme_sampling
from inferences.utilities.sampling.spatial_allocation import uniform_sample_spatial_allocation, uniform_case_spatial_allocation, uniform_population_spatial_allocation, even_spatial_allocation


# (Spatial, Temporal) = (US, US)
def sUS_tUS_draw(
        case_incidence: dict,
        samples_df: pd.DataFrame,
        target_proportion: float = None,
        target_number: int = None,
        min_number_per_deme: int = 0,
        target_demes: list = None,
        random_state: int = 42
    ) -> pd.DataFrame:

    # Spatial allocation by US
    spatial_allocation = uniform_sample_spatial_allocation(
        case_incidence,
        samples_df,
        target_proportion=target_proportion,
        target_number=target_number,
        min_number_per_deme=min_number_per_deme,
        target_demes=target_demes
    )

    # Temporal allocation by US
    samples_drawn_df = weighted_temporal_sampling(
        spatial_allocation,
        samples_df,
        weighting_strategy="samples",
        random_state=random_state
    )

    return samples_drawn_df


# (Spatial, Temporal) = (US, UC)
def sUS_tUC_draw(
        case_incidence: dict,
        samples_df: pd.DataFrame,
        target_proportion: float = None,
        target_number: int = None,
        min_number_per_deme: int = 0,
        target_demes: list = None,
        random_state: int = 42
    ) -> pd.DataFrame:

    # Spatial allocation by US
    spatial_allocation = uniform_sample_spatial_allocation(
        case_incidence,
        samples_df,
        target_proportion=target_proportion,
        target_number=target_number,
        min_number_per_deme=min_number_per_deme,
        target_demes=target_demes
    )

    # Temporal sampling by UC
    samples_drawn_df = weighted_temporal_sampling(
        spatial_allocation,
        samples_df,
        weighting_strategy="cases",
        case_incidence=case_incidence,
        random_state=random_state
    )

    return samples_drawn_df


# (Spatial, Temporal) = (US, EV)
def sUS_tEV_draw(
        case_incidence: dict,
        samples_df: pd.DataFrame,
        target_proportion: float = None,
        target_number: int = None,
        min_number_per_deme: int = 0,
        target_demes: list = None,
        random_state: int = 42
    ) -> pd.DataFrame:

    # Spatial allocation by US
    spatial_allocation = uniform_sample_spatial_allocation(
        case_incidence,
        samples_df,
        target_proportion=target_proportion,
        target_number=target_number,
        min_number_per_deme=min_number_per_deme,
        target_demes=target_demes
    )

    # Temporal sampling by EV
    samples_drawn_df = weighted_temporal_sampling(
        spatial_allocation,
        samples_df,
        weighting_strategy="even",
        random_state=random_state
    )

    return samples_drawn_df


# (Spatial, Temporal) = (US, EN)
def sUS_tEN_draw(
        case_incidence: dict,
        samples_df: pd.DataFrame,
        target_proportion: float = None,
        target_number: int = None,
        min_number_per_deme: int = 0,
        target_demes: list = None,
        random_state: int = 42
    ) -> pd.DataFrame:

    # Spatial allocation by US
    spatial_allocation = uniform_sample_spatial_allocation(
        case_incidence,
        samples_df,
        target_proportion=target_proportion,
        target_number=target_number,
        min_number_per_deme=min_number_per_deme,
        target_demes=target_demes
    )

    # Temporal sampling by EN
    samples_drawn_df = earliest_N_by_deme_sampling(
        spatial_allocation,
        samples_df,
        random_state=random_state
    )

    return samples_drawn_df


# (Spatial, Temporal) = (UC, US)
def sUC_tUS_draw(
        case_incidence: dict,
        samples_df: pd.DataFrame,
        target_proportion: float = None,
        target_number: int = None,
        min_number_per_deme: int = 0,
        target_demes: list = None,
        random_state: int = 42
    ) -> pd.DataFrame:

    # Spatial allocation by UC
    spatial_allocation = uniform_case_spatial_allocation(
        case_incidence,
        samples_df,
        target_proportion=target_proportion,
        target_number=target_number,
        min_number_per_deme=min_number_per_deme,
        target_demes=target_demes
    )

    # Temporal sampling by US
    samples_drawn_df = weighted_temporal_sampling(
        spatial_allocation,
        samples_df,
        weighting_strategy="samples",
        random_state=random_state
    )

    return samples_drawn_df


# (Spatial, Temporal) = (UC, UC)
def sUC_tUC_draw(
        case_incidence: dict,
        samples_df: pd.DataFrame,
        target_proportion: float = None,
        target_number: int = None,
        min_number_per_deme: int = 0,
        target_demes: list = None,
        random_state: int = 42
    ) -> pd.DataFrame:

    # Spatial allocation by UC
    spatial_allocation = uniform_case_spatial_allocation(
        case_incidence,
        samples_df,
        target_proportion=target_proportion,
        target_number=target_number,
        min_number_per_deme=min_number_per_deme,
        target_demes=target_demes
    )

    # Temporal sampling by UC
    samples_drawn_df = weighted_temporal_sampling(
        spatial_allocation,
        samples_df,
        weighting_strategy="cases",
        case_incidence=case_incidence,
        random_state=random_state
    )

    return samples_drawn_df


# (Spatial, Temporal) = (UC, EV)
def sUC_tEV_draw(
        case_incidence: dict,
        samples_df: pd.DataFrame,
        target_proportion: float = None,
        target_number: int = None,
        min_number_per_deme: int = 0,
        target_demes: list = None,
        random_state: int = 42
    ) -> pd.DataFrame:

    # Spatial allocation by UC
    spatial_allocation = uniform_case_spatial_allocation(
        case_incidence,
        samples_df,
        target_proportion=target_proportion,
        target_number=target_number,
        min_number_per_deme=min_number_per_deme,
        target_demes=target_demes
    )

    # Temporal sampling by EV
    samples_drawn_df = weighted_temporal_sampling(
        spatial_allocation,
        samples_df,
        weighting_strategy="even",
        random_state=random_state
    )

    return samples_drawn_df


# (Spatial, Temporal) = (UC, EN)
def sUC_tEN_draw(
        case_incidence: dict,
        samples_df: pd.DataFrame,
        target_proportion: float = None,
        target_number: int = None,
        min_number_per_deme: int = 0,
        target_demes: list = None,
        random_state: int = 42
    ) -> pd.DataFrame:

    # Spatial allocation by UC
    spatial_allocation = uniform_case_spatial_allocation(
        case_incidence,
        samples_df,
        target_proportion=target_proportion,
        target_number=target_number,
        min_number_per_deme=min_number_per_deme,
        target_demes=target_demes
    )

    # Temporal sampling by EN
    samples_drawn_df = earliest_N_by_deme_sampling(
        spatial_allocation,
        samples_df,
        random_state=random_state
    )

    return samples_drawn_df


# (Spatial, Temporal) = (UP, UC)
def sUP_tUC_draw(
        case_incidence: dict,
        samples_df: pd.DataFrame,
        population_sizes: dict,
        target_proportion: float = None,
        target_number: int = None,
        min_number_per_deme: int = 0,
        target_demes: list = None,
        random_state: int = 42
    ) -> pd.DataFrame:

    # Spatial allocation by UP
    spatial_allocation = uniform_population_spatial_allocation(
        population_sizes,
        samples_df,
        target_proportion=target_proportion,
        target_number=target_number,
        min_number_per_deme=min_number_per_deme,
        target_demes=target_demes
    )

    # Temporal sampling by UC
    samples_drawn_df = weighted_temporal_sampling(
        spatial_allocation,
        samples_df,
        weighting_strategy="cases",
        case_incidence=case_incidence,
        random_state=random_state
    )

    return samples_drawn_df


# (Spatial, Temporal) = (UP, EV)
def sUP_tEV_draw(
        samples_df: pd.DataFrame,
        population_sizes: dict,
        target_proportion: float = None,
        target_number: int = None,
        min_number_per_deme: int = 0,
        target_demes: list = None,
        random_state: int = 42
    ) -> pd.DataFrame:

    # Spatial allocation by UP
    spatial_allocation = uniform_population_spatial_allocation(
        population_sizes,
        samples_df,
        target_proportion=target_proportion,
        target_number=target_number,
        min_number_per_deme=min_number_per_deme,
        target_demes=target_demes
    )

    # Temporal sampling by EV
    samples_drawn_df = weighted_temporal_sampling(
        spatial_allocation,
        samples_df,
        weighting_strategy="even",
        random_state=random_state
    )

    return samples_drawn_df


# (Spatial, Temporal) = (UP, EN)
def sUP_tEN_draw(
        samples_df: pd.DataFrame,
        population_sizes: dict,
        target_proportion: float = None,
        target_number: int = None,
        min_number_per_deme: int = 0,
        target_demes: list = None,
        random_state: int = 42
    ) -> pd.DataFrame:

    # Spatial allocation by UP
    spatial_allocation = uniform_population_spatial_allocation(
        population_sizes,
        samples_df,
        target_proportion=target_proportion,
        target_number=target_number,
        min_number_per_deme=min_number_per_deme,
        target_demes=target_demes
    )

    # Temporal sampling by EN
    samples_drawn_df = earliest_N_by_deme_sampling(
        spatial_allocation,
        samples_df,
        random_state=random_state
    )

    return samples_drawn_df


# (Spatial, Temporal) = (EV, US)
def sEV_tUS_draw(
        case_incidence: dict,
        samples_df: pd.DataFrame,
        target_proportion: float = None,
        target_number: int = None,
        min_number_per_deme: int = 0,
        target_demes: list = None,
        random_state: int = 42
    ) -> pd.DataFrame:

    # Spatial allocation by EV
    spatial_allocation = even_spatial_allocation(
        samples_df,
        target_proportion=target_proportion,
        target_number=target_number,
        min_number_per_deme=min_number_per_deme,
        target_demes=target_demes
    )

    # Temporal allocation by US
    samples_drawn_df = weighted_temporal_sampling(
        spatial_allocation,
        samples_df,
        weighting_strategy="samples",
        random_state=random_state
    )

    return samples_drawn_df


# (Spatial, Temporal) = (EV, UC)
def sEV_tUC_draw(
        case_incidence: dict,
        samples_df: pd.DataFrame,
        target_proportion: float = None,
        target_number: int = None,
        min_number_per_deme: int = 0,
        target_demes: list = None,
        random_state: int = 42
    ) -> pd.DataFrame:

    # Spatial allocation by EV
    spatial_allocation = even_spatial_allocation(
        samples_df,
        target_proportion=target_proportion,
        target_number=target_number,
        min_number_per_deme=min_number_per_deme,
        target_demes=target_demes
    )

    # Temporal sampling by UC
    samples_drawn_df = weighted_temporal_sampling(
        spatial_allocation,
        samples_df,
        weighting_strategy="cases",
        case_incidence=case_incidence,
        random_state=random_state
    )

    return samples_drawn_df


# (Spatial, Temporal) = (EV, EV)
def sEV_tEV_draw(
        samples_df: pd.DataFrame,
        target_proportion: float = None,
        target_number: int = None,
        min_number_per_deme: int = 0,
        target_demes: list = None,
        random_state: int = 42
    ) -> pd.DataFrame:

    # Spatial allocation by EV
    spatial_allocation = even_spatial_allocation(
        samples_df,
        target_proportion=target_proportion,
        target_number=target_number,
        min_number_per_deme=min_number_per_deme,
        target_demes=target_demes
    )

    # Temporal sampling by EV
    samples_drawn_df = weighted_temporal_sampling(
        spatial_allocation,
        samples_df,
        weighting_strategy="even",
        random_state=random_state
    )

    return samples_drawn_df


# (Spatial, Temporal) = (EV, EN)
def sEV_tEN_draw(
        samples_df: pd.DataFrame,
        target_proportion: float = None,
        target_number: int = None,
        min_number_per_deme: int = 0,
        target_demes: list = None,
        random_state: int = 42
    ) -> pd.DataFrame:

    # Spatial allocation by EV
    spatial_allocation = even_spatial_allocation(
        samples_df,
        target_proportion=target_proportion,
        target_number=target_number,
        min_number_per_deme=min_number_per_deme,
        target_demes=target_demes
    )

    # Temporal sampling by EN
    samples_drawn_df = earliest_N_by_deme_sampling(
        spatial_allocation,
        samples_df,
        random_state=random_state
    )

    return samples_drawn_df