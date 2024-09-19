from django.db import models
from phone_field import PhoneField


class UserBot(models.Model):
    """
    Модель пользователя Telegram бота.
    """

    user_id = models.CharField(max_length=20, unique=True, verbose_name="ID Телеграма")
    full_name = models.CharField(max_length=100, verbose_name="ФИО")
    phone = PhoneField(blank=True, help_text="Телефон")
    address = models.CharField(
        max_length=200, null=True, blank=True, verbose_name="Адрес"
    )
    STATUS_CHOICES = [
        ("owner", "Владелец сервиса"),
        ("user", "Пользователь"),
        ("admin", "Админ"),
        ("manager", "Менеджер"),
        ("delivery", "Доставщик"),
    ]
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="user", verbose_name="Статус"
    )

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"


class Category(models.Model):
    """
    Модель категорий товаров.
    """

    name = models.CharField(max_length=50, verbose_name="Название категории")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Катагория"
        verbose_name_plural = "Категории"


class PriceRange(models.Model):
    """
    Модель ценовых категорий
    """

    min_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Минимальная цена",
    )
    max_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Максимальная цена",
    )

    def __str__(self):
        if self.min_price and self.max_price:
            return f"{self.min_price} - {self.max_price} руб"
        elif self.min_price:
            return f"от {self.min_price} руб"
        elif self.max_price:
            return f"до {self.max_price} руб"
        else:
            return "Без ограничения"

    class Meta:
        verbose_name = "Ценовой диапазон"
        verbose_name_plural = "Ценовые диапазоны"

    def get_products(self):
        if self.min_price and self.max_price:
            return Product.objects.filter(
                price__gte=self.min_price, price__lte=self.max_price
            )
        elif self.min_price:
            return Product.objects.filter(price__gte=self.min_price)
        elif self.max_price:
            return Product.objects.filter(price__lte=self.max_price)
        else:
            return Product.objects.all()


class Product(models.Model):
    """
    Модель товара.
    """

    id = models.AutoField(primary_key=True, editable=False)
    name = models.CharField(max_length=30, verbose_name="Название")
    description = models.TextField(max_length=300, verbose_name="Описание")
    price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Цена")
    categories = models.ManyToManyField(Category, verbose_name="Категории")
    image = models.ImageField(upload_to="static/products/", verbose_name="Изображение")
    STATUS_CHOICES = [
        ("active", "Актуальный"),
        ("archived", "Архивный"),
    ]
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="active", verbose_name="Статус"
    )

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

    def __str__(self):
        return self.name


class Order(models.Model):
    """
    Модель заказа.
    """

    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    user = models.ForeignKey(
        UserBot,
        on_delete=models.CASCADE,
        related_name="user_orders",
        verbose_name="Пользователь",
    )
    comment = models.TextField(
        max_length=300,
        verbose_name="Комментарий к заказу",
        null=True,
        blank=True,
    )
    delivery_address = models.CharField(max_length=200, verbose_name="Адрес доставки")
    desired_delivery_date = models.DateTimeField(
        verbose_name="Дата и время желаемой доставки"
    )
    creation_date = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата и время создания заказа"
    )
    STATUS_CHOICES = [
        ("created", "Создан"),
        ("inWork", "В работе"),
        ("inDelivery", "В доставке"),
        ("delivered", "Выдан клиенту"),
        ("cancelled", "Отменен"),
    ]
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default="created",
        verbose_name="Статус заказа",
    )
    delivery_date = models.DateTimeField(
        null=True, blank=True, verbose_name="Дата и время выдачи товара клиенту"
    )
    manager = models.ForeignKey(
        UserBot,
        on_delete=models.CASCADE,
        related_name="managed_orders",
        null=True,
        blank=True,
        verbose_name="Менеджер",
    )
    delivery_person = models.ForeignKey(
        UserBot,
        on_delete=models.CASCADE,
        related_name="delivery_orders",
        null=True,
        blank=True,
        verbose_name="Доставщик",
    )
    delivery_comments = models.TextField(
        null=True, blank=True, verbose_name="Комментарии к доставке"
    )

    def __str__(self):
        return f"Заказ {self.product.name} для {self.user.full_name}"

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
