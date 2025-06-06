from rest_framework import serializers
from django.db import transaction
from .models import (
    Service, Feature, PricingOption, PricingOptionFeature, 
    Question, QuestionOption, Contact, Purchase, GlobalSettings, SavedPricingPlan, QuestionsAndAnswers
)

class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = '__all__'




class QuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ['value', 'label', 'additional_price', 'order']


class QuestionSerializer(serializers.ModelSerializer):
    options = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False
    )
    
    
    class Meta:
        model = Question
        fields = ['id', 'text', 'type', 'unit_price', 'options', 'is_required', 'order']
        # extra_kwargs = {
        #     'id': {'read_only': True},
        #     'unit_price': {'source': 'unit_price'}
        # }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Include options in response
        if instance.type in ['choice', 'multiple_choice']:
            print("instance type: ",instance.options.all())
            data['options'] = [{opt.label:opt.value} for opt in instance.options.all()]
        return data


class FeatureSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    
    class Meta:
        model = Feature
        fields = ['id', 'name', 'description']


class SelectedFeatureSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    is_included = serializers.BooleanField()


class PricingOptionSerializer(serializers.ModelSerializer):
    selectedFeatures = SelectedFeatureSerializer(many=True, write_only=True, required=False)
    
    class Meta:
        model = PricingOption
        fields = [
            'id', 'name', 'discount', 'base_price', 
            'selectedFeatures', 'is_active'
        ]
        extra_kwargs = {
            'id': {'read_only': True}
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Include selected features in response
        selected_features = []
        for pof in instance.selected_features.all():
            selected_features.append({
                'id': pof.feature.id,
                'is_included': pof.is_included
            })
        data['selectedFeatures'] = selected_features
        return data


class ServiceSerializer(serializers.ModelSerializer):
    features = FeatureSerializer(many=True, required=False)
    pricingOptions = PricingOptionSerializer(many=True, write_only=True, required=False)
    questions = QuestionSerializer(many=True, required=False)
    minimumPrice = serializers.DecimalField(max_digits=10, decimal_places=2, write_only=True, required=False)

    class Meta:
        model = Service
        fields = [
            'id', 'name', 'description', 'minimumPrice',
            'features', 'pricingOptions', 'questions', 
            'is_active', 'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'id': {'read_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
        }

    def create(self, validated_data):
        # Handle both camelCase and snake_case
        pricing_options_data = validated_data.pop('pricingOptions', [])
        features_data = validated_data.pop('features', [])
        questions_data = validated_data.pop('questions', [])

        with transaction.atomic():
            # Create service
            service = Service.objects.create(
                name=validated_data['name'],
                description=validated_data.get('description', '')
            )

            # Create features
            feature_mapping = {}  # Map frontend IDs to actual Feature objects
            for feature_data in features_data:
                frontend_id = feature_data.pop('id', None)
                feature = Feature.objects.create(
                    service=service,
                    name=feature_data['name'],
                    description=feature_data.get('description', '')
                )
                if frontend_id:
                    feature_mapping[frontend_id] = feature

            # Create questions
            for question_data in questions_data:
                print("question data: ", question_data)
                options_data = question_data.pop('options', [])
                question = Question.objects.create(
                    service=service,
                    text=question_data['text'],
                    type=question_data['type'],
                    unit_price=question_data.get('unit_price', 0),
                    is_required=question_data.get('is_required', False),
                    order=question_data.get('order', 0)
                )
                for i, option_dict in enumerate(options_data):
                    key, value = list(option_dict.items())[0]  # Unpack the first (and only) key-value pair
                    QuestionOption.objects.create(
                        question=question,
                        value=value,
                        label=key,
                        order=i
                    )


            # Create pricing options
            for pricing_data in pricing_options_data:
                selected_features_data = pricing_data.pop('selectedFeatures', [])
                
                pricing_option = PricingOption.objects.create(
                    service=service,
                    name=pricing_data['name'],
                    discount=pricing_data.get('discount', 0),
                    base_price=pricing_data.get('base_price', 0),
                )

                # Link features to pricing options
                for selected_feature in selected_features_data:
                    feature_id = selected_feature['id']
                    if feature_id in feature_mapping:
                        PricingOptionFeature.objects.create(
                            pricing_option=pricing_option,
                            feature=feature_mapping[feature_id],
                            is_included=selected_feature['is_included']
                        )

        return service

    def update(self, instance, validated_data):
        # Handle both camelCase and snake_case
        pricing_options_data = validated_data.pop('pricingOptions', []) or validated_data.pop('pricing_options', [])
        features_data = validated_data.pop('features', [])
        questions_data = validated_data.pop('questions', [])

        with transaction.atomic():
            # Update service basic info
            instance.name = validated_data.get('name', instance.name)
            instance.description = validated_data.get('description', instance.description)
            instance.save()

            # Clear existing relationships
            instance.features.all().delete()
            instance.pricing_options.all().delete()
            instance.questions.all().delete()

            # Recreate features
            feature_mapping = {}
            for feature_data in features_data:
                frontend_id = feature_data.pop('id', None)
                feature = Feature.objects.create(
                    service=instance,
                    name=feature_data['name'],
                    description=feature_data.get('description', '')
                )
                if frontend_id:
                    feature_mapping[frontend_id] = feature

            # Recreate questions
            for question_data in questions_data:
                options_data = question_data.pop('options', [])
                question = Question.objects.create(
                    service=instance,
                    text=question_data['text'],
                    type=question_data['type'],
                    unit_price=question_data.get('unit_price', 0),
                    is_required=question_data.get('is_required', False),
                    order=question_data.get('order', 0)
                )
                print("option DataL ", options_data)
                for i, option_value in enumerate(options_data):
                    print(option_value)
                    key, value = list(option_value.items())[0]

                    QuestionOption.objects.create(
                        question=question,
                        value=value,
                        label=key,
                        order=i
                    )

            # Recreate pricing options
            for pricing_data in pricing_options_data:
                selected_features_data = (
                    pricing_data.pop('selectedFeatures', []) or 
                    pricing_data.pop('selected_features', [])
                )
                
                pricing_option = PricingOption.objects.create(
                    service=instance,
                    name=pricing_data['name'],
                    discount=pricing_data.get('discount', 0),
                    base_price=pricing_data.get('base_price', 0),
                )

                for selected_feature in selected_features_data:
                    feature_id = selected_feature['id']
                    if feature_id in feature_mapping:
                        PricingOptionFeature.objects.create(
                            pricing_option=pricing_option,
                            feature=feature_mapping[feature_id],
                            is_included=selected_feature['is_included']
                        )

        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Add pricing options for read operations
        pricing_options = []
        for po in instance.pricing_options.all():
            po_data = {
                'id': po.id,
                'name': po.name,
                'discount': po.discount,
                'base_price': po.base_price,
                'is_active': po.is_active,
                'selectedFeatures': []
            }
            # Add selected features
            for pof in po.selected_features.all():
                po_data['selectedFeatures'].append({
                    'id': pof.feature.id,
                    'is_included': pof.is_included
                })
            pricing_options.append(po_data)
        
        data['pricingOptions'] = pricing_options
        return data
    
class QuestionsAndAnswersSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionsAndAnswers
        exclude = ['purchase', 'question']
    
class QuestionWithAnswerSerializer(serializers.ModelSerializer):
    reactions = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ['id', 'text', 'type', 'unit_price', 'options', 'is_required', 'order', 'reactions']

    def get_reactions(self, obj):
        purchase = self.context.get('purchase')
        print(purchase, 'sss')
        if not purchase:
            return None
        try:
            answer = QuestionsAndAnswers.objects.filter(purchase=purchase, question=obj)
            return QuestionsAndAnswersSerializer(answer, many=True).data
        except QuestionsAndAnswers.DoesNotExist:
            return None
    
class ServiceWithQuestionsSerializer(serializers.ModelSerializer):
    features = FeatureSerializer(many=True, required=False)
    pricingOptions = PricingOptionSerializer(many=True, required=False)
    questions = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = ['id', 'name', 'description', 'features', 'pricingOptions', 'questions', 
            'is_active', 'created_at', 'updated_at']

    def get_questions(self, obj):
        purchase = self.context.get('purchase')
        questions = obj.questions.all()
        return QuestionWithAnswerSerializer(questions, many=True, context={'purchase': purchase}).data
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Add pricing options for read operations
        pricing_options = []
        for po in instance.pricing_options.all():
            po_data = {
                'id': po.id,
                'name': po.name,
                'discount': po.discount,
                'base_price': po.base_price,
                'is_active': po.is_active,
                'selectedFeatures': []
            }
            # Add selected features
            for pof in po.selected_features.all():
                po_data['selectedFeatures'].append({
                    'id': pof.feature.id,
                    'is_included': pof.is_included
                })
            pricing_options.append(po_data)
        
        data['pricingOptions'] = pricing_options
        return data


class SavedPricingPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedPricingPlan
        fields = '__all__'

class PurchaseDetailSerializer(serializers.ModelSerializer):
    contact = ContactSerializer()
    services = serializers.SerializerMethodField()
    price_plan = serializers.SerializerMethodField()

    class Meta:
        model = Purchase
        fields = ['id', 'contact', 'services', 'total_amount', 'price_plan', 'is_submited']

    def get_services(self, obj):
        return ServiceWithQuestionsSerializer(
            obj.services.all(),
            many=True,
            context={'purchase': obj}
        ).data

    def get_price_plan(self, instance):
        if instance.is_submited:
            spp = SavedPricingPlan.objects.filter(purchase=instance).first()
            if spp:
                return SavedPricingPlanSerializer(spp).data
        return instance.price_plan.id
    
class QuestionAnswerInputSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    qty = serializers.CharField()
    ans = serializers.BooleanField()

class ServiceWithAnswersInputSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    questions = QuestionAnswerInputSerializer(many=True)

class PurchaseCreateSerializer(serializers.Serializer):
    contact = serializers.SlugRelatedField(
        slug_field='contact_id',
        queryset=Contact.objects.all()
    )
    services = ServiceWithAnswersInputSerializer(many=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    price_plan = serializers.PrimaryKeyRelatedField(queryset=PricingOption.objects.all())
    is_submited = serializers.BooleanField(read_only=True)

    def create(self, validated_data):
        contact = validated_data['contact']
        total_amount = validated_data['total_amount']
        services_data = validated_data['services']
        price_plan = validated_data['price_plan']

        purchase = Purchase.objects.create(
            contact=contact,
            total_amount=total_amount,
            price_plan=price_plan
        )

        service_ids = []
        for service_data in services_data:
            service_id = service_data['id']
            service_ids.append(service_id)
            questions = service_data['questions']
            for q in questions:
                try:
                    question_obj = Question.objects.get(id=q['id'])
                    QuestionsAndAnswers.objects.create(
                        purchase=purchase,
                        question=question_obj,
                        qty=q['qty'],
                        ans=q['ans']
                    )
                except Question.DoesNotExist:
                    raise serializers.ValidationError(f"Question with id {q['id']} not found")

        purchase.services.set(service_ids)
        return purchase
    
class GlobalSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalSettings
        fields = '__all__'
    
    def update(self, instance, data):
        instance.minimum_price = data.get('minimum_price')
        instance.save()
        return instance