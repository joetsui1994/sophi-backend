from rest_framework import serializers
from .models import SamplesAllocation, Inference


class SamplesAllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SamplesAllocation
        fields = [
            'id',
            'created_at', 
            'earliest_time', 'latest_time',
            'target_proportion', 'target_number', 'target_demes',
            'min_number',
            'temporal_strategy', 'spatial_strategy', 'allocation_priority',
            ]
        

class InferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inference
        fields = [
            "simulation",
            "samples_allocation",
            "head",
            "dta_method",
            "note",
            "status",
            "random_seed"
        ]
        extra_kwargs = {
            "random_seed": { "required": False, "allow_null": True },
        }


    def create(self, validated_data):
        # automatically assign the current user if not explicitly provided
        user = self.context['request'].user
        validated_data['user'] = user
            
        # Only set status to PENDING if no status is provided
        if 'status' not in validated_data:
            validated_data['status'] = Inference.StatusChoices.PENDING

        # if the user explicitly sent "random_seed": null or "random_seed": None, remove it
        # unless dta_method is None (i.e. a checkpoint)
        if "random_seed" in validated_data and validated_data["random_seed"] is None and validated_data["dta_method"] is not None:
            del validated_data["random_seed"]

        return super().create(validated_data)
    

class InferenceSimpleSerializer(InferenceSerializer):
    simulation_uuid = serializers.SerializerMethodField()

    class Meta(InferenceSerializer.Meta):
        fields = [
            'uuid',
            'simulation_uuid',
            'created_at',
            'status',
        ]

    def get_simulation_uuid(self, obj):
        return obj.simulation.uuid


class InferenceOverviewSerializer(InferenceSerializer):
    is_user_owner = serializers.SerializerMethodField()
    head_uuid = serializers.SerializerMethodField()
    prop_sampled = serializers.SerializerMethodField()
    samples_allocation = SamplesAllocationSerializer(read_only=True)

    class Meta(InferenceSerializer.Meta):  # Inherit from InferenceSerializer
        fields = [
            'uuid',
            'created_at',
            'dta_method',
            'depth',
            'prop_sampled',
            'samples_allocation',
            'head_uuid',
            'note',
            'evaluations',
            'is_user_owner',
            'status',
            'random_seed'
        ]
    
    def get_is_user_owner(self, obj):
        request = self.context.get('request')
        return bool(request and hasattr(request, 'user') and request.user == obj.user)

    def get_head_uuid(self, obj):
        return obj.head.uuid if obj.head else None
    
    def get_prop_sampled(self, obj):
        return obj.evaluations['sampling_props'] if obj.evaluations else None