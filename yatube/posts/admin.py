from django.contrib import admin

from .models import Post, Group, Comment, Follow


class PostAdmin(admin.ModelAdmin):
    list_display = ('pk', 'text', 'pub_date', 'author', 'group')
    search_fields = ('text',)
    list_filter = ('pub_date',)
    list_editable = ('group',)
    empty_value_display = '-пусто-'


class PostGroup(admin.ModelAdmin):
    list_display = ('pk', 'description', 'title', 'slug')
    search_fields = ('description',)
    list_filter = ('slug',)
    empty_value_display = '-пусто-'


admin.site.register(Post, PostAdmin)
admin.site.register(Group, PostGroup)
admin.site.register(Comment)
admin.site.register(Follow)
