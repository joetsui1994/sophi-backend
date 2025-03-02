from simulations.utilities.traj_process import get_migratory_events, get_case_incidence, get_sampling_times
from simulations.utilities.tree_process import read_nexus_tree, get_subsampled_tree
from django.conf import settings
from django.db import models
import pandas as pd
import base64
import uuid
import os


# File upload functions for Simulation model
def upload_populations_file_path(instance, filename):
    return os.path.join(settings.SIMULATIONS_FOLDER, str(instance.uuid), 'populations.tsv')
def upload_mobility_matrix_file_path(instance, filename):
    return os.path.join(settings.SIMULATIONS_FOLDER, str(instance.uuid), 'mobility_matrix.tsv')
def upload_sampled_tree_file_path(instance, filename):
    return os.path.join(settings.SIMULATIONS_FOLDER, str(instance.uuid), 'simulated.tree.nex')
def upload_trajectory_file_path(instance, filename):
    return os.path.join(settings.SIMULATIONS_FOLDER, str(instance.uuid), 'simulated.traj.gz')
def upload_epi_params_file_path(instance, filename):
    return os.path.join(settings.SIMULATIONS_FOLDER, str(instance.uuid), 'epi_params.json')
def upload_xml_file_path(instance, filename):
    return os.path.join(settings.SIMULATIONS_FOLDER, str(instance.uuid), 'run.xml')


# Function to generate a short UUID
def generate_short_uuid(length=8):
    """Generate a short UUID by encoding a UUID4 in Base62."""
    uuid_bytes = uuid.uuid4().bytes  # Get the raw UUID bytes
    short_uuid = base64.urlsafe_b64encode(uuid_bytes).decode('utf-8').rstrip('=')  # Base64 encode and strip padding
    return short_uuid[:length]


