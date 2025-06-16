from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from inferences.serializers import InferenceOverviewSerializer
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission
from django.shortcuts import get_object_or_404
from .serializers import SimulationSerializer
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from .models import Simulation
from django.db.models import Q

from rest_framework.exceptions import PermissionDenied


# Custom permission to allow unauthenticated access for demo simulations
class AllowUnauthenticatedForDemo(BasePermission):
    """
    Custom permission to allow unauthenticated access for demo simulations
    """
    def has_permission(self, request, view):
        # Extract simulation UUID from the URL or request data
        simulation_uuid = None
        
        # For inference deletion, you might need to get simulation UUID from the inference
        if 'inference_uuid' in view.kwargs:
            try:
                from .models import Inference  # Adjust import
                inference = Inference.objects.get(uuid=view.kwargs['inference_uuid'])
                simulation_uuid = inference.simulation.uuid
            except Inference.DoesNotExist:
                return False
        
        # For direct simulation access
        elif 'simulation_uuid' in view.kwargs:
            simulation_uuid = view.kwargs['simulation_uuid']
        
        if simulation_uuid:
            try:
                simulation = Simulation.objects.get(uuid=simulation_uuid)
                # If it's a demo simulation, allow access regardless of authentication
                if 'demo' in simulation.keywords:
                    return True
            except Simulation.DoesNotExist:
                return False
        
        # For non-demo simulations, require authentication
        return request.user and request.user.is_authenticated


class CustomSetPagination(PageNumberPagination):
    page_size = settings.DEFAULT_PAGE_SIZE
    page_size_query_param = 'page_size'
    max_page_size = settings.MAX_PAGE_SIZE


class SimulationRepository(APIView, CustomSetPagination):
    permission_classes = [AllowAny]  # Allow access to anyone

    def get_paginated_response(self, data, request):
        return Response(dict([
            ('count', self.page.paginator.count),
            ('max_page', self.page.paginator.num_pages),
            ('current', self.page.number),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('page_size', self.get_page_size(request)),
            ('results', data)
        ]))

    def get(self, request, format=None):
        # get the search parameter from the query
        search = request.query_params.get('search', None)
        
        # get the ordering parameter from the query
        ordering = request.query_params.get('ordering', None)
        descending = request.query_params.get('descending', 'false').lower() == 'true'
        allowed_ordering_fields = ['num_demes', 'duration_days', 'total_population', 'total_infected', 'total_sampled']

        # start with base queryset
        simulation_queryset = Simulation.objects.filter(is_complete=True)

        # apply search filter if search parameter exists
        if search:
            if search.startswith('#'):
                search = search[1:]  # remove the hash
                simulation_queryset = simulation_queryset.filter(uuid__startswith=search)
            else:
                simulation_queryset = simulation_queryset.filter(keywords__overlap=[search])

        # apply ordering if valid
        if ordering in allowed_ordering_fields:
            if descending:
                ordering = '-' + ordering
            simulation_queryset = simulation_queryset.order_by(ordering)

        # paginate the queryset
        page = self.paginate_queryset(simulation_queryset, request)

        if page is not None:
            serializer = SimulationSerializer(
                page,
                many=True,
                fields=('uuid', 'num_demes', 'duration_days', 'total_population', 'total_infected', 'total_sampled'))
            return self.get_paginated_response(serializer.data, request)
        
        serializer = SimulationSerializer(
            simulation_queryset,
            many=True,
            fields=('uuid', 'num_demes', 'duration_days', 'total_population', 'total_infected', 'total_sampled'))
        return Response(serializer.data)
    

@api_view(['GET'])
@permission_classes([AllowAny])  # Allow access to anyone
def get_simulation_data(request, simulation_uuid):    
    simulation = get_object_or_404(Simulation, uuid=simulation_uuid)
    serializer = SimulationSerializer(
        simulation,
        fields=(
            'uuid',
            'name',
            'description',
            'created_at',
            'keywords',
            'num_demes',
            'duration_days',
            'populations',
            'sampling_times',
            'mobility_matrix',
            'case_incidence',
            'total_population',
            'total_infected',
            'total_sampled',
            'deme_infected',
            'deme_sampled')
    )

    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowUnauthenticatedForDemo]) # Ensure only authenticated users can access this view
