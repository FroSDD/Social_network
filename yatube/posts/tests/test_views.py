import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.conf import settings
from django import forms
from django.core.cache import cache

from ..models import Post, Group, Comment, Follow

User = get_user_model()


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='Perturabo')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )
        cls.templates_page_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list', kwargs={'slug': cls.group.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile', kwargs={'username': cls.post.author}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail', kwargs={'post_id': cls.post.id}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit', kwargs={'post_id': cls.post.id}
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        cls.reversed_urls = {
            'index': reverse('posts:index'),
            'group': reverse('posts:group_list',
                             kwargs={'slug': cls.group.slug}),
            'profile': reverse('posts:profile',
                               kwargs={'username': cls.post.author}),
            'post': reverse('posts:post_detail', kwargs={
                'post_id': cls.post.id}),
            'post_edit': reverse('posts:post_edit', kwargs={
                'post_id': cls.post.id}),
            'create': reverse('posts:post_create'),
            'comment': reverse('posts:add_comment', kwargs={
                'post_id': cls.post.id}),
        }
        cls.comment = Comment.objects.create(
            author=cls.user,
            text='Тестовый комментарий',
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostPagesTests.user)

    def test_pages_uses_correct_template(self):
        '''URL-адрес использует соответствующий шаблон.'''
        for template, reverse_name in self.templates_page_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(template)
                self.assertTemplateUsed(response, reverse_name)

    def test_index_show_correct_context(self):
        '''Список постов в шаблоне index равен ожидаемому контексту.'''
        response = self.guest_client.get(self.reversed_urls['index'])
        expected = list(Post.objects.all()[:settings.NUMBER_OF_POSTS])
        self.assertEqual(list(response.context['page_obj']), expected)

    def test_group_list_show_correct_context(self):
        '''Список постов в шаблоне group_list равен ожидаемому контексту.'''
        response = self.guest_client.get(self.reversed_urls['group'])
        expected = list(Post.objects.filter(group_id=self.group.id)
                        [:settings.NUMBER_OF_POSTS])
        self.assertEqual(list(response.context['page_obj']), expected)

    def test_profile_show_correct_context(self):
        '''Список постов в шаблоне profile равен ожидаемому контексту.'''
        response = self.guest_client.get(self.reversed_urls['profile'])
        expected = list(Post.objects.filter(author_id=self.user.id)
                        [:settings.NUMBER_OF_POSTS])
        self.assertEqual(list(response.context['page_obj']), expected)

    def test_post_detail_show_correct_context(self):
        '''Шаблон post_detail сформирован с правильным контекстом.'''
        response = self.guest_client.get(self.reversed_urls['post'])
        post = response.context.get('post')
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(post.group, self.post.group)

    def test_create_edit_show_correct_context(self):
        '''Шаблон post_edit сформирован с правильным контекстом.'''
        response = self.authorized_client.get(self.reversed_urls['post_edit'])
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_create_show_correct_context(self):
        '''Шаблон create сформирован с правильным контекстом.'''
        response = self.authorized_client.get(self.reversed_urls['create'])
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_check_group_in_pages(self):
        '''Проверяем создание поста на страницах с выбранной группой.'''
        post = Post.objects.get(group=self.post.group)
        form_fields = {
            self.reversed_urls['index']: post,
            self.reversed_urls['group']: post,
            self.reversed_urls['profile']: post,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                form_field = response.context['page_obj']
                self.assertIn(expected, form_field)

    def test_check_group_not_in_mistake_group_list_page(self):
        '''Проверяем чтобы созданный Пост с группой не попап в чужую группу.'''
        form_fields = {
            self.reversed_urls['group']: Post.objects.exclude(
                group=self.post.group),
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                form_field = response.context['page_obj']
                self.assertNotIn(expected, form_field)

    def test_comment_have_correct_context(self):
        '''Комментарий создает запись на странице поста.'''
        comments_count = Comment.objects.count()
        form_data = {'text': 'Тестовый пост'}
        response = self.authorized_client.post(
            self.reversed_urls['comment'],
            data=form_data,
            follow=True,
        )
        self.assertRedirects(response, self.reversed_urls['post'])
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertTrue(
            Comment.objects.filter(text=self.comment.text).exists()
        )

    def test_cache_work(self):
        '''Проверка работы кеша.'''
        new_post = Post.objects.create(
            author=self.user,
            text='Пост для кеша',
            group=self.group,
        )
        page_1 = self.guest_client.get(self.reversed_urls['index'])
        page_content_1 = page_1.content
        new_post.delete
        page_2 = self.guest_client.get(self.reversed_urls['index'])
        page_content_2 = page_2.content
        self.assertEqual(page_content_1, page_content_2)
        cache.clear()
        page_3 = self.guest_client.get(self.reversed_urls['index'])
        page_content_3 = page_3.content
        self.assertNotEqual(page_content_2, page_content_3)


class PaginatorViewsTest(TestCase):
    POSTS_COUNT = 13
    POSTS_SECOND_PAGE_COUNT = 3

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user('Perturabo')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание',
        )
        Post.objects.bulk_create(
            [Post(author=cls.user, group=cls.group, text=f'Тестовый пост{i}')
             for i in range(cls.POSTS_COUNT)])

    def test_first_page_contains_ten_records(self):
        reversed_urls = (
            reverse('posts:index'),
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}),
            reverse('posts:profile',
                    kwargs={'username': self.user.username}),
        )
        '''Проверка: количество постов на первой странице равно 10.'''
        for reverse_name in reversed_urls:
            with self.subTest(reverse_name=reverse_name):
                response = self.client.get(reverse_name)
                self.assertEqual(len(response.context['page_obj']),
                                 settings.NUMBER_OF_POSTS)

    def test_second_page_contains_three_records(self):
        '''Проверка: на второй странице должно быть три поста.'''
        reversed_urls = (
            reverse('posts:index') + '?page=2',
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}) + '?page=2',
            reverse('posts:profile',
                    kwargs={'username': self.user.username}) + '?page=2',
        )
        for reverse_name in reversed_urls:
            with self.subTest(reverse_name=reverse_name):
                response = self.client.get(reverse_name)
                self.assertEqual(len(response.context['page_obj']),
                                 self.POSTS_SECOND_PAGE_COUNT)


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TaskImageTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='Perturabo')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
            image=cls.uploaded,
        )
        cls.reversed_urls = {
            'index': reverse('posts:index'),
            'group': reverse('posts:group_list',
                             kwargs={'slug': cls.group.slug}),
            'profile': reverse('posts:profile',
                               kwargs={'username': cls.post.author}),
            'post': reverse('posts:post_detail', kwargs={
                'post_id': cls.post.id}),
            'post_edit': reverse('posts:post_edit', kwargs={
                'post_id': cls.post.id}),
            'create': reverse('posts:post_create'),
        }

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()

    def test_image_in_index_and_profile_page(self):
        '''Изображение передается в index и profile.'''
        templates = (
            self.reversed_urls['index'],
            self.reversed_urls['profile'],
        )
        for url in templates:
            with self.subTest(url):
                response = self.guest_client.get(url)
                obj = response.context['page_obj'][0]
                self.assertEqual(obj.image, self.post.image)

    def test_image_in_group_list_page(self):
        '''Изображение передается в group_list.'''
        response = self.guest_client.get(self.reversed_urls['group'])
        obj = response.context['page_obj'][0]
        self.assertEqual(obj.image, self.post.image)

    def test_image_in_post_detail_page(self):
        '''Изображение передается в страницу post_detail.'''
        response = self.guest_client.get(self.reversed_urls['post'])
        obj = response.context['post']
        self.assertEqual(obj.image, self.post.image)

    def test_image_in_page(self):
        '''Пост с изображением создается в БД'''
        self.assertTrue(
            Post.objects.filter(
                text=self.post.text, image="posts/small.gif").exists()
        )


class FollowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.authorized_client = Client()
        cls.author_client = Client()
        cls.guest_client = Client()

        cls.user = User.objects.create(username='Perturabo')
        cls.author = User.objects.create(username='Jilliman')
        cls.guest = User.objects.create(username='Dorn')

        cls.authorized_client.force_login(cls.user)
        cls.author_client.force_login(cls.author)
        cls.guest_client.force_login(cls.guest)

    def test_follow(self):
        '''Проверка подписки на автора.'''
        follow_count = Follow.objects.count()
        self.authorized_client.get(
            reverse('posts:profile_follow', kwargs={'username':
                    self.author.username}))
        self.assertEqual(Follow.objects.count(), follow_count + 1)
        follow = Follow.objects.last()
        self.assertEqual(follow.author, self.author)
        self.assertEqual(follow.user, self.user)

    def test_unfollow(self):
        '''Проверка отписки от автора.'''
        Follow.objects.create(user=self.user, author=self.author)
        follow_count = Follow.objects.count()
        self.authorized_client.get(
            reverse('posts:profile_unfollow', kwargs={'username':
                    self.author.username}))
        self.assertEqual(Follow.objects.count(), follow_count - 1)
        self.assertFalse(Follow.objects.filter(
            user=self.user, author=self.author).exists())

    def test_new_post_auth_in_the_feed(self):
        '''Проверка ленты подписанного пользователя.'''
        Follow.objects.create(user=self.user, author=self.author)
        post_text = 'Text'
        Post.objects.create(author=self.author, text=post_text)
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertNotEqual(len(response.context.get('page_obj')), 0)
        follow = Follow.objects.get(user=self.user, author=self.author)
        self.assertEqual(follow.author, self.author)
        self.assertEqual(follow.user, self.user)
        post = response.context['page_obj'][0]
        self.assertEqual(post.text, post_text)

    def test_new_post_not_auth_in_the_feed(self):
        '''Проверка ленты не подписанного пользователя.'''
        Post.objects.create(author=self.author, text='Text')
        response = self.guest_client.get(reverse('posts:follow_index'))
        self.assertEqual(len(response.context.get('page_obj')), 0)
