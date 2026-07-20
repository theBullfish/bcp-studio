"""Django admin registration — the studio's back-office.

Every domain model is here so Owners/Admins get full CRUD, filtering and search
without any custom UI. This is deliberate: the front-end Skote views are for the
day-to-day flow; the admin is the power tool.
"""

from django.contrib import admin

from . import models


@admin.register(models.Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "title", "pay_rate_cents")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email", "title")


class BrandKitInline(admin.StackedInline):
    model = models.BrandKit
    can_delete = False


class SocialAccountInline(admin.TabularInline):
    model = models.SocialAccount
    extra = 0


@admin.register(models.Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "active", "created_at")
    list_filter = ("active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [BrandKitInline, SocialAccountInline]


@admin.register(models.BrandAsset)
class BrandAssetAdmin(admin.ModelAdmin):
    list_display = ("name", "client", "kind", "created_at")
    list_filter = ("kind", "client")
    search_fields = ("name",)


@admin.register(models.ClientMembership)
class ClientMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "client", "role")
    list_filter = ("client", "role")


class MediaAssetInline(admin.TabularInline):
    model = models.MediaAsset
    extra = 0
    fk_name = "project"
    fields = ("label", "kind", "status", "format", "url")


@admin.register(models.Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "client", "owner", "status", "updated_at")
    list_filter = ("status", "client")
    search_fields = ("title", "summary")
    inlines = [MediaAssetInline]


@admin.register(models.MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ("label", "project", "kind", "status", "format", "created_at")
    list_filter = ("kind", "status")
    search_fields = ("label",)


@admin.register(models.Play)
class PlayAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "builtin", "active")
    list_filter = ("builtin", "active")
    search_fields = ("name", "key")


@admin.register(models.PlayRun)
class PlayRunAdmin(admin.ModelAdmin):
    list_display = ("play", "project", "status", "progress", "created_at")
    list_filter = ("status", "play")


class PostMediaInline(admin.TabularInline):
    model = models.PostMedia
    extra = 0


class ApprovalInline(admin.TabularInline):
    model = models.Approval
    extra = 0


class PostMetricInline(admin.TabularInline):
    model = models.PostMetric
    extra = 0


@admin.register(models.Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("__str__", "client", "platform", "status", "scheduled_at", "published_at")
    list_filter = ("status", "platform", "client")
    search_fields = ("caption",)
    inlines = [PostMediaInline, ApprovalInline, PostMetricInline]


@admin.register(models.Approval)
class ApprovalAdmin(admin.ModelAdmin):
    list_display = ("post", "reviewer", "decision", "decided_at")
    list_filter = ("decision",)


@admin.register(models.Release)
class ReleaseAdmin(admin.ModelAdmin):
    list_display = ("title", "client", "kind", "release_date", "is_primary")
    list_filter = ("kind", "client", "is_primary")
    search_fields = ("title",)


@admin.register(models.CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "start", "end", "client")
    list_filter = ("kind",)


@admin.register(models.RevenueEntry)
class RevenueEntryAdmin(admin.ModelAdmin):
    list_display = ("client", "source", "amount_cents", "currency", "occurred_at")
    list_filter = ("source", "client")


@admin.register(models.PayEntry)
class PayEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "amount_cents", "period_start", "period_end", "paid")
    list_filter = ("paid",)


@admin.register(models.TrendItem)
class TrendItemAdmin(admin.ModelAdmin):
    list_display = ("title", "source", "category", "captured_at")
    list_filter = ("source", "category")


@admin.register(models.Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("__str__", "created_at", "updated_at")


@admin.register(models.Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "sender", "created_at")


@admin.register(models.Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "title", "read", "created_at")
    list_filter = ("read", "kind")


@admin.register(models.AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "entity", "entity_id", "user", "created_at")
    list_filter = ("entity", "action")


admin.site.site_header = "Balls & Chunk Studio — Admin"
admin.site.site_title = "BCP Studio Admin"
admin.site.index_title = "Back office"
