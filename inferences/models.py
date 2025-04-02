from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.contrib.auth.models import User
from collections import defaultdict
from django.core.files import File
from django.conf import settings
from django.db import models
from ete3 import Tree
import tempfile
import inspect
import base64
import random
import uuid
import os

from inferences.utilities.dta.ph_dta import run_phangorn_dta
from inferences.utilities.sampling.temporal_prioritised_strategies import (
    tUS_sUS_draw,
    tUS_sEV_draw,
    tUS_sUP_draw,
    tUS_sUC_draw,
    tUC_sUS_draw,
    tUC_sUC_draw,
    tUC_sUP_draw, 
    tUC_sEV_draw,
    tEV_sUS_draw,
    tEV_sUC_draw,
    tEV_sUP_draw,
    tEV_sEV_draw
)
from inferences.utilities.sampling.spatial_prioritised_strategies import (
    sUS_tUS_draw,
    sUS_tUC_draw,
    sUS_tEV_draw,
    sUS_tEN_draw,
    sUC_tUS_draw,
    sUC_tUC_draw,
    sUC_tEV_draw,
    sUC_tEN_draw,
    sUP_tUS_draw,
    sUP_tUC_draw,
    sUP_tEV_draw,
    sUP_tEN_draw,
    sEV_tUS_draw,
    sEV_tUC_draw,
    sEV_tEV_draw,
    sEV_tEN_draw
)
from inferences.utilities.sampling.temporal_sampling import earliest_N_temporal_sampling as tEN_draw
from inferences.utilities.sampling.spatiotemporal_sampling import stUC_draw, stEV_draw, stUS_draw
from inferences.utilities.vis_tree.run_d3tree import run_d3tree
from inferences.utilities.vis_tree.tree_thinning import thin_tree


def generate_short_uuid(length=8):
    """Generate a short UUID by encoding a UUID4 in Base62."""
    uuid_bytes = uuid.uuid4().bytes  # Get the raw UUID bytes
    short_uuid = base64.urlsafe_b64encode(uuid_bytes).decode('utf-8').rstrip('=')  # Base64 encode and strip padding
    return short_uuid[:length]


