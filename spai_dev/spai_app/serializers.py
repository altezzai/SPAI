from django.conf import settings
from rest_framework import serializers
from datetime import datetime, timedelta
from .utils import get_registration_num
from .models import LifeMembers, User, UserDetailModel, PaymentModel, AnnualSubscriptionModel, SubscriptionPayment


class LifeMembersSerializer(serializers.ModelSerializer):
    membership_date = serializers.DateField(
        format="%d-%m-%Y",  # This is the desired output format
        input_formats=["%d.%m.%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%y","%d/%m/%y", "%d/%m/%Y"],
        required=False,
        allow_null=True
    )
    upload_date = serializers.DateTimeField(format="%d-%m-%Y %H:%M:%S", required=False)
    update_date = serializers.DateTimeField(format="%d-%m-%Y %H:%M:%S", required=False)

    def to_internal_value(self, data):
        for key, value in data.items():
            if isinstance(value, str):
                value = value.replace("\\", "\\\\")
            if value == "":
                data[key] = None
        return super().to_internal_value(data)

    class Meta:
        model = LifeMembers
        fields = ['reg_no', 'name', 'address', 'mobile', 'email', 'membership_date', 'upload_date', 'update_date',
                  'active', 'uid', 'lm_key']
        read_only_fields = ['upload_date', 'update_date']


# User direct ingestion API

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'last_name', 'state', 'annual_subscription',
                  'status', 'user_role', 'reg_no', 'admin_approved', 'date_approved', 'approval_percentage',
                  'active_key', 'original_date_approved', 'subscription_status', 'subscription_count']

    def create(self, validated_data):
        validated_data['status'] = settings.ADMIN_APPROVED
        validated_data['user_role'] = settings.MEMBER_ROLE_VALUE
        validated_data['admin_approved'] = True
        validated_data['approval_percentage'] = 100
        validated_data['active_key'] = True
        validated_data['president_approval'] = True
        validated_data['secretary_approval'] = True
        validated_data['original_date_approved'] = datetime.now()
        validated_data['reg_no'] = get_registration_num()
        cutoff_date = datetime(2025, 4, 1, 0, 0, 0)
        if datetime.now() < cutoff_date:
            validated_data['date_approved'] = cutoff_date
        else:
            validated_data['date_approved'] = datetime.now()
        return super().create(validated_data)


class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDetailModel
        fields = ['user', 'degree', 'profession', 'institution', 'department', 'address', 'phone_number',
                  'alternate_number',
                  'alternate_mail', 'specialized_in', 'research_interest']


class SubscriptionPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPayment
        fields = ['user', 'transaction_id', 'bank_name', 'payment_date', 'document', 'payment_id']


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentModel
        fields = ['user_info', 'transaction_id', 'reference_id', 'bank_name', 'payment_type', 'document']


class AnnualSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnnualSubscriptionModel
        fields = ['user', 'date_created', 'end_date', 'active']
