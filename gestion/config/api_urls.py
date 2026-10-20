from rest_framework.routers import DefaultRouter

from catalog.api import CategoryViewSet, ProductViewSet, UnitOfMeasureViewSet

router = DefaultRouter()
router.register("productos", ProductViewSet, basename="product")
router.register("categorias", CategoryViewSet, basename="category")
router.register("unidades", UnitOfMeasureViewSet, basename="unit")

urlpatterns = router.urls
