def thin_tree(tree, inferred_migratory_events, target_size, min_lineage_size=200, fuzziness=0.05, alpha=1.0):
    """
    Function to thin out an ETE3 tree with consideration of inferred transmission lineages.
    
    Parameters:
        tree: an ETE3 tree object
        inferred_migratory_events: list of dictionaries for transmission lineages
        target_size: desired final number of tree leaves
        min_lineage_size: minimum lineage size to qualify for thinning
        fuzziness: an additional thinning factor
        alpha: exponent to scale lineage sizes; alpha > 1 will thin larger lineages more aggressively
    """
    # get a list of all anchor nodes (i.e. origin_node and destionation_node) in the inferred_migratory_events
    origin_nodes = [event['origin_node'] for event in inferred_migratory_events]
    destination_nodes = [event['destination_node'] for event in inferred_migratory_events]
    anchor_nodes = set(origin_nodes + destination_nodes)
    
    # sort objects in inferred_migratory_events by size attribute and take only those with size >= min_lineage_size
    inferred_migratory_events = sorted(inferred_migratory_events, key=lambda x: x['size'], reverse=True)
    inferred_migratory_events = [event for event in inferred_migratory_events if event['size'] >= min_lineage_size]

    # get the total number of leaves in the lineages that qualify for thinning
    total_lineage_size = sum([event['size'] ** alpha for event in inferred_migratory_events])
    # calculate the overall thinning factor
    tree_size = len(tree.get_leaves())
    global_thinning_factor = (tree_size - target_size) / total_lineage_size

    # get a dictionary of all leaves in the tree, with the leaf name as the key and the leaf object as the value
    leaves = {leaf.name: leaf for leaf in tree.get_leaves()}

    # iterate over lineages
    for lineage in inferred_migratory_events:
        # calculate the number of leaves to remove from the lineage
        num_leaves_to_remove = int((global_thinning_factor + fuzziness) * (lineage['size'] ** alpha))

        while num_leaves_to_remove > 0:
            # recompute the dictionary of candidate leaves with updated distances
            lineage_leaf_dists = {
                leaf_name: leaves[leaf_name].dist
                for leaf_name in lineage['members']
                if leaf_name.startswith('leaf') and leaf_name in leaves
            }
            # re-sort the leaves based on the current distances
            sorted_lineage_leaves = sorted(lineage_leaf_dists, key=lineage_leaf_dists.get)

            # if there are no candidates left, break out of the loop
            if not sorted_lineage_leaves:
                break

            # iterate over leaves in the lineage
            for leaf_name in sorted_lineage_leaves:
                leaf = leaves[leaf_name]
                # check if parent node is an anchor node
                if leaf.up.name in anchor_nodes:
                    continue
                # remove the leaf from the tree
                leaf.delete(preserve_branch_length=True)
                num_leaves_to_remove -= 1
                # remove the pruned leaf from the leaves dictionary to avoid reprocessing
                del leaves[leaf_name]
                # break out of the for-loop if we've reached the target for this lineage
                if num_leaves_to_remove <= 0:
                    break
            
    return tree