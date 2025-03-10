from ete3 import Tree
import subprocess
import tempfile
import json
import os


def run_d3tree(inferred_tree, reflect_xy = False):
    """
    Function to run the D3Tree visualization tool on a tree JSON file.
    """
    def tree_to_json_dict(inferred_tree):
        def get_attrs(node):
            return {
                'name': node.name,
                'brlen': node.dist,
                'type': 'leaf' if node.is_leaf() else 'node'
            }

        def collect_children(node):
            children = [collect_children(child) for child in node.children]
            node_attrs = get_attrs(node)
            node_attrs['children'] = children
            return node_attrs

        return collect_children(inferred_tree)

    # convert inferred_tree to JSON format and store as tempfile
    tree_json = tree_to_json_dict(inferred_tree)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=True) as tree_json_file:
        json.dump(tree_json, tree_json_file)
        tree_json_file.flush()  # Ensure data is written

        # Build command
        node_script = os.path.join(os.path.dirname(__file__), 'd3tree', 'index.js')
        command = ['node', node_script, '-i', tree_json_file.name]

        # run the R script
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        if result.returncode != 0:
            raise RuntimeError("Error running js script:", result.stderr)

        # Parse the output
        output_json = json.loads(result.stdout)            
        tree_xy = { node['name']: (node['x'], node['y']) for node in output_json }

        # Rescale x and y to be between 0 and 1
        min_x = min(node['x'] for node in output_json)
        min_y = min(node['y'] for node in output_json)
        max_x = max(node['x'] for node in output_json)
        max_y = max(node['y'] for node in output_json)
        tree_xy = { node['name']: ((node['x'] - min_x) / (max_x - min_x), (node['y'] - min_y) / (max_y - min_y)) for node in output_json }

    # Reflex x and y if requested
    if reflect_xy:
        tree_xy = {
            name: (coords[1], -coords[0]) 
            for name, coords in tree_xy.items()
        }

    return tree_xy
