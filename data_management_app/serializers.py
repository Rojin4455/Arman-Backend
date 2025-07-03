from rest_framework import serializers
from django.db import transaction
from .models import (
    Service, Feature, PricingOption, PricingOptionFeature, 
    Question, QuestionOption, Contact, Purchase, GlobalSettings, PurchasedService, QuestionsAndAnswers, QuestionOptionAnswers,PurChasedServiceFeature,
    PurchasedServicePlan, PlanFeature, CustomProduct, Address
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
        if instance.type in ['choice', 'multiple_choice', 'extra_choice']:
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
        from data_management_app.models import GlobalSettings  # Adjust if it's in a different app
        try:
            settings = GlobalSettings.load()  # `load()` is a standard method for SingletonModel
            data['minimum_price'] = settings.minimum_price
        except GlobalSettings.DoesNotExist:
            data['minimum_price'] = None
        return data
    
class QuestionOptionAnswersSerializer(serializers.ModelSerializer):
    class Meta:
        model=QuestionOptionAnswers
        fields=['qty', 'value', 'label']

    def get_question_option(self, instance):
        if instance.qu_ans.question_type == 'choice':
            return QuestionOptionSerializer(instance.question_option).data
        return None

    
class QuestionsAndAnswersSerializer(serializers.ModelSerializer):
    options = serializers.SerializerMethodField()
    class Meta:
        model = QuestionsAndAnswers
        fields = ['options', 'bool_ans', 'question_name', 'question_type', 'unit_price']

    def get_options(self, obj):
        option_answers = QuestionOptionAnswers.objects.filter(qu_ans=obj)
        return QuestionOptionAnswersSerializer(option_answers, many=True).data
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['type']=data['question_type']
        data['text']=data['question_name']
        return data
    
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
        
class PurChasedServiceFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurChasedServiceFeature
        fields = '__all__'
    
class ServiceWithQuestionsSerializer(serializers.ModelSerializer):
    features = FeatureSerializer(many=True, required=False)
    price_plan = serializers.SerializerMethodField()
    pricingOptions = PricingOptionSerializer(many=True, required=False)
    questions = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = ['id', 'name', 'description', 'features', 'pricingOptions', 'price_plan', 'questions', 
            'is_active', 'created_at', 'updated_at']

    def get_questions(self, obj):
        purchase = self.context.get('purchase')
        questions = obj.questions.all()
        q_ans=QuestionsAndAnswers.objects.filter(purchase=purchase)
        return QuestionsAndAnswersSerializer(q_ans, many=True).data
    
    def get_price_plan(self, instance):
        purchase = self.context.get('purchase')
        print(purchase, 'll')
        spp = PurchasedService.objects.filter(purchase=purchase, service=instance).first()
        print(spp, 'ddd')
        if purchase.is_submited:
            pricing_options = PurChasedServiceFeatureSerializer(spp.service_feature.all(), many=True).data
            print(pricing_options, 'priiggg')
        return PurchasedServiceSerializer(spp).data
    
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
    
class PurchasedServicePlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchasedServicePlan
        fields = '__all__'

class PlanFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanFeature
        fields = '__all__'


class PurchasedServiceSerializer(serializers.ModelSerializer):
    features = serializers.SerializerMethodField()
    pricingOptions = serializers.SerializerMethodField()
    price_plan = serializers.SerializerMethodField()
    questions = serializers.SerializerMethodField()
    class Meta:
        model = PurchasedService
        exclude = ['purchase']

    def get_features(self, obj):
        if not obj.selected_plan:
            return []

        # Get related PlanFeatures
        features = obj.selected_plan.plan_feat.select_related('feature')

        return [
            {
                'id': pf.feature.id,
                'name': pf.feature.name,
                'description': pf.feature.description,
            }
            for pf in features
        ]

    def get_questions(self, obj):
        purchase = self.context.get('purchase')
        q_ans=QuestionsAndAnswers.objects.filter(purchase=purchase, purchased_service=obj)
        return QuestionsAndAnswersSerializer(q_ans, many=True).data
    
    def get_pricingOptions(self, instance):
        return PurChasedServiceFeatureSerializer(instance.service_feature.all(), many=True).data
    
    def get_price_plan(self, instance):
        return PurchasedServicePlanSerializer(instance.service_feature_plans.all(), many=True).data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        pricing_options = []
        for po in instance.service_feature_plans.all():
            po_data = {
                'id': po.id,
                'name': po.name,
                'discount': po.discount,
                'selectedFeatures': []
            }
            # Add selected features
            for pof in po.plan_feat.all():
                po_data['selectedFeatures'].append({
                    'id': pof.feature.id,
                    'name':pof.feature.name,
                    'is_included': pof.is_included
                })
            pricing_options.append(po_data)
          
        data['pricingOptions'] = pricing_options
        data['name'] = data['service_name']
        data['price_plan'] = data['selected_plan']
        return data

class PurchaseDetailSerializer(serializers.ModelSerializer):
    contact = ContactSerializer()
    services = serializers.SerializerMethodField()
    custom_products = serializers.SerializerMethodField()

    class Meta:
        model = Purchase
        fields = ['id', 'contact', 'services', 'total_amount', 'is_submited', 'signature', 'custom_products']

    def get_services(self, obj):
        return PurchasedServiceSerializer(
            obj.service_plans.all(),
            many=True,
            context={'purchase': obj}
        ).data
    
    def get_custom_products(self, obj):
        custom_products = obj.custom_products.all()
        return CustomProductSerializer(custom_products, many=True).data
        
    def to_representation(self, instance):
        data = super().to_representation(instance)
        from data_management_app.models import GlobalSettings  # Adjust if it's in a different app
        try:
            settings = GlobalSettings.load()  # `load()` is a standard method for SingletonModel
            data['minimum_price'] = settings.minimum_price
        except GlobalSettings.DoesNotExist:
            data['minimum_price'] = None
        return data
    
class QuestionAnswerInputSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    ans = serializers.BooleanField()
    options = serializers.DictField(
        child=serializers.IntegerField(),
        required=False
    )

class ServiceWithAnswersInputSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    price_plan = serializers.PrimaryKeyRelatedField(queryset=PricingOption.objects.all())
    questions = QuestionAnswerInputSerializer(many=True)

class CustomProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomProduct
        exclude = ['purchase']

class PurchaseCreateSerializer(serializers.Serializer):
    contact = serializers.SlugRelatedField(
        slug_field='contact_id',
        queryset=Contact.objects.all()
    )
    address = serializers.PrimaryKeyRelatedField(queryset=Address.objects.all())
    services = ServiceWithAnswersInputSerializer(many=True,required=False)
    custom_products = CustomProductSerializer(many=True, required=False)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    is_submited = serializers.BooleanField(read_only=True)

    def validate(self, data):
        services = data.get('services', [])
        custom_products = data.get('custom_products', [])

        if not services and not custom_products:
            raise serializers.ValidationError(
                "At least one of 'services' or 'custom_products' must be provided."
            )
        return data

    def create(self, validated_data):
        contact = validated_data['contact']
        address = validated_data['address']
        total_amount = validated_data['total_amount']
        services_data = validated_data['services']
        custom_products = validated_data.get('custom_products', [])

        purchase = Purchase.objects.create(
            contact=contact,
            address=address,
            total_amount=total_amount,
        )

        for service in services_data:
            service_id = service['id']
            service_obj = Service.objects.get(id=service_id)
            pricing_plan = service['price_plan']

            purchased_service_obj=PurchasedService.objects.create(
                purchase=purchase,
                service_name=service_obj.name,
                description=service_obj.description
            )

            print(pricing_plan, 'pricinggggddd')

            pricing_options = PricingOption.objects.filter(service=service_obj)
            selected_plan = None
            for option in pricing_options:
                print(option, 'optionn')
                purchased_pricing_plan_obj = PurchasedServicePlan.objects.create(purchased_service=purchased_service_obj, name=option.name, discount=option.discount)
                features = pricing_plan.selected_features.all()
                for feat in features:
                    p_feat_obj=PurChasedServiceFeature.objects.create(purchased_service=purchased_service_obj, name=feat.feature.name, description=feat.feature.description)

                    PlanFeature.objects.create(purchased_service_plan=purchased_pricing_plan_obj, feature=p_feat_obj, is_included=feat.is_included)     
                if option == pricing_plan:
                    print('selected', option)
                    selected_plan = purchased_pricing_plan_obj
            
            purchased_service_obj.selected_plan = selected_plan
            purchased_service_obj.save()



            questions = service['questions']
            for q in questions:
                try:
                    question_obj = Question.objects.get(id=q['id'])
                    if question_obj.type=='boolean':
                        QuestionsAndAnswers.objects.create(
                            purchase=purchase,
                            purchased_service=purchased_service_obj,
                            bool_ans=q['ans'],
                            question_name=question_obj.text,
                            question_type=question_obj.type,
                            unit_price=question_obj.unit_price
                        )
                    elif question_obj.type=='extra_choice':
                        qu_ans = QuestionsAndAnswers.objects.create(
                            purchase=purchase,
                            purchased_service=purchased_service_obj,
                            bool_ans=q['ans'],
                            question_name=question_obj.text,
                            question_type=question_obj.type,
                            unit_price=question_obj.unit_price
                        )
                        options_data = q.get('options', {})
                        for key, value in options_data.items():
                            try:
                                question_opt_obj = QuestionOption.objects.get(question=question_obj, label__iexact=key)
                                QuestionOptionAnswers.objects.create(
                                    qu_ans=qu_ans,
                                    label=question_opt_obj.label,
                                    value=question_opt_obj.value,
                                )
                            except QuestionOption.DoesNotExist:
                                raise serializers.ValidationError(
                                    f"QuestionOption '{key}' not found for Question ID {question_obj.id}"
                                )
                    else:
                        qu_ans = QuestionsAndAnswers.objects.create(
                            purchase=purchase,
                            purchased_service=purchased_service_obj,
                            bool_ans=q['ans'],
                            question_name=question_obj.text,
                            question_type=question_obj.type,
                            unit_price=question_obj.unit_price
                        )
                        options_data = q.get('options', {})
                        for key, value in options_data.items():
                            try:
                                question_opt_obj = QuestionOption.objects.get(question=question_obj, label__iexact=key)
                                QuestionOptionAnswers.objects.create(
                                    qu_ans=qu_ans,
                                    qty=value,
                                    label=question_opt_obj.label,
                                    value=question_opt_obj.value,
                                )
                            except QuestionOption.DoesNotExist:
                                raise serializers.ValidationError(
                                    f"QuestionOption '{key}' not found for Question ID {question_obj.id}"
                                )
                except Question.DoesNotExist:
                    raise serializers.ValidationError(f"Question with id {q['id']} not found")
        if custom_products:
            print(custom_products, 'hiii')
            for custom_product in custom_products:
                CustomProduct.objects.create(purchase=purchase, product_name=custom_product.get('product_name'), description=custom_product.get('description'), price=custom_product.get('price'))
        else:
            print('nOO custom product')

        return purchase
    
    def update(self, instance, validated_data):
        services_data = validated_data.get('services', [])
        custom_products = validated_data.get('custom_products', [])

        for service in services_data:
            service_id = service['id']
            service_obj = Service.objects.get(id=service_id)
            pricing_plan = service['price_plan']

            purchased_service_obj = PurchasedService.objects.create(
                purchase=instance,
                service_name=service_obj.name,
                description=service_obj.description
            )

            pricing_options = PricingOption.objects.filter(service=service_obj)
            selected_plan = None
            for option in pricing_options:
                purchased_pricing_plan_obj = PurchasedServicePlan.objects.create(
                    purchased_service=purchased_service_obj,
                    name=option.name,
                    discount=option.discount
                )

                features = pricing_plan.selected_features.all()
                for feat in features:
                    p_feat_obj = PurChasedServiceFeature.objects.create(
                        purchased_service=purchased_service_obj,
                        name=feat.feature.name,
                        description=feat.feature.description
                    )
                    PlanFeature.objects.create(
                        purchased_service_plan=purchased_pricing_plan_obj,
                        feature=p_feat_obj,
                        is_included=feat.is_included
                    )
                if option == pricing_plan:
                    selected_plan = purchased_pricing_plan_obj

            purchased_service_obj.selected_plan = selected_plan
            purchased_service_obj.save()

            for q in service['questions']:
                try:
                    question_obj = Question.objects.get(id=q['id'])
                    if question_obj.type == 'boolean':
                        QuestionsAndAnswers.objects.create(
                            purchase=instance,
                            purchased_service=purchased_service_obj,
                            bool_ans=q['ans'],
                            question_name=question_obj.text,
                            question_type=question_obj.type,
                            unit_price=question_obj.unit_price
                        )
                    elif question_obj.type == 'extra_choice':
                        qu_ans = QuestionsAndAnswers.objects.create(
                            purchase=instance,
                            purchased_service=purchased_service_obj,
                            bool_ans=q['ans'],
                            question_name=question_obj.text,
                            question_type=question_obj.type,
                            unit_price=question_obj.unit_price
                        )
                        for key, value in q.get('options', {}).items():
                            question_opt_obj = QuestionOption.objects.get(question=question_obj, label__iexact=key)
                            QuestionOptionAnswers.objects.create(
                                qu_ans=qu_ans,
                                label=question_opt_obj.label,
                                value=question_opt_obj.value
                            )
                    else:
                        qu_ans = QuestionsAndAnswers.objects.create(
                            purchase=instance,
                            purchased_service=purchased_service_obj,
                            bool_ans=q['ans'],
                            question_name=question_obj.text,
                            question_type=question_obj.type,
                            unit_price=question_obj.unit_price
                        )
                        for key, value in q.get('options', {}).items():
                            question_opt_obj = QuestionOption.objects.get(question=question_obj, label__iexact=key)
                            QuestionOptionAnswers.objects.create(
                                qu_ans=qu_ans,
                                label=question_opt_obj.label,
                                value=question_opt_obj.value,
                                qty=value
                            )
                except Question.DoesNotExist:
                    raise serializers.ValidationError(f"Question with id {q['id']} not found")

        for product in custom_products:
            CustomProduct.objects.create(
                purchase=instance,
                product_name=product.get('product_name'),
                description=product.get('description'),
                price=product.get('price')
            )

        return instance
        
class GlobalSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalSettings
        fields = '__all__'
    
    def update(self, instance, data):
        instance.minimum_price = data.get('minimum_price')
        instance.save()
        return instance
    
class FinalSubmissionServicePlanSerializer(serializers.Serializer):
    service_id = serializers.IntegerField()
    price_plan = serializers.PrimaryKeyRelatedField(queryset=PurchasedServicePlan.objects.all())
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    
class FinalSubmissionSerializer(serializers.Serializer):
    purchase_id = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    signature = serializers.CharField()
    services = FinalSubmissionServicePlanSerializer(many=True)

    def validate(self, data):
        # Optional: check if purchase exists and is not already submitted
        try:
            purchase = Purchase.objects.get(id=data['purchase_id'])
            if purchase.is_submited:
                raise serializers.ValidationError("Purchase is already submitted.")
        except Purchase.DoesNotExist:
            raise serializers.ValidationError("Purchase not found.")
        return data

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = '__all__'