def get_inference_tree(request, simulation_uuid):
    simulation = get_object_or_404(Simulation, uuid=simulation_uuid)

    # get user
    request_user = request.user if request.user.is_authenticated else None
    # get inference tree
    inference_tree = simulation.get_inference_tree(user=request_user)
    # get UUID of most recent 3 inferences
    recent_inferences = simulation.get_recent_inferences(user=request_user, N=3)

    # get inference queryset and serialize
    inferences = (
        simulation.inference_set.filter(Q(user=request_user) | Q(head__isnull=True))
        .select_related('samples_allocation', 'head')
    )
    serializer = InferenceOverviewSerializer(inferences, many=True)

    # convert the serializer output from a list to a dictionary with UUIDs as keys
    inferences_dict = { item['uuid']: item for item in serializer.data }

    return Response({
        'simulation_uuid': simulation_uuid,
        'tree': inference_tree,
        'recent_inferences': recent_inferences,
        'inferences': inferences_dict
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated]) # Ensure only authenticated users can access this view
def get_migratory_event_counts(request, simulation_uuid):
    simulation = get_object_or_404(Simulation, uuid=simulation_uuid)

    # get request params (deme, deme_pair, show_importation)
    deme = request.query_params.get('deme', None)
    deme_pair = request.query_params.get('deme_pair', None)
    show_importation = request.query_params.get('show_importation', 'true').lower() != 'false'
    rolling_window = request.query_params.get('rolling_window', 7)

    if deme_pair is not None:
        # get migration counts for a deme pair
        deme1, deme2 = deme_pair.split('-')
        # with rolling average
        migratory_event_counts_ra = simulation.get_migratory_event_counts(
            demes=[int(deme1), int(deme2)],
            event_type='transfer',
            rolling_window=rolling_window)
        # without rolling average
        migratory_event_counts_raw = simulation.get_migratory_event_counts(
            demes=[int(deme1), int(deme2)],
            event_type='transfer')
    else:
        if deme is None:
            # get migration counts summed across all demes
            # with rolling average
            all_migratory_event_counts_ra = simulation.get_migratory_event_counts(
                event_type='import' if show_importation else 'export',
                rolling_window=rolling_window)
            # without rolling average
            all_migratory_event_counts_raw = simulation.get_migratory_event_counts(
                event_type='import' if show_importation else 'export')
            # sum the counts across all
            migratory_event_counts_ra = list(map(sum, zip(*all_migratory_event_counts_ra.values())))
            migratory_event_counts_raw = list(map(sum, zip(*all_migratory_event_counts_raw.values())))
        else:
            # get migration counts for a single deme
            # with rolling average
            migratory_event_counts_ra = simulation.get_migratory_event_counts(
                demes=[int(deme)],
                event_type='import' if show_importation else 'export',
                rolling_window=rolling_window)[int(deme)]
            # without rolling average
            migratory_event_counts_raw = simulation.get_migratory_event_counts(
                demes=[int(deme)],
                event_type='import' if show_importation else 'export')[int(deme)]
            
    return Response({
        'simulation_uuid': simulation_uuid,
        'event_type': 'transfer' if deme_pair is not None else 'import' if show_importation else 'export',
        'demes': list(map(int, deme_pair.split('-'))) if deme_pair is not None else [int(deme)] if deme is not None else None,
        'migratory_event_counts_ra': migratory_event_counts_ra,
        'migratory_event_counts_raw': migratory_event_counts_raw,
        'rolling_window': rolling_window
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated]) # Ensure only authenticated users can access this view
def get_earliest_introductions(request, simulation_uuid):
    simulation = get_object_or_404(Simulation, uuid=simulation_uuid)

    # get earliest importation events for each deme
    earliest_introductions = simulation.get_earliest_importation()
    return Response({
        'simulation_uuid': simulation_uuid,
        'earliest_introductions': earliest_introductions
    })