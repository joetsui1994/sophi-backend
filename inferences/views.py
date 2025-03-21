from .serializers import SamplesAllocationSerializer, InferenceSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from simulations.models import Simulation
from rest_framework.views import APIView
from rest_framework import status
# from celery import shared_task
from .models import Inference


class InferenceSubmission(APIView):
    permission_classes = [IsAuthenticated]  # Ensure only authenticated users can access this view

    def post(self, request, simulation_uuid, *args, **kwargs):
        # Fetch the simulation object
        simulation = get_object_or_404(Simulation, uuid=simulation_uuid)

        # Validate the sampling specs
        sampling_specs = request.data.get("sampling_specs")
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

        # Validate inference specs using the serializer
        inference_serializer = InferenceSerializer(data={
            "simulation": simulation.uuid,
            "samples_allocation": samples_allocation.id,
            "head": head_inference.id,
            "dta_method": inference_specs.get("dta_method"),
            "note": inference_specs.get("note"),
            "status": Inference.StatusChoices.PENDING,
            "random_seed": inference_specs.get("random_seed", None)
        }, context={"request": request})

        if not inference_serializer.is_valid():            
            return Response(inference_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Save the validated Inference object
        inference = inference_serializer.save()

        # Run the inference asynchronously
        # run_inference.delay(inference.id)
        inference.status = Inference.StatusChoices.RUNNING
        inference.save()
        inference.run_inference()

        # Return the created inference
        return Response({"message": "Inference created successfully.",}, status=status.HTTP_201_CREATED)


# @shared_task
# def run_inference(inference_id):
#     from .models import Inference  # Import here to avoid circular imports
#     import traceback

#     try:
#         inference = Inference.objects.get(id=inference_id)
#         inference.status = Inference.StatusChoices.RUNNING
#         inference.save()
#         inference.run_inference()
#     except Inference.DoesNotExist:
#         print(f"Inference with id '{inference_id}' not found.")
#     except Exception as e:
#         print(f"An error occurred while running inference with id '{inference_id}': {str(e)}")
#         traceback.print_exc()


@api_view(['GET'])
@permission_classes([IsAuthenticated]) # Ensure only authenticated users can access this view
def get_inference_data(request, uuid):
    inference = get_object_or_404(Inference, uuid=uuid)
    # check if the inference belongs to the current user, if head is not None (not a root inference)
    if inference.head is not None and inference.user != request.user:
        return Response({"error": "You do not have permission to access this inference."}, status=status.HTTP_403_FORBIDDEN)

    # get inferred (annotated) tree json
    inferred_tree_json = inference.inferred_tree_json
    # get inferred migratory events (with transmission lineages)
    inferred_migratory_events = inference.inferred_migratory_events

    # get inferred deme of inferred tree
    root_deme, root_time = inference.get_inferred_root()

    # get daily (drawn) sample counts by deme
    current_sample_counts_by_deme = inference.get_sample_counts(only_current=True, by_deme=True)
    # get daily (drawn in previous inferences) sample counts by deme
    previous_sample_counts_by_deme = inference.get_sample_counts(only_previous=True, by_deme=True)
    # get daily (undrawn) sample counts by deme
    remaining_sample_counts_by_deme = inference.get_sample_counts(only_unsampled=True, by_deme=True)

    # calculate total daily (drawn) sample counts
    total_current_samples = [sum(values) for values in zip(*current_sample_counts_by_deme.values())]
    # calculate total daily (drawn in previous inferences) sample counts
    total_previous_samples = [sum(values) for values in zip(*previous_sample_counts_by_deme.values())]
    # calculate total daily (undrawn) sample counts
    total_remaining_samples = [sum(values) for values in zip(*remaining_sample_counts_by_deme.values())]

    # clcaulte total sample number
    total_sample_num = sum(total_current_samples) + sum(total_previous_samples)

    return Response({
        'uuid': uuid,
        'head_uuid': inference.head.uuid if inference.head else None,
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