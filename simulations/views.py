from rest_framework.pagination import PageNumberPagination
from .serializers import SimulationSerializer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.conf import settings
from .models import Simulation


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
        # get the ordering parameter from the query
        ordering = request.query_params.get('ordering', None)
        descending = request.query_params.get('descending', 'false').lower() == 'true'
        allowed_ordering_fields = ['beta', 'gamma', 'delta', 'num_demes', 'duration_days', 'total_population', 'total_infected', 'total_sampled']

        # check if the ordering parameter is valid
        if ordering in allowed_ordering_fields:
            if descending:
                ordering = '-' + ordering
            simulation_queryset = Simulation.objects.filter(is_complete=True).order_by(ordering)
        else:
            simulation_queryset = Simulation.objects.filter(is_complete=True)

        # paginate the queryset
        page = self.paginate_queryset(simulation_queryset, request)

        if page is not None:
            serializer = SimulationSerializer(
                page,
                many=True,
                fields=('uuid', 'beta', 'gamma', 'delta', 'num_demes', 'duration_days', 'total_population', 'total_infected', 'total_sampled'))
            return self.get_paginated_response(serializer.data, request)
        
        serializer = SimulationSerializer(
            simulation_queryset,
            many=True,
            fields=('uuid', 'beta', 'gamma', 'delta', 'num_demes', 'duration_days', 'total_population', 'total_infected', 'total_sampled'))
        return Response(serializer.data)