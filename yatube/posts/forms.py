from django import forms

from .models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        help_texts = {
            'text': 'Текст поста',
            'group': 'Группа опубликованного поста',
        }
        labels = {
            'text': 'Текст поста',
            'group': 'Группа',
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
        help_texts = {
            'text': 'Текст комментария'
        }
        labels = {
            'text': 'Текст комментария'
        }
