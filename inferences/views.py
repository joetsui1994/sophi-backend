from .serializers import SamplesAllocationSerializer, InferenceSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from simulations.models import Simulation
from rest_framework.views import APIView
from rest_framework import status
from celery import shared_task
from .models import Inference
import logging

logger = logging.getLogger(__name__)


class InferenceSubmission(APIView):
    permission_classes = [IsAuthenticated]  # Ensure only authenticated users can access this view

    def post(self, request, simulation_uuid, *args, **kwargs):
        # Fetch the simulation object
        simulation = get_object_or_404(Simulation, uuid=simulation_uuid)

        # Validate the sampling specs
        sampling_specs = request.data.get("sampling_specs")
        samples_allocation = None

        if sampling_specs is not None:
            samples_allocation_serializer = SamplesAllocationSerializer(data=sampling_specs)
            if not samples_allocation_serializer.is_valid():
                return Response(samples_allocation_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
            # Create the SamplesAllocation instance
            samples_allocation = samples_allocation_serializer.save()

        # Validate inference specs
        inference_specs = request.data.get("inference_specs")
        head_uuid = inference_specs.get("head")
        if not head_uuid:
            return Response({"error": "'head' field is required for inference submission."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the specified head inference
        head_inference = get_object_or_404(Inference, uuid=head_uuid, simulation=simulation)

        # Get replicate_num (defaults to 1)
        replicate_num = inference_specs.get("replicate_num", 1)
        if replicate_num < 1:
            return Response({"error": "'replicate_num' must be >= 1."}, status=status.HTTP_400_BAD_REQUEST)

        for _ in range(replicate_num):
            inference_serializer = InferenceSerializer(data={
                "simulation": simulation.uuid,
                "samples_allocation": samples_allocation.id if samples_allocation else None,
                "head": head_inference.id,
                "dta_method": inference_specs.get("dta_method"),
                "note": inference_specs.get("note"),
                "status": Inference.StatusChoices.PENDING if samples_allocation else Inference.StatusChoices.SUCCESS,
                "random_seed": inference_specs.get("random_seed", None)
            }, context={"request": request})

            if not inference_serializer.is_valid():            
                return Response(inference_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # Save the validated Inference object
            inference = inference_serializer.save()

            # Run the inference asynchronously only if sampling specs are provided
            if samples_allocation:
                run_inference.delay(inference.id)

        # Return the created inference
        return Response({"message": "Inference created successfully.",}, status=status.HTTP_201_CREATED)


@shared_task
def run_inference(inference_id):
    from .models import Inference  # Import here to avoid circular imports

    try:
        inference = Inference.objects.get(id=inference_id)
        inference.status = Inference.StatusChoices.RUNNING
        inference.save()

        logger.info(f"Started inference: {inference_id}")

        inference.run_inference()

        logger.info(f"Inference completed: {inference_id}")

    except Inference.DoesNotExist:
        logger.error(f"Inference with id '{inference_id}' not found.")

    except Exception as e:
        logger.exception(f"Error running inference {inference_id}: {str(e)}")

        try:
            inference.status = Inference.StatusChoices.FAILED
            inference.save(update_fields=["status"])
        except Exception:
            logger.warning(f"Could not mark inference {inference_id} as FAILED")


@api_view(['GET'])
@permission_classes([IsAuthenticated]) # Ensure only authenticated users can access this view
def get_inference_data(request, uuid):
    inference = get_object_or_404(Inference, uuid=uuid)

    # check if the inference belongs to the current user, if head is not None (not a root inference)
    if inference.head is not None and inference.user != request.user:
        return Response({"error": "You do not have permission to access this inference."}, status=status.HTTP_403_FORBIDDEN)

    try:
        # get inferred (annotated) tree json
        inferred_tree_json = inference.inferred_tree_json
        # get inferred migratory events (with transmission lineages)
        inferred_migratory_events = inference.inferred_migratory_events

        # get inferred deme of inferred tree
        root_deme, root_time = inference.get_inferred_root()

        # get daily (current, previous, and remaining) sample counts by deme
        current_sample_counts_by_deme, previous_sample_counts_by_deme, remaining_sample_counts_by_deme = inference.get_all_sample_counts_by_deme()

        # calculate total daily (drawn) sample counts
        total_current_samples = [sum(values) for values in zip(*current_sample_counts_by_deme.values())]
        # calculate total daily (drawn in previous inferences) sample counts
        total_previous_samples = [sum(values) for values in zip(*previous_sample_counts_by_deme.values())]
        # calculate total daily (undrawn) sample counts
        total_remaining_samples = [sum(values) for values in zip(*remaining_sample_counts_by_deme.values())]

        # calculate total sample number
        total_sample_num = sum(total_current_samples) + sum(total_previous_samples)

        return Response({
            'uuid': uuid,
            'head_uuid': inference.head.uuid if inference.head else None,
            'inference_chain': inference.inference_chain,
            'inferred_tree': inferred_tree_json,
            'inferred_migratory_events': inferred_migratory_events,
            'inferred_root': {
                'deme': root_deme,
                'time': root_time
            },
            'total_sample_num': total_sample_num,
            'sample_counts': {
                'by_deme': {
                    deme: {
                        'current': current_sample_counts_by_deme[deme],
                        'previous': previous_sample_counts_by_deme[deme],
                        'remaining': remaining_sample_counts_by_deme[deme]
                    } for deme in current_sample_counts_by_deme.keys()
                },
                'total': {
                    'current': total_current_samples,
                    'previous': total_previous_samples,
                    'remaining': total_remaining_samples
                }
            }
        })
    
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_inference(request, uuid):
    inference = get_object_or_404(Inference, uuid=uuid)
    
    # Check if inference belongs to user
    if inference.user != request.user:
        return Response({'error': 'Not authorized to delete this inference'}, status=403)
        
    # Check if inference status allows deletion
    if inference.status not in [Inference.StatusChoices.SUCCESS, Inference.StatusChoices.FAILED]:
        return Response({'error': 'Can only delete completed or failed inferences'}, status=400)
        
    # Check if there are any pending or running inferences that are descendants of this inference
    protected_downstream_inferences = Inference.objects.filter(
        simulation=inference.simulation,
        status__in=[Inference.StatusChoices.PENDING, Inference.StatusChoices.RUNNING],
        inference_chain__contains=[inference.uuid])

    if protected_downstream_inferences.exists():
        return Response({'error': 'Cannot delete this inference because it has pending or running descendants'}, status=400)

    # Delete the inference
    inference.delete()
    return Response(status=204)