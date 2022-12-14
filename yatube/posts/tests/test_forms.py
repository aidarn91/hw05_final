import shutil
import tempfile

from http import HTTPStatus

from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from posts.models import Group, Post
from posts.forms import PostForm


User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='test_group',
            slug='test_slug',
            description='Тестовое описание'
        )

        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.author,
        )
        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.author)
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_create_post(self):
        """При отправке поста с картинкой через форму
        PostForm создаётся запись в базе данных"""
        posts_before = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'group': self.group.id,
            'text': 'test_post',
            'image': uploaded,
        }
        posts_before = Post.objects.count()
        response = self.authorized_author_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        self.assertTrue(
            Post.objects.filter(
                group=form_data['group'],
                text=form_data['text'],
                image='posts/small.gif'
            ).exists()
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Post.objects.count(), posts_before + 1)
        self.assertRedirects(response, reverse('posts:profile',
                             args=[self.author.username]))

    def test_create_post(self):
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.pk,
        }
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )

        self.assertEqual(Post.objects.count(), posts_count + 1)
        post = Post.objects.first()
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.author, self.author)
        self.assertEqual(post.group_id, form_data['group'])

    def test_edit_post(self):
        form_data = {
            'text': 'Новый тестовый текст',
            'group': self.group.pk,
        }
        response = self.authorized_client.post(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': PostFormTests.post.pk}
            ),
            data=form_data,
            follow=True
        )
        post = Post.objects.get(pk=PostFormTests.post.pk)
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': PostFormTests.post.pk}
        ))
        self.assertEqual(
            post.text,
            form_data['text']
        )
        self.assertEqual(
            post.group.pk,
            form_data['group']
        )

    def test_comment_only_for_auth(self):
        """После успешной отправки комментарий
        появляется на странице поста.
        Комментировать посты может
        только авторизованный пользователь"""

        comments_before = self.post.comments.count()
        commentform_data = {
            'text': 'комментарий',
        }
        response = self.guest_client.post(
            reverse('posts:add_comment', args=[self.post.id]),
            data=commentform_data,
            follow=True,
        )

        expected_redirect = str(reverse('users:login') + '?next='
                                + reverse('posts:add_comment',
                                          args=[self.post.id]))

        self.assertRedirects(response, expected_redirect)
        self.assertEqual(self.post.comments.count(), comments_before)
        response = self.authorized_client.post(
            reverse('posts:add_comment', args=[self.post.id]),
            data=commentform_data,
            follow=True,
        )
        self.assertEqual(self.post.comments.count(), comments_before + 1)
        last_comment = self.post.comments.last()
        self.assertEqual(last_comment.text, commentform_data['text'])
