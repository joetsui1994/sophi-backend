from ete3 import Tree
import pandas as pd
import re


def read_nexus_tree(nexus_file: str, remove_singletons: bool = False) -> Tree:
    """
    Function to read a (annotated) tree (from output of REMASTER) in NEXUS format and return an ETE3 (annotated) tree object.
    Single-child nodes (representing migratory events) are removed if remove_singletons is True.
    """
    # read in the nexus tree file as a string
    with open(nexus_file, 'r') as f:
        nexus_str = f.read()

    # extract the Translate block
    translate_match = re.search(r"Translate\s+(.*?);", nexus_str, re.DOTALL)
    translate_block = translate_match.group(1).strip()
    # create a mapping of numeric IDs to taxon names
    translate_mapping = dict(re.findall(r"(\d+)\s+(\S+),", translate_block))

    # extract the tree block
    tree_match = re.search(r"tree\s+\S+\s*=\s*(.*);", nexus_str, re.DOTALL)
    tree_str = tree_match.group(1)

    # replace numeric IDs with taxon names only when followed by a comment
    def replace_id_with_taxon_names(match):
        num_id = match.group(1)
        comment = match.group(2)
        # replace only if the ID exists in the mapping
        if num_id in translate_mapping:
            return f"{translate_mapping[num_id]}{comment}"
        return match.group(0)  # leave unchanged if no mapping exists
    
    # replace numeric IDs with taxon names
    labelled_tree_str = re.sub(r"(\b\d+\b)(\[\&.*?\])", replace_id_with_taxon_names, tree_str)

    # add label to internal nodes
    internal_comment_pattern = re.compile(r'(\))(?::[^,\(\)\[]+)?(\[&type="I\{\d+\}",time=[\d.eE\-]+?\]:[\d.eE\-]+)')
    counter = 0 # counter to keep track of internal node labels
    def add_node_labels(match):
        nonlocal counter
        counter += 1
        return f"{match.group(1)}innode_{counter}{match.group(2)}"
    internal_labelled_tree_str = internal_comment_pattern.sub(add_node_labels, labelled_tree_str)

    # extract node attributes from comments
    node_comment_pattern = re.compile(r'(leaf_\d+|innode_\d+)\[&type="I\{(\d+)\}",time=([\d.]+)\]')
    node_attributes = {}
    for match in node_comment_pattern.finditer(internal_labelled_tree_str):
        node_name = match.group(1)          # leaf_xxx or innode_xxx
        node_type = int(match.group(2))     # the integer in I{xx}
        node_time = float(match.group(3))   # the float in time=...
        node_attributes[node_name] = {'deme': node_type, 'time': node_time}

    # remove node attributes from the tree string
    pattern_brackets = re.compile(r'\[&type="I\{\d+\}",time=[\d.eE-]+\]')
    # Replace each match with an empty string
    uncommented_tree_str = pattern_brackets.sub('', internal_labelled_tree_str).replace('\nEnd', '')

    # create a tree object from the newick string
    tree = Tree(uncommented_tree_str, format=1)

    # add node attributes to the tree object
    for node in tree.traverse():
        node_name = node.name
        if node_name in node_attributes:
            node.add_features(**node_attributes[node_name])

    # remove single-child nodes if requested
    if remove_singletons:
        for node in list(tree.traverse("preorder")):
            if len(node.children) == 1:
                node.children[0].dist += node.dist # add the distance to the child
                node.delete()

    return tree


def get_subsampled_tree(
        tree: Tree,
        sample_ids: list = None,
        deannotate_tree: bool = False,
        extract_attributes: bool = False,
        attributes_format: str = 'dataframe'
        ) -> Tree:
    """
    Function to subsample a tree based on a list of sample names.
    If deannotate_tree is True, the tree is deannotated (for performing DTA).
    If extract_attributes is True, the node attributes are extracted and
    returned as a DataFrame if attributes_format is 'dataframe', otherwise as a dictionary.
    """    
    # check if all samples are present in the tree
    existing_samples = set([leaf.name for leaf in tree.iter_leaves()])
    assert not sample_ids or set(sample_ids).issubset(existing_samples), "All specified samples must be present in the tree"

    # find the MRCA of the leaves to keep in the original tree
    mrca = tree.get_common_ancestor(sample_ids)

    # make a copy of the tree
    subsampled_tree = mrca.copy()
    
    # prune the copied subtree to retain only the desired leaves
    subsampled_tree.prune(sample_ids, preserve_branch_length=True)
    
    # Set the branch length of the new root (MRCA) to 0
    subsampled_tree.dist = 0
    
    # extract node attributes if extract_attributes is True
    if extract_attributes:
        node_attributes = {}
        for node in subsampled_tree.traverse():
            node_name = node.name
            node_attributes[node_name] = {'deme': node.deme, 'time': node.time}
        # convert node_attributes to a DataFrame if attributes_format is 'dataframe'
        if attributes_format == 'dataframe':
            node_attributes = pd.DataFrame([(node_name, node_attr['deme'], node_attr['time'])
                                            for node_name, node_attr in node_attributes.items()],
                                            columns=['name', 'deme', 'time'])

    # remove node attributes if deannotate_tree is True (for performing DTA)
    if deannotate_tree:
        for node in subsampled_tree.traverse():
            node.del_feature('deme')
            node.del_feature('time')

    return (subsampled_tree, node_attributes) if extract_attributes else subsampled_tree
            
