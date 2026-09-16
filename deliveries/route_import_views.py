from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .import_services import validate_upload
from .import_staging import consume_upload, stage_upload
from .models import RouteOrderSuggestion, RouteRun, RouteTemplate
from .route_import_services import (
    apply_workbook_to_run,
    apply_workbook_to_template,
    preview_route_workbook,
)
from .route_services import decide_order_suggestion
from .route_views import dispatcher_required


@dispatcher_required
def template_import_excel(request, pk):
    template = get_object_or_404(RouteTemplate.objects.select_related('route'), pk=pk)
    summary = None
    preview_token = ''
    filename = ''
    current_ids = list(template.items.order_by('route_order', 'id').values_list('point_id', flat=True))
    if request.method == 'POST':
        try:
            if request.POST.get('action') == 'commit':
                filename, content = consume_upload(request.POST.get('token', ''), request.user.pk)
                validate_upload(filename, content)
                mode = request.POST.get('mode', 'replace')
                result = apply_workbook_to_template(content, template, mode=mode)
                messages.success(
                    request,
                    f'Excel применён к шаблону: {result.applied} точек; новых в справочнике {result.created_points}; '
                    f'убрано из шаблона {result.removed}.',
                )
                return redirect(f'/dispatcher/routes/{template.route_id}/?template={template.pk}')
            uploaded = request.FILES.get('file')
            if not uploaded:
                raise ValueError('Выберите XLSX-файл')
            content = uploaded.read()
            filename = uploaded.name
            validate_upload(filename, content)
            summary = preview_route_workbook(content, current_ids)
            preview_token = stage_upload(content, request.user.pk, filename)
        except Exception as exc:
            messages.error(request, f'Не удалось обработать Excel: {exc}')
    return render(
        request,
        'dispatcher/routes/excel_import.html',
        {
            'target_type': 'template',
            'target': template,
            'route': template.route,
            'summary': summary,
            'preview_token': preview_token,
            'filename': filename,
        },
    )


@dispatcher_required
def run_import_excel(request, pk):
    run = get_object_or_404(RouteRun.objects.select_related('route', 'template', 'assigned_courier'), pk=pk)
    summary = None
    preview_token = ''
    filename = ''
    current_ids = list(run.deliveries.order_by('route_order', 'id').values_list('point_id', flat=True))
    if request.method == 'POST':
        try:
            if request.POST.get('action') == 'commit':
                filename, content = consume_upload(request.POST.get('token', ''), request.user.pk)
                validate_upload(filename, content)
                mode = request.POST.get('mode', 'replace')
                result = apply_workbook_to_run(content, run, actor=request.user, mode=mode)
                messages.success(
                    request,
                    f'Excel применён только к {run.run_date:%d.%m.%Y}: {result.applied} точек; '
                    f'новых в справочнике {result.created_points}; убрано из маршрута дня {result.removed}.',
                )
                return redirect('run_detail', pk=run.pk)
            uploaded = request.FILES.get('file')
            if not uploaded:
                raise ValueError('Выберите XLSX-файл')
            content = uploaded.read()
            filename = uploaded.name
            validate_upload(filename, content)
            summary = preview_route_workbook(content, current_ids)
            preview_token = stage_upload(content, request.user.pk, filename)
        except Exception as exc:
            messages.error(request, f'Не удалось обработать Excel: {exc}')
    return render(
        request,
        'dispatcher/routes/excel_import.html',
        {
            'target_type': 'run',
            'target': run,
            'route': run.route,
            'summary': summary,
            'preview_token': preview_token,
            'filename': filename,
        },
    )


@dispatcher_required
@require_POST
def order_suggestion_decide(request, pk):
    suggestion = get_object_or_404(
        RouteOrderSuggestion.objects.select_related('run__route', 'run__template', 'courier'),
        pk=pk,
    )
    try:
        decide_order_suggestion(suggestion, request.POST.get('action', ''), request.user)
    except ValueError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, 'Решение по порядку маршрута сохранено')
    return redirect('run_detail', pk=suggestion.run_id)
