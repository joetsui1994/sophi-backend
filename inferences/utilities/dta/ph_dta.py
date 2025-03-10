import subprocess
import os


def run_phangorn_dta(tree_file: str, attributes_file: str):
    """
    Function to run phangorn to infer demes from a tree and save the annotated tree.
    """
    # path to the R script
    r_script = os.path.join(os.path.dirname(__file__), 'run_phangorn_dta.R')

    # arguments to the R script
    args = ['-t', tree_file, '-a', attributes_file, '-c', 'deme']

    # run the R script
    command = ['Rscript', r_script] + args
    result = subprocess.run(command, capture_output=True, text=True, check=True)

    if result.returncode != 0:
        raise RuntimeError("Error running R script:", result.stderr)
    else:
        # Parse the TSV output from stdout
        annotations = dict([x.split('\t') for x in result.stdout.splitlines()])
        annotations = {k: int(v) if v != '' else 0 for k, v in annotations.items()} # 0 for ambiguous deme

        return annotations