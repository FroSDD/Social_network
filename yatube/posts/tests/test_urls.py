from http import HTTPStatus
from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from ..models import Post, Group

User = get_user_model()


class PostsURLTests(TestCase):
    """Создаем тестовый пост и группу."""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Perturabo')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )
        cls.url_names = [
            "/",
            f"/group/{cls.group.slug}/",
            f"/profile/{cls.user}/",
            f"/posts/{cls.post.id}/",
        ]
        cls.templates_url_names = {
            "/": "posts/index.html",
            f"/group/{cls.group.slug}/": "posts/group_list.html",
            f"/profile/{cls.user.username}/": "posts/profile.html",
            f"/posts/{cls.post.id}/": "posts/post_detail.html",
            f"/posts/{cls.post.id}/edit/": "posts/create_post.html",
            "/create/": "posts/create_post.html",
            "/follow/": "posts/follow.html",
        }
        cls.urls = {
            "index": "/",
            "group": f"/group/{cls.group.slug}/",
            "profile": f"/profile/{cls.user}/",
            "post": f"/posts/{cls.post.id}/",
            "create": "/create/",
            "page": "/unexisting_page/",
            'follow': "/follow/",
        }

    def setUp(self):
        """Создаем клиент гостя и зарегистрированного пользователя."""
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostsURLTests.user)

    def test_urls_extsts_at_desired_location(self):
        """Страницы, доступные любому пользователю"""
        for adress in self.url_names:
            with self.subTest(adress):
                response = self.guest_client.get(adress)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_url_exists_at_desired_location_authorized(self):
        """Страница /create/ доступна авторизованному пользователю."""
        response = self.authorized_client.get(self.urls["create"])
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_id_url_exists_at_authorized_author(self):
        """Страница /posts/post_id/edit/ доступна
        авторизованному пользователю.
        """
        response = self.authorized_client.get(self.urls["post"])
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_url_redirect_anonymous_on_admin_login(self):
        """Страница /create/ перенаправит анонимного пользователя
        на страницу логина.
        """
        response = self.guest_client.get(self.urls["create"], follow=True)
        self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_unexisting_page_at_desired_location(self):
        """Страница /unexisting_page/ должна выдать ошибку."""
        response = self.guest_client.get(self.urls["page"])
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_authorizing_client_follow(self):
        """Страница /follow/ доступна авторизованному пользователю."""
        response = self.authorized_client.get(self.urls["follow"])
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for url, template in self.templates_url_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)