# Model for simulated outbreaks
class Simulation(models.Model):
    """
    Model to store information about a simulated outbreak, including the name, description, parameters, and relevant input/output files.
    """
    uuid = models.CharField(default=generate_short_uuid, editable=False, unique=True, primary_key=True)
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    outbreak_origin = models.IntegerField(blank=True, null=True) # deme ID of the outbreak origin
    beta = models.FloatField(blank=True, null=True) # transmission coefficient (before normalization)
    gamma = models.FloatField(blank=True, null=True) # recovery rate
    delta = models.FloatField(blank=True, null=True) # sampling rate
    num_demes = models.PositiveIntegerField(blank=True, null=True) # number of demes
    duration_days = models.PositiveIntegerField(blank=True, null=True) # duration of simulation in days
    populations = models.JSONField(blank=True, null=True) # population size for each deme
    sampling_times = models.JSONField(blank=True, null=True) # time of sample collection for each deme
    mobility_matrix = models.JSONField(blank=True, null=True) # mobility matrix (i.e. number of individuals moving between each pair of demes per day)
    case_incidence = models.JSONField(blank=True, null=True) # daily case incidence data (from simulated trajectories)
    migratory_events = models.JSONField(blank=True, null=True) # migration events (from simulated trajectories)
    populations_file = models.FileField(upload_to=upload_populations_file_path) # initial population sizes (header: deme, population)
    mobility_matrix_file = models.FileField(upload_to=upload_mobility_matrix_file_path) # mobility matrix (header: from, to, rate)
    trajectory_file = models.FileField(upload_to=upload_trajectory_file_path) # simulated trajectory data
    sampled_tree_file = models.FileField(upload_to=upload_sampled_tree_file_path) # sampled and annotated tree
    epi_params_file = models.FileField(upload_to=upload_epi_params_file_path) # Epidemiological parameters file
    xml_file = models.FileField(upload_to=upload_xml_file_path) # BEAST XML file
    is_complete = models.BooleanField(default=False) # flag to indicate whether all required fields have been populated

    def __str__(self):
        return self.name
    
    # method to generate a unique name for the simulation
    def generate_name(self):
        # make sure that all required fields have been populated
        assert self.check_complete(), "Aborting: not all required fields have been populated"

        # generate unique name based on model attributes
        new_name = f"dN({self.num_demes})|o({int(self.outbreak_origin)})|T({self.duration_days})|b({self.beta:.2f})|g({self.gamma:.2f})|d({self.delta:.2f})|"
        # check for duplicate names
        num_duplicate = Simulation.objects.exclude(name=self.name).filter(name__startswith=new_name).count()
        self.name = f"{new_name}{num_duplicate}"
        self.save()

    # method to get total population size
    def get_total_population(self):
        return sum(self.populations.values())
    
    # method to get total infected individuals
    def get_total_infected(self):
        return sum([sum(new_cases) for new_cases in self.case_incidence.values()])
    
    # method to get total sampled individuals
    def get_total_sampled(self):
        return sum([sum(sampling_times) for sampling_times in self.sampling_times.values()])

    # method to get total number of infected individuals in each deme
    def get_deme_infected(self):
        return {deme: sum(new_cases) for deme, new_cases in self.case_incidence.items()}
    
    # method to get total number of sampled individuals in each deme
    def get_deme_sampled(self):
        return {deme: sum(sampling_times) for deme, sampling_times in self.sampling_times.items()}

    # method to get basic reproductive number (accounting for sampling by default)
    def get_R0(self, with_sampling: bool = True):
        return self.beta / (self.gamma + self.delta if with_sampling else self.gamma)

    # method to populate description from model attributes
    def populate_description(self):
        # make sure that all required fields have been populated
        assert self.check_complete(), "Aborting: not all required fields have been populated"

        # compute global attack rate and global sampling rate (weighted by population)
        total_population = self.get_total_population()
        total_infected = self.get_total_infected()
        total_sampled = self.get_total_sampled()
        global_attack_rate = total_infected / total_population
        global_sampling_rate = total_sampled / total_infected
        description_1 = (
            f"Simulation of an outbreak (originating from deme {int(self.outbreak_origin)}) with {self.num_demes} demes "
            f"(total population {'{:,}'.format(int(total_population))}) over "
            f"{'{:,}'.format(int(self.duration_days))} days, with beta={self.beta}, gamma={self.gamma}, "
            f"and delta={self.delta}"
        )
        description_2 = (
            f"By the end of the simulation, {global_attack_rate * 100:.1f}% "
            f"(n={'{:,}'.format(total_infected)}) of the population had been infected, of whom "
            f"{global_sampling_rate * 100:.1f}% (n={'{:,}'.format(total_sampled)}) were sampled and sequenced."
        )
        self.description = f"{description_1} {description_2}"
        self.save()

    # method to populate epi_params from epi_params_file
    def populate_epi_params(self):
        epi_params = pd.read_json(self.epi_params_file.path, typ='series')
        self.outbreak_origin = epi_params['outbreak_origin']
        self.beta = epi_params['beta']
        self.gamma = epi_params['gamma']
        self.delta = epi_params['delta']
        self.save()

    # method to populate num_demes from populations
    def populate_num_demes(self):
        # make sure that populations is not empty
        assert self.populations, "Aborting: populations have not been populated"
        self.num_demes = len(self.populations)
        self.save()

    # method to populate duration_days from case_incidence
    def populate_duration_days(self):
        # make sure that case_incidence is not empty
        assert self.case_incidence, "Aborting: case_incidence has not been populated"
        self.duration_days = len(list(self.case_incidence.values())[0])
        self.save()

    # method to extract/populate populations from populations_file
    def populate_populations(self, save: bool = True):
        populations = pd.read_csv(self.populations_file.path, sep='\t')
        if save: # save population data (as a dictionary) to database
            self.populations = populations.set_index('deme')['population'].to_dict()
            self.save()
        else:
            return populations
        
    # method to extract/populate sampled_populations from trajectory_file
    def populate_sampling_times(self, save: bool = True):
        if save: # save sampling rates (as a dictionary) to database
            self.sampling_times = get_sampling_times(self.trajectory_file.path, format='dict')
            self.save()
        else:
            return get_sampling_times(self.trajectory_file.path, format='dataframe')
    
    # method to extract/populate mobility_matrix from mobility_matrix_file
    def populate_mobility_matrix(self, save: bool = True):
        mobility_matrix = pd.read_csv(self.mobility_matrix_file.path, sep='\t')
        if save: # save mobility matrix (as a list of tuples) to database
            self.mobility_matrix = [tuple(row) for row in mobility_matrix.itertuples(index=False, name=None)]
            self.save()
        else:
            return mobility_matrix

    # method to extract/populate case_incidence from trajectory_file
    def populate_case_incidence(self, save: bool = True):
        if save: # save case incidence data (as a dictionary) to database
            self.case_incidence = get_case_incidence(self.trajectory_file.path, format='dict')
            self.save()
        else:
            return get_case_incidence(self.trajectory_file.path, format='dataframe')

    # method to extract/populate migratory_events from trajectory_file
    def populate_migratory_events(self, save: bool = True):
        if save: # save migration events (as a list) to database
            self.migratory_events = get_migratory_events(self.trajectory_file.path, format='list')
            self.save()
        else:
            return get_migratory_events(self.trajectory_file.path, format='dataframe')

    # method to transform mobility matrix into nodes/links format from mobility_matrix
    def get_mobility_graph(self):
        # make sure that both populations and mobility matrix have been populated
        assert self.populations, "Aborting: populations have not been populated"
        assert self.mobility_matrix, "Aborting: mobility_matrix has not been populated"
        nodes = [{'id': deme, 'size': population} for deme, population in self.populations.items()]
        links = [{'source': i, 'target': j, 'value': rate} for i, j, rate in self.mobility_matrix]
        return {'nodes': nodes, 'links': links}

    # method to check that all required files have been specified
    def check_files(self):
        return all([self.populations_file,
                    self.mobility_matrix_file,
                    self.trajectory_file,
                    self.sampled_tree_file,
                    self.epi_params_file,
                    self.xml_file])
    
    # method to populate all fields based on uploaded files
    def populate_all(self):
        self.populate_epi_params()
        self.populate_populations()
        self.populate_mobility_matrix()
        self.populate_case_incidence()
        self.populate_sampling_times()
        self.populate_migratory_events()
        self.populate_num_demes()
        self.populate_duration_days()
        self.save()

    # method to check that all required fields have been populated
    def check_complete(self, save: bool = True):
        is_complete = all(
            field is not None for field in [
                self.num_demes,
                self.duration_days,
                self.outbreak_origin,
                self.beta,
                self.gamma,
                self.delta,
                self.populations,
                self.mobility_matrix,
                self.case_incidence,
                self.sampling_times,
                self.migratory_events
                ])
        if save:
            self.is_complete = is_complete
            self.save()
        return is_complete
    
    # method to read annotated tree from sampled_tree_file as an ETE3 Tree object
    def read_sampled_tree(self):
        return read_nexus_tree(self.sampled_tree_file.path)
    
    # method to get the IDs of all samples and their sampling (time, deme) from the sampled tree as a DataFrame (default) or a dictionary
    def get_samples(self, format: str = 'dataframe', by_day: bool = False):
        tree = self.read_sampled_tree()
        # extract leaf nodes with sampling time and deme
        samples_data = {leaf.name: {
            'time': int(leaf.time) if by_day else leaf.time,
            'deme': int(leaf.deme)
            } for leaf in tree.iter_leaves()}
        if format == 'dataframe':
            df = pd.DataFrame(samples_data).T.astype({'deme': int}).reset_index()
            df.columns = ['sample_id', 'time', 'deme']
            return df
        return samples_data
    
    # method to subsample the full tree given a list of sample IDs
    def subsample_tree(self, sample_ids: list = None, deannotate_tree: bool = True, extract_attributes: bool = False, attributes_format: str = 'dataframe'):
        tree = self.read_sampled_tree()
        return get_subsampled_tree(tree, sample_ids=sample_ids,
                                   deannotate_tree=deannotate_tree,
                                   extract_attributes=extract_attributes,
                                   attributes_format=attributes_format)
    
    # method to get inference-tree
    def get_inference_tree(self, user=None):
        root_inference = self.inference_set.filter(head__isnull=True).prefetch_related('children').first()

        # recursive function to get the tree as a nested dictionary
        def collect_children_inferences(inference):
            children_inferences = inference.children.all()

            # if filtering by user, only include children belonging to the same user
            if user:
                children_inferences = children_inferences.filter(user=user)

            children = []
            for child_inference in children_inferences:
                children.append({
                    'uuid': child_inference.uuid,
                    'children': collect_children_inferences(child_inference)
                })
            return children

        # build tree dict
        tree_dict = {
            'uuid': root_inference.uuid,
            'children': collect_children_inferences(root_inference)
        }

        return tree_dict
    
    # method to get the uuid of the  most N recent inferences
    def get_recent_inferences(self, user=None, N=3):
        if user:
            return self.inference_set.filter(user=user).order_by('-created_at').values_list('uuid', flat=True)[:N]
        return self.inference_set.order_by('-created_at').values_list('uuid', flat=True)[:N]

    # method to get counts of true migratory events (either importation or exportation) for each deme
    def get_migratory_event_counts(self, demes: list = None, event_type: str = 'import', rolling_window: int = 1):
        # make sure that migratory events have been populated
        assert self.migratory_events, "Aborting: migratory_events have not been populated"
        # make sure that demes provided is valid
        assert demes is None or all([str(deme) in self.populations for deme in demes]), "Aborting: invalid deme ID provided"
        # make sure that event_type is valid
        assert event_type in ['import', 'export', 'transfer'], "Aborting: invalid event type provided"
        # if 'transfer', make sure that two demes are provided
        assert event_type != 'transfer' or len(demes) == 2, "Aborting: two demes must be provided for transfer events"

        # if 'transfer', get counts for deme 0 -> deme 1
        if event_type == 'transfer':
            event_counts = [0] * self.duration_days
            for event in self.migratory_events:
                time, origin, destination = event
                time_int = int(time)

                if origin == demes[0] and destination == demes[1]:
                    event_counts[time_int] += 1

            # apply rolling window
            if rolling_window > 1:
                event_counts = [0] * (rolling_window - 1) + [sum(event_counts[i:i+rolling_window]) / rolling_window for i in range(self.duration_days - rolling_window + 1)] + [0] * (rolling_window - 1)

            return event_counts
        
        # if 'import' or 'export', get counts for each deme
        event_counts = { int(deme): [0] * self.duration_days for deme in self.populations.keys() if demes is None or int(deme) in demes }
        for event in self.migratory_events:
            time, origin, destination = event
            time_int = int(time)

            if event_type == 'import' and destination in event_counts:
                event_counts[destination][time_int] += 1
            elif event_type == 'export' and origin in event_counts:
                event_counts[origin][time_int] += 1 

        # apply rolling window
        if rolling_window > 1:
            for deme, counts in event_counts.items():
                event_counts[deme] = [0] * (rolling_window - 1) + [sum(counts[i:i+rolling_window]) / rolling_window for i in range(self.duration_days - rolling_window + 1)] + [0] * (rolling_window - 1)

        return event_counts
    
    # method to get time and source of earliest importation event for each deme
    def get_earliest_importation(self, demes: list = None):
        # make sure that migratory events have been populated
        assert self.migratory_events, "Aborting: migratory_events have not been populated"
        # make sure that demes provided is valid
        assert demes is None or all([str(deme) in self.populations for deme in demes]), "Aborting: invalid deme ID provided"

        # filter migratory events by deme, if specified
        earliest_importations = { int(deme): { 'time': float('inf'), 'source': None }
                                 for deme in self.populations.keys() if demes is None or int(deme) in demes }
        for event in self.migratory_events:
            time, origin, destination = event

            if destination in earliest_importations and earliest_importations[destination]['time'] > time:
                earliest_importations[destination] = { 'time': time, 'source': int(origin) }

        # convert float(inf) to None
        for deme, earliest_importation in earliest_importations.items():
            if earliest_importation['time'] == float('inf'):
                earliest_importations[deme] = { 'time': None, 'source': None }

        # add outbreak origin
        if self.outbreak_origin in earliest_importations:
            earliest_importations[self.outbreak_origin] = { 'time': 0, 'source': None }

        return earliest_importations