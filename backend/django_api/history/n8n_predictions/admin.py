# ============================================================
# n8n_predictions/admin.py
# Interface d'administration Django pour les prédictions N8N
# ============================================================

from django.contrib import admin
from django.utils.html import format_html
from .models import PredictionNotification, FCMToken, PushNotificationLog


@admin.register(PredictionNotification)
class PredictionNotificationAdmin(admin.ModelAdmin):
    """Interface admin pour les notifications/prédictions N8N"""
    
    list_display = [
        'title_short',
        'type_badge',
        'date',
        'affluence_badge',
        'read_status',
        'confidence_display',
        'generated_at_short',
    ]
    list_filter = [
        'type',
        'niveau_affluence',
        'is_read',
        'date',
        'generated_at',
    ]
    search_fields = ['title', 'message', 'notification_uuid', 'profil_dominant']
    readonly_fields = [
        'notification_uuid',
        'generated_at',
        'read_at',
        'confidence_percentage',
    ]
    
    fieldsets = (
        ('📌 Métadonnées', {
            'fields': ('notification_uuid', 'type', 'title')
        }),
        ('📝 Contenu', {
            'fields': ('message', 'date', 'tags')
        }),
        ('🔮 Prédiction', {
            'fields': (
                'visiteurs_prevus',
                'profil_dominant',
                'niveau_affluence',
                'heure_pointe'
            ),
            'description': 'Paramètres de la prédiction'
        }),
        ('🤖 Modèle IA', {
            'fields': ('model', 'confidence_score', 'confidence_percentage'),
            'classes': ('collapse',)
        }),
        ('📨 Statut de lecture', {
            'fields': ('is_read', 'generated_at', 'sent_at', 'read_at'),
            'description': 'Historique de transmission et lecture'
        }),
        ('📦 Données supplémentaires', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )
    
    def title_short(self, obj):
        """Affiche le titre tronqué"""
        return obj.title[:60] + "..." if len(obj.title) > 60 else obj.title
    title_short.short_description = 'Titre'
    title_short.admin_order_field = 'title'
    
    def type_badge(self, obj):
        """Affiche le type avec couleur"""
        colors = {
            'prediction': '#007bff',    # Bleu
            'report': '#6f42c1',        # Violet
            'alert': '#dc3545',         # Rouge
            'custom': '#17a2b8',        # Cyan
        }
        color = colors.get(obj.type, '#6c757d')
        return format_html(
            '<span style=\"background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;\">{}</span>',
            color,
            obj.get_type_display()
        )
    type_badge.short_description = 'Type'
    
    def affluence_badge(self, obj):
        """Affiche le niveau d'affluence avec couleur"""
        colors = {
            'low': '#28a745',           # Vert
            'medium': '#ffc107',        # Jaune
            'high': '#fd7e14',          # Orange
            'very_high': '#dc3545',     # Rouge
        }
        color = colors.get(obj.niveau_affluence, '#6c757d')
        icons = {
            'low': '🟢',
            'medium': '🟡',
            'high': '🟠',
            'very_high': '🔴',
        }
        icon = icons.get(obj.niveau_affluence, '•')
        return format_html(
            '<span style=\"color: {};\">{} {}</span>',
            color,
            icon,
            obj.get_niveau_affluence_display()
        )
    affluence_badge.short_description = 'Affluence'
    affluence_badge.admin_order_field = 'niveau_affluence'
    
    def read_status(self, obj):
        """Affiche le statut de lecture"""
        if obj.is_read:
            return format_html('<span style=\"color: green;\">✅ Lue</span>')
        else:
            return format_html('<span style=\"color: red;\">❌ Non lue</span>')
    read_status.short_description = 'Statut'
    read_status.admin_order_field = 'is_read'
    
    def confidence_display(self, obj):
        """Affiche le score de confiance"""
        if not obj.confidence_score:
            return "—"
        percentage = obj.get_confidence_percentage()
        color = 'green' if percentage > 70 else 'orange' if percentage > 40 else 'red'
        return format_html(
            '<span style=\"color: {}; font-weight: bold;\">{:.0f}%</span>',
            color,
            percentage
        )
    confidence_display.short_description = 'Confiance'
    confidence_display.admin_order_field = 'confidence_score'
    
    def confidence_percentage(self, obj):
        """Affiche le pourcentage de confiance (champ readonly)"""
        return obj.get_confidence_percentage() or "Pas de score"
    confidence_percentage.short_description = "Score de confiance (%)"
    
    def generated_at_short(self, obj):
        """Affiche la date de génération formatée"""
        return obj.generated_at.strftime('%d/%m %H:%M') if obj.generated_at else '—'
    generated_at_short.short_description = 'Créée le'
    generated_at_short.admin_order_field = 'generated_at'
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        """Action : marquer comme lue"""
        updated = queryset.update(is_read=True)
        self.message_user(request, f"{updated} notification(s) marquée(s) comme lue(s).")
    mark_as_read.short_description = "✅ Marquer comme lue"
    
    def mark_as_unread(self, request, queryset):
        """Action : marquer comme non lue"""
        updated = queryset.update(is_read=False)
        self.message_user(request, f"{updated} notification(s) marquée(s) comme non lue(s).")
    mark_as_unread.short_description = "❌ Marquer comme non lue"


@admin.register(FCMToken)
class FCMTokenAdmin(admin.ModelAdmin):
    """Interface admin pour les tokens FCM"""
    
    list_display = [
        'token_display',
        'device_type',
        'device_info',
        'is_active_badge',
        'updated_at_short',
    ]
    list_filter = ['is_active', 'updated_at']
    search_fields = ['token', 'device_info']
    readonly_fields = ['token', 'created_at', 'updated_at']
    
    fieldsets = (
        ('🔑 Token', {
            'fields': ('token',)
        }),
        ('📱 Appareil', {
            'fields': ('device_info', 'is_active')
        }),
        ('⏱️ Historique', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def token_display(self, obj):
        """Affiche le token tronqué"""
        return f"{obj.token[:30]}..."
    token_display.short_description = 'Token'
    token_display.admin_order_field = 'token'
    
    def device_type(self, obj):
        """Affiche le type d'appareil"""
        device = obj.get_device_type()
        icons = {
            'iOS': '🍎',
            'Android': '🤖',
            'Web': '🌐',
            'Unknown': '❓'
        }
        icon = icons.get(device, '❓')
        return f"{icon} {device}"
    device_type.short_description = 'Type'
    device_type.admin_order_field = 'device_info'
    
    def is_active_badge(self, obj):
        """Affiche le statut actif/inactif"""
        if obj.is_active:
            return format_html('<span style="color: green; font-weight: bold;">✅ Actif</span>')
        else:
            return format_html('<span style="color: red; font-weight: bold;">❌ Inactif</span>')
    is_active_badge.short_description = 'Statut'
    is_active_badge.admin_order_field = 'is_active'
    
    def updated_at_short(self, obj):
        """Affiche la dernière mise à jour formatée"""
        return obj.updated_at.strftime('%d/%m %H:%M') if obj.updated_at else '—'
    updated_at_short.short_description = 'Dernière mise à jour'
    updated_at_short.admin_order_field = 'updated_at'


@admin.register(PushNotificationLog)
class PushNotificationLogAdmin(admin.ModelAdmin):
    """Interface admin pour l'historique d'envoi FCM"""
    
    list_display = [
        'title_short',
        'status_badge',
        'success_rate_display',
        'sent_count',
        'error_count',
        'created_at_short',
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['title', 'body']
    readonly_fields = [
        'created_at',
        'updated_at',
        'sent_at',
        'success_rate',
    ]
    
    fieldsets = (
        ('📬 Notification', {
            'fields': ('notification', 'title', 'body')
        }),
        ('📊 Résultats', {
            'fields': (
                'status',
                'sent_count',
                'error_count',
                'success_rate',
            ),
            'description': "Statistiques d'envoi"
        }),
        ('⏱️ Dates', {
            'fields': ('created_at', 'updated_at', 'sent_at'),
            'classes': ('collapse',)
        }),
        ('❌ Erreurs', {
            'fields': ('errors',),
            'classes': ('collapse',)
        }),
        ('📦 Données', {
            'fields': ('data',),
            'classes': ('collapse',)
        }),
    )
    
    def title_short(self, obj):
        """Affiche le titre tronqué"""
        return obj.title[:50] + "..." if len(obj.title) > 50 else obj.title
    title_short.short_description = 'Titre'
    title_short.admin_order_field = 'title'
    
    def status_badge(self, obj):
        """Affiche le statut avec couleur"""
        colors = {
            'queued': '#ffc107',        # Jaune
            'sent': '#28a745',          # Vert
            'failed': '#dc3545',        # Rouge
            'bounced': '#6f42c1',       # Violet
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Statut'
    status_badge.admin_order_field = 'status'
    
    def success_rate_display(self, obj):
        """Affiche le taux de succès"""
        if obj.sent_count + obj.error_count == 0:
            return "—"
        rate = obj.success_rate
        color = 'green' if rate >= 90 else 'orange' if rate >= 50 else 'red'
        # CORRECTIF : format_html n'applique pas de spécificateur de format
        # numérique ({:.0f}) — il insère ses arguments tels quels avec
        # échappement HTML. Le formatage doit se faire AVANT l'appel, avec
        # une f-string ou str.format() classique sur un float/int normal.
        rate_str = f"{rate:.0f}"
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}%</span>',
            color,
            rate_str
        )
    success_rate_display.short_description = 'Succès'
    success_rate_display.admin_order_field = 'sent_count'
    
    def created_at_short(self, obj):
        """Affiche la date de création formatée"""
        return obj.created_at.strftime('%d/%m %H:%M') if obj.created_at else '—'
    created_at_short.short_description = 'Créée le'
    created_at_short.admin_order_field = 'created_at'