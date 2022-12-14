from django.forms import ModelForm

from .models import Post, Comment


class PostForm(ModelForm):
    class Meta:
        model = Post
        fields = ['text', 'group', 'image']
        labels = {
            'text': 'Текст',
            'group': 'Сообщество'
        }
        help_text = {
            'text': 'Hапишите свой пост здесь',
            'group': 'Выберите сообщество'
        }


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
        labels = {
            'text': 'Текст комментария',
        }
        help_texts = {
            'text': 'Напишите комментарий',
        }
