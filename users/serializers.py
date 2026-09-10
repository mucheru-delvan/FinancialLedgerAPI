from django.contrib.auth import authenticate
from django.db import transaction
from rest_framework import serializers

from accounts.models import Account
from users.models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
    )

    class Meta:
        model = User
        fields = ["email", "name", "password"]

    @transaction.atomic
    def create(self, validated_data):
        """
        Create a user and their initial KES account atomically.
        """
        #Create the user and create their account as one operation. 
        # If either operation fails, neither is saved to the database.
        user = User.objects.create_user(
            email=validated_data["email"],
            name=validated_data["name"],
            password=validated_data["password"],
        )

        Account.objects.create(
            user=user,
            currency="KES",
            status="active",
        )

        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "name", "created_at"]


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """
        Authenticate the user and reject inactive accounts.
        """
        email = attrs["email"]
        password = attrs["password"]

        user = authenticate(
            username=email,
            password=password,
        )

        if not user:
            raise serializers.ValidationError(
                "Invalid email or password."
            )

        if not user.is_active:
            raise serializers.ValidationError(
                "This account is inactive."
            )

        attrs["user"] = user

        return attrs