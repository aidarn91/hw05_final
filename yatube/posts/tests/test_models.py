from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post, User

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Какой-то там текст',
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        post = PostModelTest.post
        group = PostModelTest.group
        expected_object_names = {
            post: post.text[:15],
            group: group.title,
        }
        for field, expected in expected_object_names.items():
            with self.subTest(field=field):
                self.assertEqual(str(field), expected)
