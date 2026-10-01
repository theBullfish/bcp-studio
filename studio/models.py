"""BCP Studio domain models.

The whole platform hangs off these. Everything is registered in Django admin
(studio/admin.py) so the team gets back-office CRUD for free, and the Skote
front-end views read/write the same models.
"""

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

# ---------------------------------------------------------------------------
# Roles / identity
# ---------------------------------------------------------------------------


class Role(models.TextChoices):
    OWNER = "OWNER", "Owner"
    ADMIN = "ADMIN", "Admin"
    PRODUCER = "PRODUCER", "Producer"
    EDITOR = "EDITOR", "Editor"
    APPROVER = "APPROVER", "Approver"
    CONTRIBUTOR = "CONTRIBUTOR", "Contributor"
    VIEWER = "VIEWER", "Viewer"


# Most→least privileged. Lower index = more power.
ROLE_ORDER = [
    Role.OWNER,
    Role.ADMIN,
    Role.PRODUCER,
    Role.EDITOR,
    Role.APPROVER,
    Role.CONTRIBUTOR,
    Role.VIEWER,
]


def role_at_least(role: str, minimum: str) -> bool:
    try:
        return ROLE_ORDER.index(role) <= ROLE_ORDER.index(minimum)
    except ValueError:
        return False


class Profile(models.Model):
    """Extends the built-in Django User with a studio role + pay tracking."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CONTRIBUTOR)
    pay_rate_cents = models.IntegerField(null=True, blank=True)  # private
    avatar_url = models.URLField(blank=True)
    title = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    def can(self, minimum_role: str) -> bool:
        return role_at_least(self.role, minimum_role)


# ---------------------------------------------------------------------------
# Clients / brands
# ---------------------------------------------------------------------------


class ClientType(models.TextChoices):
    ARTIST = "ARTIST", "Artist"
    GROUP = "GROUP", "Group / Band"
    LABEL = "LABEL", "Label"
    NEWS_AGENCY = "NEWS_AGENCY", "News agency"
    BUSINESS = "BUSINESS", "Business"
    CREATOR = "CREATOR", "Creator"


class Client(models.Model):
    """A tenant: an artist, group, agency or business the studio produces for.

    An authorized rep can grant the app permission to act on their channels
    (see SocialAccount.authorized_by) — that's the 'log in as the client and
    let the app do stuff' flow.
    """

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    type = models.CharField(max_length=20, choices=ClientType.choices, default=ClientType.ARTIST)
    primary_contact = models.EmailField(blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class BrandKit(models.Model):
    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name="brand_kit")
    primary_color = models.CharField(max_length=9, default="#556ee6")
    secondary_color = models.CharField(max_length=9, default="#34c38f")
    accent_color = models.CharField(max_length=9, default="#f1b44c")
    font_heading = models.CharField(max_length=80, default="Poppins")
    font_body = models.CharField(max_length=80, default="Poppins")
    logo_url = models.URLField(blank=True)
    logo_mark_url = models.URLField(blank=True)
    watermark_url = models.URLField(blank=True)
    tone_of_voice = models.TextField(blank=True)  # guides AI copy
    hashtags_csv = models.CharField(max_length=500, blank=True)

    def __str__(self):
        return f"Brand kit — {self.client.name}"

    @property
    def hashtags_list(self):
        return [h.strip() for h in self.hashtags_csv.split(",") if h.strip()]


class BrandAsset(models.Model):
    class Kind(models.TextChoices):
        LOGO = "LOGO", "Logo"
        FONT = "FONT", "Font"
        TEMPLATE = "TEMPLATE", "Template"
        OVERLAY = "OVERLAY", "Overlay"
        LOWER_THIRD = "LOWER_THIRD", "Lower third"
        INTRO = "INTRO", "Intro"
        OUTRO = "OUTRO", "Outro"
        OTHER = "OTHER", "Other"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="assets")
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.OTHER)
    name = models.CharField(max_length=200)
    url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ClientMembership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=20, choices=Role.choices, blank=True)

    class Meta:
        unique_together = ("user", "client")

    def __str__(self):
        return f"{self.user.username} @ {self.client.name}"


# ---------------------------------------------------------------------------
# Social accounts
# ---------------------------------------------------------------------------


class Platform(models.TextChoices):
    INSTAGRAM = "INSTAGRAM", "Instagram"
    TIKTOK = "TIKTOK", "TikTok"
    YOUTUBE = "YOUTUBE", "YouTube"
    X = "X", "X"
    FACEBOOK = "FACEBOOK", "Facebook"
    LINKEDIN = "LINKEDIN", "LinkedIn"
    THREADS = "THREADS", "Threads"


class SocialAccount(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="social_accounts")
    platform = models.CharField(max_length=20, choices=Platform.choices)
    handle = models.CharField(max_length=120)
    display_name = models.CharField(max_length=200, blank=True)
    connected = models.BooleanField(default=False)
    access_token = models.CharField(max_length=500, blank=True)
    refresh_token = models.CharField(max_length=500, blank=True)
    token_expires = models.DateTimeField(null=True, blank=True)
    scopes = models.CharField(max_length=500, blank=True)
    # Who authorized the app to act on this channel, and when.
    authorized_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="authorized_channels"
    )
    authorized_at = models.DateTimeField(null=True, blank=True)
    auto_post = models.BooleanField(default=False)  # publish without manual push
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("client", "platform", "handle")

    def __str__(self):
        return f"{self.get_platform_display()} {self.handle}"


class DistributionRule(models.Model):
    """How a produced format is routed to platforms for a client.

    e.g. source_format 'reel_9x16' -> Instagram + TikTok + YouTube.
    Drives which channels a play's outputs get posted to.
    """

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="distribution_rules")
    source_format = models.CharField(max_length=40)  # e.g. reel_9x16, square_1x1
    platforms = models.JSONField(default=list)        # ["INSTAGRAM","TIKTOK",...]
    auto_post = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.client.name}: {self.source_format} → {', '.join(self.platforms)}"


class PlatformProfile(models.Model):
    """Per-client, per-platform posting policy/defaults."""

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="platform_profiles")
    platform = models.CharField(max_length=20, choices=Platform.choices)
    default_hashtags = models.CharField(max_length=500, blank=True)
    posting_cadence = models.CharField(max_length=120, blank=True)  # e.g. "3x/week, 9am"
    best_times = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("client", "platform")

    def __str__(self):
        return f"{self.client.name} · {self.get_platform_display()}"


# ---------------------------------------------------------------------------
# Projects & media
# ---------------------------------------------------------------------------


class Project(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PROCESSING = "PROCESSING", "Processing"
        READY = "READY", "Ready"
        SCHEDULED = "SCHEDULED", "Scheduled"
        ARCHIVED = "ARCHIVED", "Archived"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="projects")
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="projects")
    title = models.CharField(max_length=250)
    summary = models.TextField(blank=True)  # feeds AI copy
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class MediaAsset(models.Model):
    class Kind(models.TextChoices):
        VIDEO = "VIDEO", "Video"
        AUDIO = "AUDIO", "Audio"
        IMAGE = "IMAGE", "Image"
        DOCUMENT = "DOCUMENT", "Document"

    class Status(models.TextChoices):
        UPLOADING = "UPLOADING", "Uploading"
        UPLOADED = "UPLOADED", "Uploaded"
        PROCESSING = "PROCESSING", "Processing"
        READY = "READY", "Ready"
        FAILED = "FAILED", "Failed"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="media")
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.VIDEO)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.UPLOADED)
    label = models.CharField(max_length=250)
    url = models.CharField(max_length=1000, blank=True)
    thumbnail_url = models.CharField(max_length=1000, blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)
    format = models.CharField(max_length=40, blank=True)  # reel_9x16, square_1x1, ...
    derived_from = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="derivatives"
    )
    play_run = models.ForeignKey(
        "PlayRun", on_delete=models.SET_NULL, null=True, blank=True, related_name="outputs"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.label


# ---------------------------------------------------------------------------
# AI plays
# ---------------------------------------------------------------------------


class Play(models.Model):
    key = models.SlugField(unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    steps = models.JSONField(default=list)   # declarative pipeline
    outputs = models.JSONField(default=list)  # expected formats
    builtin = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class PlayRun(models.Model):
    class Status(models.TextChoices):
        QUEUED = "QUEUED", "Queued"
        RUNNING = "RUNNING", "Running"
        SUCCEEDED = "SUCCEEDED", "Succeeded"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    play = models.ForeignKey(Play, on_delete=models.CASCADE, related_name="runs")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="play_runs")
    triggered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.QUEUED)
    progress = models.IntegerField(default=0)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.play.name} → {self.project.title}"


# ---------------------------------------------------------------------------
# Posts / publishing / approvals
# ---------------------------------------------------------------------------


class Post(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        IN_REVIEW = "IN_REVIEW", "In review"
        APPROVED = "APPROVED", "Approved"
        SCHEDULED = "SCHEDULED", "Scheduled"
        PUBLISHING = "PUBLISHING", "Publishing"
        PUBLISHED = "PUBLISHED", "Published"
        FAILED = "FAILED", "Failed"
        REJECTED = "REJECTED", "Rejected"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="posts")
    project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts"
    )
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="posts")
    social_account = models.ForeignKey(
        SocialAccount, on_delete=models.SET_NULL, null=True, blank=True
    )
    platform = models.CharField(max_length=20, choices=Platform.choices)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    caption = models.TextField(blank=True)
    caption_ai = models.TextField(blank=True)  # original AI draft
    hashtags = models.CharField(max_length=500, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    external_url = models.URLField(blank=True)
    failure_reason = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_platform_display()}: {self.caption[:40]}"


class PostMedia(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="media")
    media = models.ForeignKey(MediaAsset, on_delete=models.CASCADE)
    position = models.IntegerField(default=0)

    class Meta:
        unique_together = ("post", "media")
        ordering = ["position"]


class Approval(models.Model):
    class Decision(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CHANGES_REQUESTED = "CHANGES_REQUESTED", "Changes requested"

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="approvals")
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="approvals")
    decision = models.CharField(max_length=20, choices=Decision.choices, default=Decision.PENDING)
    comment = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("post", "reviewer")

    def __str__(self):
        return f"{self.reviewer.username}: {self.decision}"


# ---------------------------------------------------------------------------
# Calendar / releases
# ---------------------------------------------------------------------------


class Release(models.Model):
    class Kind(models.TextChoices):
        SINGLE = "SINGLE", "Single"
        ALBUM = "ALBUM", "Album"
        EP = "EP", "EP"
        VIDEO = "VIDEO", "Video"
        EPISODE = "EPISODE", "Episode"
        CAMPAIGN = "CAMPAIGN", "Campaign"
        EVENT = "EVENT", "Event"
        OTHER = "OTHER", "Other"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="releases")
    project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="releases"
    )
    title = models.CharField(max_length=250)
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.SINGLE)
    release_date = models.DateTimeField()
    is_primary = models.BooleanField(default=False)  # shows in "my release dates" view
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.title


class CalendarEvent(models.Model):
    class Kind(models.TextChoices):
        RELEASE = "RELEASE", "Release"
        MEETING = "MEETING", "Meeting"
        DEADLINE = "DEADLINE", "Deadline"
        SHOOT = "SHOOT", "Shoot"
        HOLD = "HOLD", "Hold"
        OTHER = "OTHER", "Other"

    title = models.CharField(max_length=250)
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.OTHER)
    start = models.DateTimeField()
    end = models.DateTimeField(null=True, blank=True)
    all_day = models.BooleanField(default=False)
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.title


# ---------------------------------------------------------------------------
# Tracking (private)
# ---------------------------------------------------------------------------


class PostMetric(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="metrics")
    captured_at = models.DateTimeField(default=timezone.now)
    impressions = models.IntegerField(default=0)
    reach = models.IntegerField(default=0)
    likes = models.IntegerField(default=0)
    comments = models.IntegerField(default=0)
    shares = models.IntegerField(default=0)
    saves = models.IntegerField(default=0)
    views = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    revenue_cents = models.IntegerField(default=0)


class RevenueEntry(models.Model):
    class Source(models.TextChoices):
        STREAMING = "STREAMING", "Streaming"
        SYNC = "SYNC", "Sync"
        MERCH = "MERCH", "Merch"
        AD_REVENUE = "AD_REVENUE", "Ad revenue"
        SPONSORSHIP = "SPONSORSHIP", "Sponsorship"
        LIVE = "LIVE", "Live"
        OTHER = "OTHER", "Other"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="revenue")
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.STREAMING)
    amount_cents = models.IntegerField()
    currency = models.CharField(max_length=3, default="USD")
    occurred_at = models.DateTimeField()
    note = models.CharField(max_length=250, blank=True)


class PayEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="pay_entries")
    amount_cents = models.IntegerField()
    currency = models.CharField(max_length=3, default="USD")
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    note = models.CharField(max_length=250, blank=True)
    paid = models.BooleanField(default=False)


class TrendItem(models.Model):
    source = models.CharField(max_length=120)
    title = models.CharField(max_length=400)
    url = models.URLField(blank=True)
    score = models.FloatField(null=True, blank=True)
    category = models.CharField(max_length=80, blank=True)
    captured_at = models.DateTimeField(default=timezone.now)


# ---------------------------------------------------------------------------
# Messaging / notifications
# ---------------------------------------------------------------------------


class Conversation(models.Model):
    title = models.CharField(max_length=200, blank=True)
    participants = models.ManyToManyField(User, related_name="conversations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title or f"Conversation #{self.pk}"


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=60)
    title = models.CharField(max_length=250)
    body = models.CharField(max_length=500, blank=True)
    link = models.CharField(max_length=500, blank=True)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=120)
    entity = models.CharField(max_length=120)
    entity_id = models.CharField(max_length=60, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


# Pillar model modules (store, paid video, ingest) — imported so Django and the
# admin discover them as part of the `studio` app.
from .commerce_models import (  # noqa: E402,F401
    Order, OrderItem, Price, Product, StoreCustomer,
)
from .video_models import (  # noqa: E402,F401
    Channel, Membership, MembershipPlan, Video, VideoView,
)
from .ingest_models import Device, IngestedFile  # noqa: E402,F401
