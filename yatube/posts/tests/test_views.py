import shutil
import tempfile

from django.conf import settings
from django import forms
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache

from ..models import Post, Group, Follow

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
small_gif = (
    b'\x47\x49\x46\x38\x39\x61\x01\x00'
    b'\x01\x00\x00\x00\x00\x21\xf9\x04'
    b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
    b'\x00\x00\x01\x00\x01\x00\x00\x02'
    b'\x02\x4c\x01\x00\x3b'
)
uploaded = SimpleUploadedFile(
    name='small.gif',
    content=small_gif,
    content_type='image/gif'
)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='test_name')
        cls.group = Group.objects.create(
            title='test_group',
            slug='test_slug',
            description='Проверка описания',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=Group.objects.get(slug='test_slug'),
            image=uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_uses_correct_template(self, *args, **kwargs):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list',
                kwargs={'slug': PostPagesTests.group.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile',
                kwargs={'username': PostPagesTests.user.username}
            ): 'posts/profile.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse(
                'posts:post_detail',
                kwargs={'post_id': PostPagesTests.post.id}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit',
                kwargs={'post_id': PostPagesTests.post.id}
            ): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def check_context(self, response_post):
        self.assertEqual(response_post.author, self.post.author)
        self.assertEqual(response_post.group, self.group)
        self.assertEqual(response_post.text, self.post.text)
        self.assertEqual(response_post.image, self.post.image)

    def test_index_pages_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        post_text_0 = first_object.text
        post_author_0 = first_object.author.username
        post_group_0 = first_object.group.title
        self.assertEqual(post_text_0, 'Тестовый текст')
        self.assertEqual(post_author_0, 'test_name')
        self.assertEqual(post_group_0, 'test_group')

    def test_group_pages_show_correct_context(self):
        """Шаблон группы"""
        response = self.authorized_client.get(reverse(
            'posts:group_list', kwargs={'slug': 'test_slug'}
        ))
        first_object = response.context['group']
        group_title_0 = first_object.title
        group_slug_0 = first_object.slug
        self.assertEqual(group_title_0, 'test_group')
        self.assertEqual(group_slug_0, 'test_slug')

    def test_post_another_group(self):
        """Пост не попал в другую группу"""
        response = self.authorized_client.get(
            reverse('posts:group_list',
                    kwargs={'slug': 'test_slug'}
                    ))
        first_object = response.context['page_obj'][0]
        post_text_0 = first_object.text
        self.assertTrue(post_text_0, 'Тестовый текст')

    def test_new_post_show_correct_context(self):
        """Шаблон сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_profile_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом"""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': 'test_name'}
                    ))
        first_object = response.context['page_obj'][0]
        post_text_0 = first_object.text
        self.assertEqual(response.context['author'].username, 'test_name')
        self.assertEqual(post_text_0, 'Тестовый текст')

    def test_detail_page_show_correct_context(self):
        """Шаблон post_detail.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}))
        first_object = response.context['post']
        post_author_0 = first_object.author.username
        post_text_0 = first_object.text
        group_slug_0 = first_object.group.slug
        self.assertEqual(post_author_0, 'test_name')
        self.assertEqual(post_text_0, 'Тестовый текст')
        self.assertEqual(group_slug_0, 'test_slug')


class PostPaginatorTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_name1')
        cls.group = Group.objects.create(
            title='test_group1',
            slug='test_slug1',
            description='Тестовое описание1',
        )
        cls.posts = [
            Post(
                author=cls.user,
                text=f'Тестовый пост {post_number}',
                group=cls.group,
            )
            for post_number in range(13)
        ]
        Post.objects.bulk_create(cls.posts)

        cls.paginator_list = {
            'posts:index': reverse('posts:index'),
            'posts:group_list': reverse(
                'posts:group_list',
                kwargs={'slug': 'test_slug1'}
            ),
            'posts:profile': reverse(
                'posts:profile',
                kwargs={'username': 'test_name1'}
            ),
        }

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_first_page_contains_ten_posts(self):
        for template_, reverse_name in self.paginator_list.items():
            response = self.guest_client.get(reverse_name)
            self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_contains_ten_posts(self):
        for template_, reverse_name in self.paginator_list.items():
            response = self.guest_client.get(reverse_name, {'page': 2})
            self.assertEqual(len(response.context['page_obj']), 3)


class Cache(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Тестовый пользователь')
        cls.group = Group.objects.create(slug='test-slug')

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_cache(self):
        Post.objects.create(author=self.user,
                            text='Тестовый пост',
                            group=self.group)
        self.authorized_client.get(reverse('index'))
        response = self.authorized_client.get(reverse('index'))
        self.assertEqual(response.context, None)
        cache.clear()
        response = self.authorized_client.get(reverse('index'))
        self.assertNotEqual(response.context, None)
        self.assertEqual(response.context['page'][0].text, 'Тестовый пост')


class TestFollow(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUser')
        cls.group = Group.objects.create(title='TestGroup',
                                         slug='test_slug',
                                         description='Test description')
        cls.follow_user = User.objects.create_user(username='TestAuthor')

    def setUp(self):
        self.authorized_user = Client()
        self.authorized_user.force_login(self.follow_user)

    def test_follow(self):
        self.authorized_user.get(reverse('profile_follow',
                                 kwargs={'username': self.user.username}))
        follow = Follow.objects.first()
        self.assertEqual(Follow.objects.count(), 1)
        self.assertEqual(follow.author, self.user)
        self.assertEqual(follow.user, self.follow_user)

    def test_unfollow(self):
        self.authorized_user.get(reverse('profile_follow',
                                 kwargs={'username': self.user.username}))
        self.authorized_user.get(reverse('profile_unfollow',
                                         kwargs={
                                             'username': self.user.username}))
        self.assertFalse(Follow.objects.exists())

    def test_follow_index(self):
        Post.objects.create(author=self.user, text='Тестовый текст вот так',
                            group=self.group)
        Follow.objects.create(user=self.follow_user, author=self.user)
        response = self.authorized_user.get(reverse('follow_index'))
        post = response.context['post']
        self.assertEqual(post.text, 'Тестовый текст вот так')
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.group.id, self.group.id)

    def test_unfollow_index(self):
        Post.objects.create(author=self.user, text='Тестовый текст вот так',
                            group=self.group)
        response = self.authorized_user.get(reverse('follow_index'))
        self.assertEqual(response.context['paginator'].count, 0)