# Model for samples allocation
class SamplesAllocation(models.Model):
    """
    Model to store information about the allocation of samples, including the relevant time frame, sampling strategy, sampling rates, and other relevant details.
    """
    class TemporalStrategies(models.TextChoices):
        UNIFORM_SAMPLE = "US", _("Uniform allocation in proportion to number of samples")
        UNIFORM_CASE = "UC", _("Uniform allocation in proportion to case incidence")
        INV_UNIFORM_CASE = "IUC", _("Uniform allocation in inverse proportion to case incidence")
        EVEN = "EV", _("Even allocation of samples across time")
        EARLIEST_N = "EN", _("Earliest N samples")
        LATEST_N = "LN", _("Latest N samples")
    
    class SpatialStrategies(models.TextChoices):
        UNIFORM_SAMPLE = "US", _("Uniform allocation in proportion to number of samples")
        UNIFORM_CASE = "UC", _("Uniform allocation in proportion to number of cases")
        INV_UNIFORM_CASE = "IUC", _("Uniform allocation in inverse proportion to number of cases")
        UNIFORM_POP = "UP", _("Uniform allocation in proportion to population size")
        INV_UNIFORM_POP = "IUP", _("Uniform allocation in inverse proportion to population size")
        EVEN = "EV", _("Even allocation of samples across demes")

    class AllocationPriority(models.TextChoices):
        TEMPORAL = "T", _("Temporal prioritization")
        SPATIAL = "S", _("Spatial prioritization")
        JOINT = "J", _("Joint prioritization")

    created_at = models.DateTimeField(auto_now_add=True)
    earliest_time = models.PositiveIntegerField(blank=False, null=False) # inclusive
    latest_time = models.PositiveIntegerField(blank=False, null=False) # inclusive
    target_proportion = models.FloatField(blank=True, null=True) # target sampling proportion (mutually exclusive with target_number)
    target_number = models.PositiveIntegerField(blank=True, null=True) # target number of samples (takes precedence over target_proportion)
    target_demes = models.JSONField(blank=True, null=True) # list of demes to target for sampling; if empty, sample from all demes
    min_number = models.PositiveIntegerField(default=0) # minimum number of samples to allocate per day
    temporal_strategy = models.CharField(max_length=3, choices=TemporalStrategies.choices, default=TemporalStrategies.UNIFORM_CASE, blank=True, null=True)
    spatial_strategy = models.CharField(max_length=3, choices=SpatialStrategies.choices, default=SpatialStrategies.UNIFORM_CASE, blank=True, null=True)
    allocation_priority = models.CharField(max_length=1, choices=AllocationPriority.choices, default=AllocationPriority.JOINT)

    def __str__(self):
        if self.allocation_priority == self.AllocationPriority.JOINT:
            return f"{self.allocation_priority}({self.temporal_strategy})"
        elif self.allocation_priority == self.AllocationPriority.TEMPORAL:
            if self.spatial_strategy:
                return f"{self.allocation_priority}({self.temporal_strategy}->{self.spatial_strategy})"
            return f"{self.allocation_priority}({self.temporal_strategy})"
        elif self.allocation_priority == self.AllocationPriority.SPATIAL:
            return f"{self.allocation_priority}({self.spatial_strategy}->{self.temporal_strategy})"

    def set_target_proportion(self, proportion):
        self.target_proportion = proportion
        self.target_number = None

    def set_target_number(self, number):
        self.target_number = number
        self.target_proportion = None
    
    def draw_samples(self, simulation, random_state=42):
        # Get associated simulation and required data
        case_incidence = simulation.case_incidence
        population_sizes = simulation.populations
        samples_df = simulation.get_samples(by_day=True)

        # Arguments for allocation and sampling
        all_args = {
            "case_incidence": case_incidence,
            "samples_df": samples_df,
            "population_sizes": population_sizes,
            "time_range": (self.earliest_time, self.latest_time),
            "target_proportion": self.target_proportion,
            "target_number": self.target_number,
            "min_number_per_day": self.min_number,
            "min_number_per_deme": self.min_number,
            "target_demes": self.target_demes,
            "random_state": random_state,
        }

        # Helper to extract relevant arguments for a function
        def get_relevant_args(func, all_args):
            func_params = inspect.signature(func).parameters
            args = []
            kwargs = {}
            for i, (param_name, param) in enumerate(func_params.items()):
                if param.kind in [inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD]:
                    # Positional arguments
                    if param_name in all_args:
                        args.append(all_args[param_name])
                    elif param.default == inspect.Parameter.empty:
                        raise ValueError(f"Missing required positional argument: {param_name}")
                elif param.kind == inspect.Parameter.KEYWORD_ONLY:
                    # Keyword arguments
                    if param_name in all_args:
                        kwargs[param_name] = all_args[param_name]
                    elif param.default == inspect.Parameter.empty:
                        raise ValueError(f"Missing required keyword argument: {param_name}")
            return args, kwargs
        
        # Helper to get the appropriate draw function
        def get_draw_function(allocation_priority, temporal_strategy=None, spatial_strategy=None):
            draw_function_map = {
                # Temporal-prioritised strategies
                "T": {
                    ("US", "US"): tUS_sUS_draw,
                    ("US", "UC"): tUS_sUC_draw,
                    ("US", "UP"): tUS_sUP_draw,
                    ("US", "EV"): tUS_sEV_draw,
                    ("UC", "US"): tUC_sUS_draw,
                    ("UC", "UC"): tUC_sUC_draw,
                    ("UC", "UP"): tUC_sUP_draw,
                    ("UC", "EV"): tUC_sEV_draw,
                    ("EV", "US"): tEV_sUS_draw,
                    ("EV", "UC"): tEV_sUC_draw,
                    ("EV", "UP"): tEV_sUP_draw,
                    ("EV", "EV"): tEV_sEV_draw,
                    ("EN", None): tEN_draw,  # Earliest-N temporal sampling
                },
                # Spatial-prioritised strategies
                "S": {
                    ("US", "US"): sUS_tUS_draw,
                    ("UC", "US"): sUS_tUC_draw,
                    ("EV", "US"): sUS_tEV_draw,
                    ("EN", "US"): sUS_tEN_draw,
                    ("US", "UC"): sUC_tUS_draw,
                    ("UC", "UC"): sUC_tUC_draw,
                    ("EV", "UC"): sUC_tEV_draw,
                    ("EN", "UC"): sUC_tEN_draw,
                    ("US", "UP"): sUP_tUS_draw,
                    ("UC", "UP"): sUP_tUC_draw,
                    ("EV", "UP"): sUP_tEV_draw,
                    ("EN", "UP"): sUP_tEN_draw,
                    ("US", "EV"): sEV_tUS_draw,
                    ("UC", "EV"): sEV_tUC_draw,
                    ("EV", "EV"): sEV_tEV_draw,
                    ("EN", "EV"): sEV_tEN_draw,
                },
                # Joint-prioritised strategies
                "J": {
                    ("US", None): stUS_draw,
                    ("UC", None): stUC_draw,
                    ("EV", None): stEV_draw,
                    ("EN", None): tEN_draw,  # Earliest-N temporal sampling
                },
            }

            # Get the mapping for the given allocation priority
            priority_map = draw_function_map.get(allocation_priority)
            if not priority_map:
                raise ValueError(f"Invalid allocation priority: {allocation_priority}")

            # Determine the key based on strategies
            strategy_key = (temporal_strategy, spatial_strategy)

            # Find the corresponding draw function
            draw_function = priority_map.get(strategy_key)
            if not draw_function:
                raise ValueError(
                    f"Invalid strategy combination: allocation_priority={allocation_priority}, "
                    f"temporal_strategy={temporal_strategy}, spatial_strategy={spatial_strategy}"
                )

            return draw_function

        # Get the appropriate draw function
        draw_function = get_draw_function(self.allocation_priority, self.temporal_strategy, self.spatial_strategy)

        # Extract relevant arguments for the draw function
        args, kwargs = get_relevant_args(draw_function, all_args)

        # Call the draw function
        return draw_function(*args, **kwargs)


