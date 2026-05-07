"""
views/mlops.py — Endpoints Admin MLOps
Tous protégés par IsAdminUser.
"""
import csv
import json
import logging
from datetime import timedelta

from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Avg, Count, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework import status

from ..models import NLUFallbackLog, RetrainingLog
from ..permissions import IsAdminUser
from ..serializers.mlops import (
    NLUFallbackLogListSerializer,
    NLUFallbackLogReviewSerializer,
    RetrainingLogSerializer,
)

logger = logging.getLogger(__name__)

# ─── 1. Stats globales ───────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAdminUser])
def mlops_stats(request):
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    seven_days_ago  = today - timedelta(days=7)

    total_fallbacks_30d = NLUFallbackLog.objects.filter(created_at__date__gte=thirty_days_ago).count()
    reviewed_count = NLUFallbackLog.objects.filter(reviewed=True).count()
    pending_review = NLUFallbackLog.objects.filter(reviewed=False).count()

    avg_confidence = NLUFallbackLog.objects.filter(
        created_at__date__gte=thirty_days_ago,
        tunbert_confidence__isnull=False,
    ).aggregate(avg=Avg('tunbert_confidence'))['avg'] or 0.0

    by_reason = list(
        NLUFallbackLog.objects
        .filter(created_at__date__gte=thirty_days_ago)
        .values('trigger_reason')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    sparkline = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        sparkline.append(NLUFallbackLog.objects.filter(created_at__date=d).count())

    last_retrain = RetrainingLog.objects.first()
    last_retrain_data = RetrainingLogSerializer(last_retrain).data if last_retrain else None

    return Response({
        'reviewed_count':      reviewed_count,
        'pending_review':      pending_review,
        'total_fallbacks_30d': total_fallbacks_30d,
        'avg_tunbert_confidence': round(avg_confidence, 3),
        'fallback_by_reason':  by_reason,
        'sparkline_7d':        sparkline,
        'last_retraining':     last_retrain_data,
    })


# ─── 2. Liste paginée des fallbacks ─────────────────────────────────────────

class FallbackPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@api_view(['GET'])
@permission_classes([IsAdminUser])
def mlops_fallbacks_list(request):
    qs = NLUFallbackLog.objects.select_related('message').all()

    reviewed_param = request.query_params.get('reviewed')
    if reviewed_param is not None:
        qs = qs.filter(reviewed=(reviewed_param.lower() == 'true'))

    trigger = request.query_params.get('trigger')
    if trigger:
        qs = qs.filter(trigger_reason=trigger.upper())

    intent = request.query_params.get('intent')
    if intent:
        qs = qs.filter(Q(tunbert_intent=intent) | Q(gemini_intent=intent))

    search = request.query_params.get('search')
    if search:
        qs = qs.filter(original_text__icontains=search)

    paginator = FallbackPagination()
    page = paginator.paginate_queryset(qs, request)
    serializer = NLUFallbackLogListSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


# ─── 3. Révision d'un label (PATCH) ─────────────────────────────────────────

@api_view(['PATCH'])
@permission_classes([IsAdminUser])
def mlops_review_fallback(request, pk):
    try:
        log = NLUFallbackLog.objects.get(pk=pk)
    except NLUFallbackLog.DoesNotExist:
        return Response({'error': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)

    serializer = NLUFallbackLogReviewSerializer(log, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({'id': pk, 'reviewed': True, 'review_label': log.review_label})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ─── 4. Export dataset ───────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAdminUser])
def mlops_export(request):
    export_format = request.query_params.get('format', 'json').lower()
    reviewed_only = request.query_params.get('reviewed', 'true').lower() == 'true'

    qs = NLUFallbackLog.objects.all()
    if reviewed_only:
        qs = qs.filter(reviewed=True, review_label__isnull=False)

    trigger = request.query_params.get('trigger')
    if trigger:
        qs = qs.filter(trigger_reason=trigger.upper())

    date_from = request.query_params.get('date_from')
    date_to   = request.query_params.get('date_to')
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    if export_format == 'json':
        data = [
            {
                'original_text':      obj.original_text,
                'tunbert_intent':     obj.tunbert_intent,
                'tunbert_confidence': obj.tunbert_confidence,
                'gemini_intent':      obj.gemini_intent,
                'review_label':       obj.review_label,
                'trigger_reason':     obj.trigger_reason,
                'label':              obj.review_label or obj.gemini_intent,
            }
            for obj in qs
        ]
        response = HttpResponse(json.dumps(data, ensure_ascii=False, indent=2), content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="fallback_logs.json"'
        return response

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="fallback_logs.csv"'
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow(['id', 'original_text', 'tunbert_intent', 'tunbert_confidence', 'gemini_intent', 'review_label', 'trigger_reason', 'created_at'])
    for obj in qs:
        writer.writerow([obj.id, obj.original_text, obj.tunbert_intent, obj.tunbert_confidence, obj.gemini_intent, obj.review_label or obj.gemini_intent, obj.trigger_reason, obj.created_at.strftime('%Y-%m-%d %H:%M')])
    return response


# ─── 5. Trigger réentraînement ───────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAdminUser])
def mlops_retrain_trigger(request):
    reviewed_count = NLUFallbackLog.objects.filter(reviewed=True).count()

    if reviewed_count < 50:
        return Response({'error': f'Pas assez d exemples revises ({reviewed_count}/50 minimum).'}, status=status.HTTP_400_BAD_REQUEST)

    log = RetrainingLog.objects.create(status='PENDING', samples=reviewed_count, triggered_by=request.user.username)
    return Response({'message': 'Retraining enregistre.', 'log_id': log.id, 'samples': reviewed_count}, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAdminUser])
def mlops_retrain_status(request):
    last = RetrainingLog.objects.first()
    history = RetrainingLog.objects.all()[:10]
    return Response({'current': RetrainingLogSerializer(last).data if last else None, 'history': RetrainingLogSerializer(history, many=True).data})


# ─── 6. Enregistrement déploiement + rapport complet (appelé par GitHub Actions)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def mlops_deployment_log(request):
    old_f1          = request.data.get('old_f1')
    new_f1          = request.data.get('new_f1')
    run_number      = request.data.get('run')
    training_report = request.data.get('report')

    log = RetrainingLog.objects.filter(status__in=['PENDING', 'RUNNING']).first()
    deployed = new_f1 and old_f1 and (float(new_f1) > float(old_f1))

    if log:
        log.old_f1          = old_f1
        log.new_f1          = new_f1
        log.run_number      = run_number
        log.deployed        = deployed
        log.training_report = training_report
        log.status          = 'SUCCESS' if deployed else 'SKIPPED'
        log.finished_at     = timezone.now()
        log.save()
        return Response({'updated': log.id, 'deployed': deployed})

    log = RetrainingLog.objects.create(
        status='SUCCESS',
        old_f1=old_f1, new_f1=new_f1,
        run_number=run_number,
        deployed=deployed,
        training_report=training_report,
        finished_at=timezone.now(),
        triggered_by='github_actions',
    )
    return Response({'created': log.id}, status=status.HTTP_201_CREATED)


# ─── 7. Rapport détaillé d'un run ────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAdminUser])
def mlops_retrain_report(request, pk):
    try:
        log = RetrainingLog.objects.get(pk=pk)
    except RetrainingLog.DoesNotExist:
        return Response({'error': 'Run introuvable.'}, status=status.HTTP_404_NOT_FOUND)

    if not log.training_report:
        return Response({'error': 'Aucun rapport disponible pour ce run.'}, status=404)

    return Response({
        'run_id':   log.id,
        'status':   log.status,
        'old_f1':   log.old_f1,
        'new_f1':   log.new_f1,
        'deployed': log.deployed,
        'report':   log.training_report,
    })
