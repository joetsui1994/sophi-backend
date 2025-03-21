from rest_framework import serializers
from .models import Simulation

# set fields dynamically depending on query_params or fields in post requests
class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        # Don't pass the 'fields' arg up to the superclass
        fields = kwargs.pop('fields', None)

        # Instantiate the superclass normally
        super(DynamicFieldsModelSerializer, self).__init__(*args, **kwargs)

        if fields is not None:
            # Drop any fields that are not specified in the `fields` argument.
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


# A serializer for the Simulation model
class SimulationSerializer(DynamicFieldsModelSerializer):
    total_population = serializers.SerializerMethodField()
    total_infected = serializers.SerializerMethodField()
    total_sampled = serializers.SerializerMethodField()
    deme_infected = serializers.SerializerMethodField()
    deme_sampled = serializers.SerializerMethodField()
    mobility_matrix = serializers.SerializerMethodField()  # override mobility_matrix field

    class Meta:
        model = Simulation
        fields = [
            'uuid',
            'name',
            'description',
            'created_at',
            'gamma',
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
            'deme_sampled'
            ]
        
    def get_total_population(self, obj):
        return obj.get_total_population()
    
    def get_total_infected(self, obj):
        return obj.get_total_infected()
    
    def get_total_sampled(self, obj):
        return obj.get_total_sampled()
    
    def get_deme_infected(self, obj):
        return obj.get_deme_infected()
    
    def get_deme_sampled(self, obj):
        return obj.get_deme_sampled()
    
    def get_mobility_matrix(self, obj):
        num_demes = obj.num_demes
        matrix = [[0 for _ in range(num_demes)] for _ in range(num_demes)]

        # populate matrix based on the long-format data
        for source, destination, value in obj.mobility_matrix:
            matrix[source][destination] = value

        return matrix