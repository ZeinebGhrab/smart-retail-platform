# ============================================================
# video_alerts/admin.py
# Interface d'administration Django pour les alertes vidéo
# ============================================================

from django.contrib import admin
from django.utils.html import format_html
from .models import VideoTheftAlert, AlertSpace


@admin.register(AlertSpace)
class AlertSpaceAdmin(admin.ModelAdmin):
    """Interface admin pour les espaces de surveillance"""
    
    list_display = ['name', 'code', 'city', 'country', 'organization_id']
    list_filter = ['country', 'city']
    search_fields = ['name', 'code', 'city', 'address']
    readonly_fields = ['id', 'organization_id']
    
    fieldsets = (
        ('Identification', {
            'fields': ('id', 'name', 'code')
        }),
        ('Localisation', {
            'fields': ('address', 'city', 'country')
        }),
        ('Organisation', {
            'fields': ('organization_id',)
        }),
    )


@admin.register(VideoTheftAlert)
class VideoTheftAlertAdmin(admin.ModelAdmin):
    """Interface admin pour les alertes vidéo"""
    
    list_display = [
        'code',
        'status_badge',
        'qualification_display',
        'probability_display',
        'space_name',
        'recording_date_short',
    ]
    list_filter = [
        'status',
        'qualification',
        'recording_date',
    ]
    search_fields = ['code', 'path', 'space__name']
    readonly_fields = [
        'id',
        'recording_date',
        'create_date',
        'probability_display',
    ]
    
    fieldsets = (
        ('📍 Identification', {
            'fields': ('id', 'code', 'camera_id', 'space')
        }),
        ('📹 Vidéo', {
            'fields': ('path', 'recording_date', 'create_date')
        }),
        ('🎯 Détection', {
            'fields': ('probability', 'probability_display', 'nb_alerts')
        }),
        ('✅ Qualification', {
            'fields': ('status', 'qualification', 'sub_status'),
            'description': "Définissez le statut et la qualification de l'alerte"
        }),
        ('👤 Relecteur', {
            'fields': ('reviewer', 'reviewed_at', 'notes'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        """Affiche le statut avec une couleur"""
        colors = {
            'PENDING': '#FFA500',      # Orange
            'APPROVED': '#28a745',     # Vert
            'REJECTED': '#dc3545',     # Rouge
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style=\"background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;\">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Statut'
    
    def qualification_display(self, obj):
        """Affiche la qualification avec icône"""
        icons = {
            'vol': '⚠️',
            'suspicious': '❓',
            'false_alarm': '✅',
            None: '—'
        }
        icon = icons.get(obj.qualification, '—')
        label = obj.get_qualification_display() if obj.qualification else 'Non qualifiée'
        return f"{icon} {label}"
    qualification_display.short_description = 'Qualification'
    
    def probability_display(self, obj):
        """Affiche la probabilité en pourcentage"""
        if not obj.probability:
            return "—"
        percentage = obj.get_probability_percentage()
        color = 'red' if percentage > 70 else 'orange' if percentage > 40 else 'green'
        return format_html(
            '<span style=\"color: {};\">{} %</span>',
            color,
            percentage
        )
    probability_display.short_description = 'Probabilité'
    
    def space_name(self, obj):
        """Affiche le nom de l'espace"""
        return obj.space.name if obj.space else '—'
    space_name.short_description = 'Espace'
    space_name.admin_order_field = 'space__name'
    
    def recording_date_short(self, obj):
        """Affiche la date d'enregistrement formatée"""
        return obj.recording_date.strftime('%d/%m/%Y %H:%M') if obj.recording_date else '—'
    recording_date_short.short_description = "Date d'enregistrement"
    recording_date_short.admin_order_field = 'recording_date'
    
    actions = ['mark_approved', 'mark_rejected', 'mark_pending']
    
    def mark_approved(self, request, queryset):
        """Action : marquer comme approuvée"""
        updated = queryset.update(status='APPROVED')
        self.message_user(request, f"{updated} alerte(s) marquée(s) comme approuvée(s).")
    mark_approved.short_description = "✅ Marquer comme approuvée"
    
    def mark_rejected(self, request, queryset):
        """Action : marquer comme rejetée"""
        updated = queryset.update(status='REJECTED')
        self.message_user(request, f"{updated} alerte(s) marquée(s) comme rejetée(s).")
    mark_rejected.short_description = "❌ Marquer comme rejetée"
    
    def mark_pending(self, request, queryset):
        """Action : marquer comme en attente"""
        updated = queryset.update(status='PENDING')
        self.message_user(request, f"{updated} alerte(s) remise(s) en attente.")
    mark_pending.short_description = "⏳ Marquer comme en attente"