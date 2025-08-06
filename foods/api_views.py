from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from .models import Food, Price
from .serializers import FoodSerializer, FoodListSerializer, FoodSearchSerializer, PriceSerializer

class DatabaseAPIView(APIView):
    """
    /db/ 엔드포인트를 위한 API 뷰
    POST 방식으로 검색 쿼리를 받아 처리
    """
    
    def post(self, request):
        """
        POST 요청으로 검색 쿼리를 받아 식품을 검색합니다.
        """
        query = request.data.get('q', '')
        category = request.data.get('category', '')
        min_calorie = request.data.get('min_calorie')
        max_calorie = request.data.get('max_calorie')
        min_protein = request.data.get('min_protein')
        max_protein = request.data.get('max_protein')
        min_fat = request.data.get('min_fat')
        max_fat = request.data.get('max_fat')
        min_carbohydrate = request.data.get('min_carbohydrate')
        max_carbohydrate = request.data.get('max_carbohydrate')
        min_sodium = request.data.get('min_sodium')
        max_sodium = request.data.get('max_sodium')
        limit = request.data.get('limit', 20)
        sort_by = request.data.get('sort_by', 'nutrition_score')
        
        queryset = Food.objects.all()
        
        # 키워드 검색
        if query:
            queryset = queryset.filter(
                Q(food_name__icontains=query) | 
                Q(representative_food__icontains=query) |
                Q(food_category__icontains=query) |
                Q(company_name__icontains=query)
            )
        
        # 카테고리 필터
        if category:
            queryset = queryset.filter(food_category=category)
        
        # 영양소 범위 필터
        if min_calorie is not None:
            queryset = queryset.filter(calorie__gte=min_calorie)
        if max_calorie is not None:
            queryset = queryset.filter(calorie__lte=max_calorie)
        
        if min_protein is not None:
            queryset = queryset.filter(protein__gte=min_protein)
        if max_protein is not None:
            queryset = queryset.filter(protein__lte=max_protein)
        
        if min_fat is not None:
            queryset = queryset.filter(fat__gte=min_fat)
        if max_fat is not None:
            queryset = queryset.filter(fat__lte=max_fat)
        
        if min_carbohydrate is not None:
            queryset = queryset.filter(carbohydrate__gte=min_carbohydrate)
        if max_carbohydrate is not None:
            queryset = queryset.filter(carbohydrate__lte=max_carbohydrate)
        
        if min_sodium is not None:
            queryset = queryset.filter(salt__gte=min_sodium)
        if max_sodium is not None:
            queryset = queryset.filter(salt__lte=max_sodium)
        
        # 정렬
        if sort_by == 'nutrition_score':
            queryset = queryset.order_by('-nutrition_score')
        elif sort_by == 'calorie':
            queryset = queryset.order_by('calorie')
        elif sort_by == 'protein':
            queryset = queryset.order_by('-protein')
        elif sort_by == 'nrf_index':
            queryset = queryset.order_by('-nrf_index')
        else:
            queryset = queryset.order_by('-nutrition_score')
        
        # 제한
        if limit:
            queryset = queryset[:limit]
        
        serializer = FoodListSerializer(queryset, many=True)
        
        return Response({
            'status': 'success',
            'count': len(serializer.data),
            'query': query,
            'results': serializer.data
        })

class FoodViewSet(viewsets.ReadOnlyModelViewSet):
    """
    식품 정보를 조회하는 API
    """
    queryset = Food.objects.all()
    serializer_class = FoodListSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['food_category', 'company_name']
    search_fields = ['food_name', 'representative_food']
    ordering_fields = ['calorie', 'protein', 'fat', 'carbohydrate', 'nutrition_score', 'nrf_index']
    ordering = ['-nutrition_score']  # 기본 정렬: 영양 점수 높은 순

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return FoodSerializer
        return FoodListSerializer

    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        고급 검색 API
        """
        serializer = FoodSearchSerializer(data=request.query_params)
        if serializer.is_valid():
            queryset = Food.objects.all()
            
            # 키워드 검색
            query = serializer.validated_data.get('query')
            if query:
                queryset = queryset.filter(
                    Q(food_name__icontains=query) | 
                    Q(representative_food__icontains=query) |
                    Q(food_category__icontains=query)
                )
            
            # 카테고리 필터
            category = serializer.validated_data.get('category')
            if category:
                queryset = queryset.filter(food_category=category)
            
            # 영양소 범위 필터
            if serializer.validated_data.get('min_calorie'):
                queryset = queryset.filter(calorie__gte=serializer.validated_data['min_calorie'])
            if serializer.validated_data.get('max_calorie'):
                queryset = queryset.filter(calorie__lte=serializer.validated_data['max_calorie'])
            
            if serializer.validated_data.get('min_protein'):
                queryset = queryset.filter(protein__gte=serializer.validated_data['min_protein'])
            if serializer.validated_data.get('max_protein'):
                queryset = queryset.filter(protein__lte=serializer.validated_data['max_protein'])
            
            if serializer.validated_data.get('min_fat'):
                queryset = queryset.filter(fat__gte=serializer.validated_data['min_fat'])
            if serializer.validated_data.get('max_fat'):
                queryset = queryset.filter(fat__lte=serializer.validated_data['max_fat'])
            
            if serializer.validated_data.get('min_carbohydrate'):
                queryset = queryset.filter(carbohydrate__gte=serializer.validated_data['min_carbohydrate'])
            if serializer.validated_data.get('max_carbohydrate'):
                queryset = queryset.filter(carbohydrate__lte=serializer.validated_data['max_carbohydrate'])
            
            if serializer.validated_data.get('min_sodium'):
                queryset = queryset.filter(salt__gte=serializer.validated_data['min_sodium'])
            if serializer.validated_data.get('max_sodium'):
                queryset = queryset.filter(salt__lte=serializer.validated_data['max_sodium'])
            
            # 영양 점수 순으로 정렬
            queryset = queryset.order_by('-nutrition_score')
            
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = FoodListSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = FoodListSerializer(queryset, many=True)
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def top_nutrition(self, request):
        """
        영양 점수가 높은 상위 제품 조회
        """
        limit = int(request.query_params.get('limit', 10))
        queryset = Food.objects.filter(nutrition_score__isnull=False).order_by('-nutrition_score')[:limit]
        serializer = FoodListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """
        사용 가능한 카테고리 목록 조회
        """
        categories = Food.objects.values_list('food_category', flat=True).distinct()
        return Response(list(categories))

class PriceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    가격 정보를 조회하는 API
    """
    queryset = Price.objects.all()
    serializer_class = PriceSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['food', 'shop_name', 'is_available']

    @action(detail=False, methods=['get'])
    def by_food(self, request):
        """
        특정 식품의 가격 정보 조회
        """
        food_id = request.query_params.get('food_id')
        if food_id:
            queryset = Price.objects.filter(food__food_id=food_id, is_available=True)
            serializer = PriceSerializer(queryset, many=True)
            return Response(serializer.data)
        return Response({'error': 'food_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST) 