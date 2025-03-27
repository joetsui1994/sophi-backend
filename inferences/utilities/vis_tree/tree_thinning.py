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
    anchor_nodes = set(origin_nodes + destination_nodes + [tree.get_tree_root().name])
    
    # get the initial tree size
    initial_tree_size = len(tree.get_leaves())

    # check if we need to thin the tree at all
    if initial_tree_size <= target_size:
        return tree
    
    # get a dictionary of all leaves in the tree, with the leaf name as the key and the leaf object as the value
    all_leaves = {leaf.name: leaf for leaf in tree.get_leaves()}

    # identify all lineage members
    lineage_members = set()
    for event in inferred_migratory_events:
        lineage_members.update(event.get('members', []))

    # identify leaves that are not part of any lineage
    exterior_leaves = {
        name: leaf for name, leaf in all_leaves.items() 
        if name not in lineage_members and name.startswith('leaf')
    }

    # get lineages that qualify for thinning and sort them by size
    sorted_inferred_migratory_events = sorted(
        [event for event in inferred_migratory_events if event['size'] >= min_lineage_size],
        key=lambda x: x['size'], reverse=True
    )

    # calculate the thinning target for the exterior leaves and the lineages
    total_weighted_lineage_size = sum([event['size'] ** alpha for event in sorted_inferred_migratory_events])
    weighted_exterior_size = len(exterior_leaves) ** alpha
    global_thinning_factor = (initial_tree_size - target_size) / (total_weighted_lineage_size + weighted_exterior_size)

    # thin the exterior leaves
    num_to_remove = int(global_thinning_factor * weighted_exterior_size)
    # track leaves we've already evaluated but couldn't remove
    skipped_leaves = set()
    while num_to_remove > 0:
        # get leaves we haven't skipped yet
        available_leaves = {
            name: leaf.dist 
            for name, leaf in exterior_leaves.items()
            if name not in skipped_leaves
        }

        if not available_leaves:
            break

        # sort leaves by branch length
        sorted_leaves = sorted(available_leaves, key=available_leaves.get)

        # flag to check if we removed any in this iteration
        removed_any = False

        for leaf_name in sorted_leaves:
            if leaf_name not in exterior_leaves:
                continue

            leaf = exterior_leaves[leaf_name]

            # skip leaves whose parent is an anchor node and mark as skipped
            if leaf.up.name in anchor_nodes:
                skipped_leaves.add(leaf_name)
                continue

            # remove the leaf
            leaf.delete(preserve_branch_length=True)
            num_to_remove -= 1
            del exterior_leaves[leaf_name]  # remove from our tracking dictionary
            removed_any = True

            # update the master list of leaves
            if leaf_name in all_leaves:
                del all_leaves[leaf_name]

            # break if we've reached our target
            if num_to_remove <= 0:
                break

        # if we didn't remove any leaves in this pass, we're stuck
        if not removed_any:
            break

    # thin the lineages
    for lineage in sorted_inferred_migratory_events:
        num_to_remove = int(global_thinning_factor * (lineage['size'] ** alpha))
        # track leaves we've already evaluated but couldn't remove
        skipped_leaves = set()
        while num_to_remove > 0:
            # get leaves we haven't skipped yet
            available_leaves = {
                name: leaf.dist 
                for name, leaf in all_leaves.items()
                if name in lineage['members'] and name not in skipped_leaves
            }

            if not available_leaves:
                break

            # sort leaves by branch length
            sorted_leaves = sorted(available_leaves, key=available_leaves.get)

            # flag to check if we removed any in this iteration
            removed_any = False

            for leaf_name in sorted_leaves:
                if leaf_name not in all_leaves:
                    continue

                leaf = all_leaves[leaf_name]

                # skip leaves whose parent is an anchor node
                if leaf.up.name in anchor_nodes:
                    skipped_leaves.add(leaf_name)
                    continue

                # remove the leaf
                leaf.delete(preserve_branch_length=True)
                num_to_remove -= 1
                del all_leaves[leaf_name]
                removed_any = True

                # break if we've reached our target
                if num_to_remove <= 0:
                    break

            # if we didn't remove any leaves in this pass, we're stuck
            if not removed_any:
                break

    return tree