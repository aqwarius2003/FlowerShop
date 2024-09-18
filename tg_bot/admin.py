from django.contrib import admin

from .models import Category, Order, PriceRange, Product, UserBot


@admin.register(UserBot)
class UserBotAdmin(admin.ModelAdmin):
    list_display = (
        "user_id",
        "full_name",
        "phone",
        "address",
        "status",
    )  # Параметры для отображения в списке
    search_fields = (
        "user_id",
        "full_name",
        "phone",
    )  # Поля, по которым будет происходить поиск
    list_filter = ("status",)  # Фильтр по статусу
    ordering = ("user_id",)  # Сортировка по user_id


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)  # Отображение только названия категории
    search_fields = ("name",)  # Поиск по названию категории


@admin.register(PriceRange)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("min_price", "max_price", "get_price_range")

    def get_price_range(self, obj):
        if obj.min_price and obj.max_price:
            return f"{obj.min_price} - {obj.max_price} руб"
        elif obj.min_price:
            return f"от {obj.min_price} руб"
        elif obj.max_price:
            return f"до {obj.max_price} руб"
        else:
            return "Без ограничения"

    get_price_range.short_description = "Ценовой диапазон"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "status")  # Параметры для отображения в списке
    search_fields = ("name", "description")  # Поля для поиска
    list_filter = ("status", "categories")  # Фильтр по статусу и категориям
    ordering = ("name",)  # Сортировка по названию
    filter_horizontal = (
        "categories",
    )  # Для удобного выбора категорий в ManyToMany поле


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "user",
        "status",
        "creation_date",
        "desired_delivery_date",
        "manager",
        "delivery_person",
    )
    search_fields = ("product__name", "user__full_name", "delivery_address")
    list_filter = ("status", "creation_date")
    ordering = ("-creation_date",)
    date_hierarchy = "creation_date"

    # Фильтрация пользователей по статусу для полей Менеджер и Доставщик
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "manager":
            # Фильтруем только тех пользователей, которые являются менеджерами
            kwargs["queryset"] = UserBot.objects.filter(status__in=["admin", "manager"])
        elif db_field.name == "delivery_person":
            # Фильтруем только тех пользователей, которые являются доставщиками
            kwargs["queryset"] = UserBot.objects.filter(status="delivery")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
