"""
Test for ingredients API
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Ingredient,
    Recipe,
)

from recipe.serializers import IngredientSerializer


INGREDIENTS_URL = reverse('recipe:ingredient-list')


def create_user(email='inuser@example.com', password='password123'):
    """create and return user."""
    return get_user_model().objects.create_user(email, password)


def create_ingredient(user, name):
    """create and return ingredient"""
    return Ingredient.objects.create(user=user, name=name)


def detail_url(ingredient_id):
    """Create and return an ingredient detail URL."""
    return reverse('recipe:ingredient-detail', args=[ingredient_id])


class PublicIngredientApiTests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required for retrieving ingredients."""
        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientApiTests(TestCase):
    """Test authenticated API requests"""

    def setUp(self) -> None:
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients(self):
        """Test retrieving a list of ingredients."""
        create_ingredient(self.user, 'Kale')
        create_ingredient(self.user, 'Vanilla')

        res = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        """Test list of ingredients is limited to authenticated user."""
        user2 = create_user(email='intwouser@example.com')
        create_ingredient(user=user2, name='Salt')
        ingredient = create_ingredient(user=self.user, name='Pepper')

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], ingredient.name)
        self.assertEqual(res.data[0]['id'], ingredient.id)

    def test_update_ingredient(self):
        """Test updating an ingredient."""
        ingredient = create_ingredient(user=self.user, name='Cilnatro')

        payload = {'name': 'Coriander'}
        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload['name'])

    def test_delete_ingredient(self):
        """Test deleting an ingredient."""
        ingredient = create_ingredient(user=self.user, name='Lettuce')

        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        ingredients = Ingredient.objects.filter(user=self.user)
        self.assertFalse(ingredients.exists())

    def test_filter_ingredients_assigned_to_recipes(self):
        """Test listing ingredients by those assigned to recipes."""
        in1 = create_ingredient(user=self.user, name='Apples')
        in2 = create_ingredient(user=self.user, name='Turkey')
        recipe = Recipe.objects.create(
            title='Apple Crumble',
            time_minutes=5,
            price=Decimal('4.50'),
            user=self.user
        )
        recipe.ingredients.add(in1)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        s1 = IngredientSerializer(in1)
        s2 = IngredientSerializer(in2)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_ingredients_unique(self):
        """Test filtered ingredients return a unique list."""
        ing = create_ingredient(user=self.user, name='Eggs')
        create_ingredient(user=self.user, name='Lentils')
        recipe1 = Recipe.objects.create(
            title='Eggs Benedict',
            time_minutes=60,
            price=Decimal('7.00'),
            user=self.user
        )
        recipe2 = Recipe.objects.create(
            title='Herb Eggs',
            time_minutes=20,
            price=Decimal('4.00'),
            user=self.user
        )
        recipe1.ingredients.add(ing)
        recipe2.ingredients.add(ing)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})
        self.assertEqual(len(res.data), 1)

    def tearDown(self) -> None:
        get_user_model().objects.get(email=self.user.email).delete()
        return super().tearDown()