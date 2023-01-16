from http import HTTPStatus
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Post, Group, User


class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username="Perturabo")
        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
        form_data = {"text": "Тестовый пост",
                     "group": self.group.id,
                     }
        response = self.authorized_client.post(
            reverse("posts:post_create"), data=form_data, follow=True
        )
        self.assertRedirects(
            response, reverse("posts:profile",
                              kwargs={"username": self.user.username})
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        post = Post.objects.first()
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.group.id, form_data["group"])
        self.assertEqual(post.text, form_data["text"])
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit(self):
        """Валидная форма изменяет запись в Post."""
        id = self.post.id
        posts_count = Post.objects.count()
        form_data = {"text": "Тестовый пост",
                     "group": self.group.id,
                     }
        response = self.authorized_client.post(
            reverse("posts:post_edit", args=({self.post.id})),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse("posts:post_detail",
                              kwargs={"post_id": self.post.id})
        )
        self.assertEqual(Post.objects.count(), posts_count)
        post = Post.objects.get(id=id)
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.group.id, form_data["group"])
        self.assertEqual(post.text, form_data["text"])
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit_not_create_guest_client(self):
        """Валидная форма не изменит запись в Post если неавторизован."""
        posts_count = Post.objects.count()
        form_data = {"text": "Тестовый пост",
                     "group": self.group.id,
                     }
        response = self.guest_client.post(
            reverse("posts:post_edit", args=({self.post.id})),
            data=form_data,
            follow=True,
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertTrue(Post.objects.filter(text=self.post.text).exists())
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(
            response,
            f'{reverse("users:login")}?next='
            f'{reverse("posts:post_edit", args=({self.post.id}))}'
        )

    def test_guest_client_not_create_post(self):
        """Неавторизованный пользователь не опубликует пост."""
        posts_count = Post.objects.count()
        form_data = {"text": "Тестовый пост",
                     "group": self.group.id,
                     }
        response = self.guest_client.post(
            reverse("posts:post_create"),
            data=form_data,
            follow=True,
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertRedirects(response, f'{reverse("users:login")}?next='
                                       f'{reverse("posts:post_create")}')
