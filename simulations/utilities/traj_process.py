import pandas as pd


def get_migratory_events(trajs_file: str, format: str = 'dataframe'):
    """
    Function to extract migratory events from simulated trajectories.
    Either returns a DataFrame with columns 'time', 'origin', and 'destination' if format is 'dataframe',
    or a list of tuples with (time, origin, destination) if format is 'list'.
    """
    # read full trajectory file
    trajs = pd.read_csv(trajs_file, sep='\t')

    # compute differences in value for each group of (population, index) at consecutive times
    trajs['value_diff'] = trajs.groupby(['population', 'index'])['value'].diff()

    # find groups (by t) where diff is in [-1, 1] and that they sum to 0
    migration_trajs = trajs[(trajs.population == 'I') & (trajs.value_diff.isin([-1, 1]))]
    migration_trajs = migration_trajs.loc[migration_trajs.groupby('t')['value_diff'].filter(lambda x: x.sum() == 0).index]

    # extract migration events in a vectorized manner
    origins = migration_trajs[migration_trajs['value_diff'] == -1].set_index('t')['index']
    destinations = migration_trajs[migration_trajs['value_diff'] == 1].set_index('t')['index']
    
    # combine origins and destinations into a DataFrame
    migration_events = pd.DataFrame({
        'time': origins.index,
        'origin': origins.values,
        'destination': destinations.values
    }).reset_index(drop=True)

    if format == 'dataframe':
        return migration_events
    
    return list(migration_events.itertuples(index=False, name=None))


def get_case_incidence(trajs_file: str, format: str = 'dataframe'):
    """
    Function to extract daily case incidence from simulated trajectories.
    Either returns a DataFrame with columns 't', 'deme', and 'new_cases' if format is 'dataframe',
    or a dictionary with deme as key and a list of new cases per day as value, where each list is of the same length (simulation duration).
    """
    # read trajectory file
    trajs = pd.read_csv(trajs_file, sep='\t')

    # filter for I and compute compute differences in value
    trajs = trajs[trajs.population == 'I'].drop(columns=['population'])
    trajs['value_diff'] = trajs.groupby('index')['value'].diff()

    # filter for valid incidence changes (i.e. sum(value_diff) == 1)
    valid_times = trajs.groupby('t')['value_diff'].transform('sum') == 1
    incidence = trajs[valid_times & (trajs['value_diff'] == 1)].astype({'t': int})
    
    # group by time and deme, count new cases
    incidence = (incidence.groupby(['t', 'index'])
                 .size()
                 .reset_index(name='new_cases')
                 .rename(columns={'index': 'deme'}))

    if format == 'dataframe':
        return incidence
    
    # convert to dictionary format
    simulation_T = int(trajs.t.max())
    incidence_dict = {}
    for deme in trajs['index'].unique():
        deme_dict = dict(incidence[incidence.deme == deme][['t', 'new_cases']].values)
        incidence_dict[int(deme)] = [int(deme_dict.get(t, 0)) for t in range(simulation_T + 1)]

    return incidence_dict


def get_sampling_rate(trajs_file: str, is_global: bool = False, format: str = 'dataframe'):
    """
    Function to compute the sampling rate from simulated trajectories.
    Returns the proportion of individuals that were sampled at the last time point, either globally or per deme.
    If the latter, the deme-specific sampling rates are returned as either a DataFrame or a dictionary.
    """
    # read trajectory file
    trajs = pd.read_csv(trajs_file, sep='\t')

    if is_global: # compute global sampling rate
        total_infected = trajs[(trajs.t == trajs.t.max()) & (trajs.population.isin(['I', 'R']))].value.sum()
        total_sampled = trajs[(trajs.t == trajs.t.max()) & (trajs.population == 'O')].value.iloc[0]
        return total_sampled / total_infected
    else: # compute per-deme sampling rate
        # compute total infected by deme
        total_infected_by_deme = trajs[(trajs.t == trajs.t.max()) & (trajs.population.isin(['I', 'R']))].groupby('index').agg({'value': 'sum'}).reset_index()
        total_infected_by_deme = total_infected_by_deme.rename(columns={'index': 'deme', 'value': 'total_infected'})

        # enumerate all sampling events
        trajs = trajs[trajs.population.isin(['I', 'O'])].copy()
        trajs['value_diff'] = trajs.groupby(['index', 'population'])['value'].diff()                                                                
        sampling_events = trajs[(trajs.population == 'O') & (trajs['value_diff'] == 1)]
        removal_events = trajs[(trajs.population == 'I') & (trajs['value_diff'] == -1)]
        merged_events = sampling_events.merge(
            removal_events,
            on='t',
            suffixes=('_O', '_I')
        )
        result = merged_events[['t', 'index_I']].rename(columns={'index_I': 'deme'})
        result = result.deme.value_counts().to_frame().reset_index()

        # merge with initial populations
        result = result.merge(total_infected_by_deme, on='deme')
        result['sampling_rate'] = result['count'] / result['total_infected']

        if format == 'dataframe':
            return result
        return result.set_index('deme').sampling_rate.to_dict()
    

def get_sampling_times(trajs_file: str, is_global: bool = False, format: str = 'dataframe'):
    """
    Function to compute the sampling times from simulated trajectories.
    Returns the time (day) when individuals were sampled, either globally or per deme.
    If the earlier, the sampling times are returned as a list; if the latter, either as a DataFrame or a dictionary of lists.
    """
    # read trajectory file
    trajs = pd.read_csv(trajs_file, sep='\t')
    
    if is_global: # compute global sampling times
        sampling_entries = trajs[trajs.population == 'O']
        sampling_counts = sampling_entries[sampling_entries.value.diff() == 1].t.astype(int).value_counts().sort_index().to_dict()
        sampling_counts_filled = [sampling_counts.get(t, 0) for t in range(int(trajs.t.max()) + 1)]
        return sampling_counts_filled
    else: # compute per-deme sampling times
        trajs = trajs[trajs.population.isin(['I', 'O'])].copy()
        trajs['value_diff'] = trajs.groupby(['index', 'population'])['value'].diff()                                                                
        sampling_events = trajs[(trajs.population == 'O') & (trajs['value_diff'] == 1)]
        removal_events = trajs[(trajs.population == 'I') & (trajs['value_diff'] == -1)]
        merged_events = sampling_events.merge(
            removal_events,
            on='t',
            suffixes=('_O', '_I')
        )
        result = merged_events[['t', 'index_I']].rename(columns={'index_I': 'deme'}).astype({'t': int})
        result = result.groupby(['t', 'deme']).size().reset_index(name='count')

        if format == 'dataframe':
            return result
        
        sampling_counts_filled_by_deme = {}
        for deme in trajs['index'].unique():
            deme_counts = dict(result[result.deme == deme][['t', 'count']].values)
            sampling_counts_filled_by_deme[int(deme)] = [int(deme_counts.get(t, 0)) for t in range(int(trajs.t.max()) + 1)]

        return sampling_counts_filled_by_deme