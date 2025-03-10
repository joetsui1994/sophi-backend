import pandas as pd
import re


# def run_treetime_dta(tree_file: str, attributes_file: str, simulation_uuid: str, inference_id: int):
#     """
#     Function to run TreeTime to infer demes from a tree and save the annotated tree.
#     """
#     pass

def get_treetime_inferred_demes(nexus_file: str, format: str = 'dataframe'):
    """
    Function to extract inferred demes from an annotated tree (from output of TreeTime) in NEXUS format.
    Returns a DataFrame with columns 'node' and 'deme' if format is 'dataframe', otherwise a dictionary mapping node names to demes.
    """
    # read in the nexus tree file as a string
    with open(nexus_file, 'r') as f:
        nexus_str = f.read()

    # extract the tree block
    tree_match = re.search(r"tree\s+\S+\s*=\s*(.*);", nexus_str, re.DOTALL)
    tree_str = tree_match.group(1)

    # extract node attributes from comments
    pattern = re.compile(r'(\bleaf_\d+|\binnode_\d+):[\d.]+\[&deme="(\d+)"\]')
    deme_mapping = {match.group(1): int(match.group(2)) - 1 for match in pattern.finditer(tree_str)} # subtract 1 to make demes 0-indexed

    if format == 'dataframe':
        return pd.DataFrame(deme_mapping.items(), columns=['node', 'deme'])
    
    return deme_mapping