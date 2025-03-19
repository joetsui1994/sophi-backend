from inferences.serializers import InferenceSimpleSerializer
from django.contrib.auth.models import User
from rest_framework import serializers
from .models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ["institution", "country"]


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer()
    recent_inferences = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "profile", "date_joined", "recent_inferences"]

    def get_recent_inferences(self, obj):
        # Get the request from serializer context so we can check for a query parameter (if provided)
        request = self.context.get("request")
        num_recent = request.query_params.get("num_recent", 5) if request else 5
        # Check if num_recent is a valid integer, if not default to 5
        try:
            num_recent = int(num_recent)
        except ValueError:
            num_recent = 5

        # Retrieve the most recent inferences; assuming the related name is 'inference_set'
        recent = obj.inference_set.order_by("-created_at")[:num_recent]
        return InferenceSimpleSerializer(recent, many=True, context=self.context).data