# File upload functions for Inference model
def upload_inferred_tree_file_path(instance, filename):
    return os.path.join(settings.INFERENCE_FOLDER, str(instance.id), 'inferred.annotated.nwk')

# Return a random integer as seed
def generate_random_seed():
    return random.randint(0, 2**31 - 1)

# Model for phylogeographic inference given samples
class Inference(models.Model):
    """
    Model to store information about the phylogeographic inference given a set of samples, including the inference method, inferred migratory events, and the inferred tree.
    """
    class DTAInferenceMethods(models.TextChoices):
        TREETIME = "TT", _("Maximum-likelihood using TreeTime")
        PARSIMONY = "PH", _("Parsimony using phangorn")

    class StatusChoices(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        RUNNING = "RUNNING", _("Running")
        SUCCESS = "SUCCESS", _("Successful")
        FAILED = "FAILED", _("Failed")

    created_at = models.DateTimeField(auto_now_add=True)
    uuid = models.CharField(max_length=8, default=generate_short_uuid, unique=True, editable=False)
    samples_allocation = models.ForeignKey(SamplesAllocation, on_delete=models.CASCADE, blank=True, null=True)
    sample_ids = models.JSONField(blank=True, null=True) # IDs of samples used for inference
    inferred_migratory_events = models.JSONField(blank=True, null=True) # inferred migratory events
    inferred_tree_json = models.JSONField(blank=True, null=True) # inferred tree in JSON (nodes/links) format
    dta_method = models.CharField(max_length=2, choices=DTAInferenceMethods.choices, blank=True, null=True)
    inferred_tree_file = models.FileField(upload_to=upload_inferred_tree_file_path) # inferred tree file
    head = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='children') # previous inference used for iterative inference
    inference_chain = ArrayField(models.CharField(max_length=8), blank=True, null=True, default=list) # list of UUIDs of all inferences in the chain, from root to current
    note = models.CharField(max_length=300, blank=True, null=True) # note for the inference
    simulation = models.ForeignKey('simulations.Simulation', on_delete=models.CASCADE, blank=False, null=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    status = models.CharField(max_length=10, choices=StatusChoices.choices, default=StatusChoices.PENDING)
    evaluations = models.JSONField(blank=True, null=True) # evaluation metrics for the inference
    random_seed = models.PositiveIntegerField(default=generate_random_seed, blank=True, null=True) # random seed for reproducibility

    def __str__(self):
        return self.uuid
    
    # prevent saving a new instance with head == None if another instance with head == None already exists
    def save(self, *args, **kwargs):
        # check if this is a new instance (i.e., it doesn't have a primary key yet)
        if self._state.adding:
            # prevent creating a new instance with head=None if one already exists
            if self.head is None and Inference.objects.filter(simulation=self.simulation, head__isnull=True).exists():
                raise ValidationError("Only one root inference is allowed.")
        else:
            # if updating an existing instance, ensure that we are not introducing a second head=None
            if self.head is None and Inference.objects.exclude(pk=self.pk).filter(simulation=self.simulation, head__isnull=True).exists():
                raise ValidationError("Only one root inference is allowed.")

        # populate inference_chain
        if self.head is None:
            self.inference_chain = [self.uuid]
        else:
            # Take parent's chain and append this node's uuid
            self.inference_chain = self.head.inference_chain + [self.uuid]

        # Proceed with saving if validation passes
        super().save(*args, **kwargs)
        
    @property
    def depth(self):
        if not self.inference_chain:
            return 0
        return len(self.inference_chain) - 1
    
    # method to collect all sample IDs from previous inferences (not including the current one)
    def get_previous_samples(self):
        previous_samples = []
        current = self.head  # move to the parent
        while current:
            if current.sample_ids:
                previous_samples.extend(current.sample_ids)
            current = current.head  # move up to the next parent

        return previous_samples
    
    # method to read inferred_tree_file and return an ETE3 tree object with node attributes (deme as integer and time as float)
    def read_inferred_tree(self):
        # Check if inferred_tree_file exists
        if not self.inferred_tree_file:
            raise FileNotFoundError("Inferred tree file not found.")

        tree = Tree(self.inferred_tree_file.path, format=1)
        for node in tree.traverse():
            try:
                node.deme = int(node.deme)
                node.time = float(node.time)
            except AttributeError as e:
                raise ValueError(
                    f"Node '{node.name}' is missing required attributes 'deme' or 'time'."
                ) from e
            except ValueError as e:
                raise ValueError(
                    f"Node '{node.name}' has invalid attribute values for 'deme' or 'time'."
                ) from e
        return tree    
    
    # method to extract/populate inferred_tree_json (or thinned_inferred_tree_json) from inferred_tree_file
    def populate_inferred_tree_json(self, save: bool = True):
        inferred_tree = self.read_inferred_tree()

        # thin tree if the number of tips exceeds a certain threshold
        if len(inferred_tree.get_leaves()) > 8500:
            inferred_migratory_events = self.inferred_migratory_events
            inferred_tree = thin_tree(inferred_tree,
                                      inferred_migratory_events,
                                      target_size=8500,
                                      min_lineage_size=100,
                                      fuzziness=0.05,
                                      alpha=1.1)

        # run d3tree script
        tree_xy = run_d3tree(inferred_tree, reflect_xy=True)

        # construct final tree json
        inferred_tree_json = {}
        current_sample_ids = self.sample_ids or []
        for node in inferred_tree.traverse():
            inferred_tree_json[node.name] = {
                'x': tree_xy[node.name][0],
                'y': tree_xy[node.name][1],
                'deme': node.deme,
                'time': node.time,
                'brlen': node.dist,
                'up': node.up.name if node.up else None,
                'curr': node.name in current_sample_ids
            }

        # save inferred_tree_json if requested
        if save:
            self.inferred_tree_json = inferred_tree_json
            self.save()
        else:
            return inferred_tree_json
        
    # method to get sample counts from simulation
    def get_all_sample_counts_by_deme(self):
        # Check if samples have been drawn
        if self.sample_ids is None:
            raise ValueError("No samples have been drawn for inference.")

        # Get previous and current samples
        previous_samples = self.get_previous_samples() or []
        current_samples = self.sample_ids or []
        
        # Convert to sets for faster lookup
        current_samples_set = set(current_samples)
        previous_samples_set = set(previous_samples)
        
        # Get samples data from simulation (do this only once)
        samples_df = self.simulation.get_samples(by_day=True)
        
        # Setup for results
        duration_days = self.simulation.duration_days
        populations = self.simulation.populations
        
        # Initialize defaultdicts for all three result types
        current_deme_sample_counts = defaultdict(lambda: defaultdict(int))
        previous_deme_sample_counts = defaultdict(lambda: defaultdict(int))
        remaining_deme_sample_counts = defaultdict(lambda: defaultdict(int))
        
        # Group by deme and time
        grouped = samples_df.groupby(["deme", "time"])
        
        # Process each group to categorize samples
        for (deme, time), group in grouped:
            deme_int = int(deme)
            time_int = int(time)
            
            for sample_id in group["sample_id"]:
                if sample_id in current_samples_set:
                    current_deme_sample_counts[deme_int][time_int] += 1
                elif sample_id in previous_samples_set:
                    previous_deme_sample_counts[deme_int][time_int] += 1
                else:
                    remaining_deme_sample_counts[deme_int][time_int] += 1
        
        # Fill in missing days for all demes in all three result types
        deme_keys = populations.keys()
        
        # Process current samples
        current_results = {
            deme: [current_deme_sample_counts[int(deme)][t] for t in range(duration_days)]
            for deme in deme_keys
        }
        
        # Process previous samples
        previous_results = {
            deme: [previous_deme_sample_counts[int(deme)][t] for t in range(duration_days)]
            for deme in deme_keys
        }
        
        # Process remaining samples
        remaining_results = {
            deme: [remaining_deme_sample_counts[int(deme)][t] for t in range(duration_days)]
            for deme in deme_keys
        }
        
        return current_results, previous_results, remaining_results
    
    def calculate_samples_per_deme(self, include_all=True, proportion=False):
        # Check for dummy inference
        if self.dta_method is None:
            dummy_output = {deme: 0 for deme in range(self.simulation.num_demes)}
            if include_all:
                dummy_output['all'] = 0
            return dummy_output

        # Get previous and current samples
        previous_samples = self.get_previous_samples() or []
        current_samples = self.sample_ids or []
        all_samples = set(previous_samples + current_samples)
        
        # Get samples dataframe from simulation
        samples_df = self.simulation.get_samples()
        total_samples = len(samples_df)
        
        # Pre-calculate the mask for included samples
        included_mask = samples_df['sample_id'].isin(all_samples)
        included_samples_df = samples_df[included_mask]
        included_count = len(included_samples_df)
        
        # Calculate counts in one pass
        samples_per_deme = included_samples_df['deme'].value_counts().to_dict()
        
        # Initialize the result dictionary with zeros for all demes
        final_samples_per_deme = {deme: 0 for deme in range(self.simulation.num_demes)}
        
        if proportion:
            # Calculate total counts per deme
            total_samples_per_deme = samples_df['deme'].value_counts().to_dict()
            
            # Update with actual proportions where we have data
            for deme, count in samples_per_deme.items():
                deme_total = total_samples_per_deme.get(deme, 0)
                if deme_total > 0:
                    final_samples_per_deme[deme] = count / deme_total
            
            # Add the 'all' key if requested
            if include_all:
                final_samples_per_deme['all'] = included_count / total_samples if total_samples > 0 else 0
        else:
            # Update with actual counts
            final_samples_per_deme.update(samples_per_deme)
            
            # Add the 'all' key if requested
            if include_all:
                final_samples_per_deme['all'] = included_count
        
        return final_samples_per_deme

    # method to draw samples from simulation given samples_allocation
    def draw_samples(self, random_state: int = 42, save: bool = True):
        # Check if samples allocation is provided
        if self.samples_allocation is None:
            raise ValueError("No samples allocation provided for inference.")
        
        # Draw samples from simulation based on the allocation
        samples_df = self.samples_allocation.draw_samples(self.simulation, random_state=random_state)

        # Get all sample IDs from previous inferences
        previous_samples = self.get_previous_samples()

        # Filter out samples that have already been used
        samples_df = samples_df[~samples_df['sample_id'].isin(previous_samples)]

        # Save the sample IDs if requested
        sample_ids = samples_df['sample_id'].tolist()
        if save:
            self.sample_ids = sample_ids
            self.save()
        else:
            return sample_ids
    
    # method to get subsampled tree from simulation based on sample_ids
    def get_subsampled_tree(self):
        # Check that samples have been drawn
        if self.sample_ids is None:
            raise ValueError("No samples have been drawn for inference.")
        
        # Get all sample IDs, including those from previous inferences
        sample_ids = self.get_previous_samples() + self.sample_ids

        # Subsample tree from simulation
        subsampled_tree, node_attributes = self.simulation.subsample_tree(sample_ids=sample_ids,
                                                                          deannotate_tree=True,
                                                                          extract_attributes=True,
                                                                          attributes_format='dict')
        return subsampled_tree, node_attributes

    # method to run specified DTA method and save the inferred tree
    def run_dta_method(self):
        # Get subsampled tree
        subsampled_tree, node_attributes = self.get_subsampled_tree()

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.nwk', delete=True) as tree_file, \
            tempfile.NamedTemporaryFile(mode='w', suffix='.tsv', delete=True) as attributes_file:

            # Write subsampled tree
            subsampled_tree.write(outfile=tree_file.name, format=1, format_root_node=True)

            # Write node attributes to TSV file
            attributes_file.write("name\tdeme\n")
            for node, attributes in node_attributes.items():
                attributes_file.write(f"{node}\t{attributes['deme'] + 1}\n") # add 1 to make demes 1-indexed
            attributes_file.flush()  # ensure data is written before reading in subprocess

            # Run specified DTA method
            if self.dta_method == self.DTAInferenceMethods.TREETIME:
                pass
            elif self.dta_method == self.DTAInferenceMethods.PARSIMONY:
                inferred_annotations = run_phangorn_dta(tree_file.name, attributes_file.name)
                inferred_annotations = {node: deme - 1 for node, deme in inferred_annotations.items()} # subtract 1 to make demes 0-indexed; -1 for ambiguous deme
            else:
                raise ValueError(f"Invalid DTA method: {self.dta_method}")
        
            # Annotate subsampled tree with inferred demes
            for node in subsampled_tree.traverse():
                node.add_features(deme=inferred_annotations[node.name], time=node_attributes[node.name]['time'])

            # Save annotated tree as newick file (permanent)
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.nwk', delete=False) as inferred_tree_file:
                inferred_tree_filename = inferred_tree_file.name  # Store file name

                # Write the tree to the temp file
                subsampled_tree.write(outfile=inferred_tree_filename, format=1, format_root_node=True, features=["deme", "time"])

            # Open the temp file in read ('rb') mode before saving to Django's FileField
            with open(inferred_tree_filename, 'rb') as temp_file:
                self.inferred_tree_file.save(
                    upload_inferred_tree_file_path(self, "inferred.annotated.nwk"), 
                    File(temp_file)  # Wrap in Django's File object
                )

            # Delete temp file manually after saving
            os.remove(inferred_tree_filename)

    # method to get the deme and time of the root node of the inferred tree
    def get_inferred_root(self):
        inferred_tree = self.read_inferred_tree()
        return inferred_tree.deme, inferred_tree.time

    # method to enumerate migratory events/transmission lineages from the inferred tree
    def enumerate_migratory_events(self, extract_tls: bool = True, sort_by_time: bool = True, save: bool = True):
        # Read inferred tree
        inferred_tree = self.read_inferred_tree()

        # Enumerate migratory events/transmission lineages
        migratory_events = []
        for node in inferred_tree.traverse():
            if node.up and node.up.deme != node.deme:
                data = {
                    'origin_node': node.up.name,
                    'origin_deme': node.up.deme,
                    'origin_time': node.up.time,
                    'destination_node': node.name,
                    'destination_deme': node.deme,
                    'destination_time': node.time,
                    'ambiguous': node.up.deme == -1 or node.deme == -1
                }

                # Extract transmission lineages if requested
                if extract_tls:
                    root_deme = node.deme
                    members = []
                    size = 0
                    stack = [node]
                    latest_sample_time = -1
                    while stack:
                        current = stack.pop()
                        if current.deme != root_deme:
                            continue # stop traversal
                        members.append(current.name)
                        stack.extend(current.children) # add children to stack
                        size += 1 if current.is_leaf() else 0
                        latest_sample_time = max(latest_sample_time, current.time)
                    data['members'] = members
                    data['size'] = size
                    data['latest_sample_time'] = latest_sample_time

                # Assign unique ID
                data['id'] = len(migratory_events)

                migratory_events.append(data)

        # Sort the migratory events by (origin_time + destination_time) / 2 if requested
        if sort_by_time:
            migratory_events = sorted(migratory_events, key=lambda x: ((x['origin_time'] or 0) + x['destination_time']) / 2)

        # Save the inferred migratory events if requested
        if save:
            self.inferred_migratory_events = migratory_events
            self.save()
        else:
            return migratory_events

    # method to run the full inference pipeline
    def run_inference(self):
        try:
            # Draw samples
            self.draw_samples(random_state=self.random_seed)
            # Run DTA method
            self.run_dta_method()
            # Enumerate migratory events
            self.enumerate_migratory_events()
            # Populate inferred tree JSON
            self.populate_inferred_tree_json()
            # Evaluate inference
            self.evaluate()

            # Update status to success
            self.status = self.StatusChoices.SUCCESS
            self.save()

        except Exception as e:
            # Update status to failed
            self.status = self.StatusChoices.FAILED
            self.save()

            raise e

    # method to run inference evaluation (comparison with ground truth)
    def evaluate(self, save: bool = True):
        # Check if inferred_tree_file exists
        if not self.inferred_tree_file:
            raise FileNotFoundError("Inferred tree file not found.")

        # Get number of migratory events
        num_inferred_events = len(self.inferred_migratory_events)

        # Get time (TPMRCA, TMRCA) and source of earliest introduction for each deme
        inferred_earliest_introductions = {}
        for event in self.inferred_migratory_events:
            origin_deme = event['origin_deme']
            destination_deme = event['destination_deme']
            tpmrca = event['origin_time']
            tmrca = event['destination_time']
            if destination_deme not in inferred_earliest_introductions or tpmrca < inferred_earliest_introductions[destination_deme]['tpmrca']:
                inferred_earliest_introductions[destination_deme] = {
                    'tpmrca': tpmrca,
                    'tmrca': tmrca,
                    'source': origin_deme
                }

        # Add root of the tree as the earliest introduction for the root deme
        inferred_tree = self.read_inferred_tree()
        root_deme = inferred_tree.deme
        root_time = inferred_tree.time
        if root_deme >= 0: # ignore if root deme is ambiguous
            inferred_earliest_introductions[root_deme] = {
                'tpmrca': 0,
                'tmrca': root_time,
                'source': None
            }

        # Get earliest introductions from ground truth
        true_events = self.simulation.migratory_events
        true_earliest_introductions = {}
        for event in true_events:
            time, origin, destination = event
            if destination not in true_earliest_introductions or time < true_earliest_introductions[destination]['time']:
                true_earliest_introductions[destination] = {
                    'time': time,
                    'source': origin
                }
        # Add outbreak origin as the earliest introduction for the root deme
        true_earliest_introductions[self.simulation.outbreak_origin] = {
            'time': 0,
            'source': None
        }

        # Evaluate inferred events
        # Give score of 1 / (1 + |TMRCA - TPMRCA|) if [TPMRCA, TMRCA] includes the true values
        earliest_introductions_time_eval_count = 0
        earliest_introductions_time_eval_score = 0
        # Give score of 1 if source is correct
        earliest_introductions_source_eval_count = 0
        for deme, true_earliest_introduction in true_earliest_introductions.items():
            inferred_introduction = inferred_earliest_introductions.get(deme, None)
            if inferred_introduction:
                # Check if inferred (TPMRCA, TMRCA) includes the true values
                tpmrca_correct = true_earliest_introduction['time'] >= inferred_introduction['tpmrca']
                tmrca_correct = true_earliest_introduction['time'] <= inferred_introduction['tmrca']
                time_correct = tpmrca_correct and tmrca_correct
                # Check if the source is correct
                if inferred_introduction['source'] is not None:
                    source_correct = inferred_introduction['source'] == true_earliest_introduction['source']
                else:
                    source_correct = true_earliest_introduction['source'] == self.simulation.outbreak_origin
            else:
                time_correct = False
                source_correct = False

            # Update evaluation scores
            earliest_introductions_time_eval_count += 1 if time_correct else 0
            earliest_introductions_time_eval_score += 1 / (1 + abs(inferred_introduction['tmrca'] - inferred_introduction['tpmrca'])) if time_correct else 0
            earliest_introductions_source_eval_count += 1 if source_correct else 0

        # Normalize scores (consider only demes with true introductions)
        num_demes = len(true_earliest_introductions)
        earliest_introductions_time_eval_count /= num_demes
        earliest_introductions_time_eval_score /= num_demes
        earliest_introductions_source_eval_count /= num_demes

        # Collect all evaluation scores
        all_evals = {
            'sampling_props': self.calculate_samples_per_deme(include_all=True, proportion=True),
            'num_inferred_events': num_inferred_events,
            'prop_true_events_inferred': num_inferred_events / len(true_events),
            'earliest_intro_time_eval_count': earliest_introductions_time_eval_count,
            'earliest_intro_time_eval_score': earliest_introductions_time_eval_score,
            'earliest_intro_source_eval_count': earliest_introductions_source_eval_count
        }

        # Save evaluation scores if requested
        if save:
            self.evaluations = all_evals
            self.save()
        else:
            return all_evals