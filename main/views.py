from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.safestring import mark_safe
from django.http import FileResponse, Http404

from .models import Site, Operation, OperationType, Item
from django.utils import timezone

from main.services.stocks import get_stock_rows, get_available_quantity
from main.services.invoices import attach_invoice_to_operation
from main.services.emailing import send_invoice_email
from main.services.local_site import get_local_site

from django.db.models import Q


@login_required(login_url='/login/')
def home(request):
    # «Локальный» склад (инстанс приложения привязан к нему)
    local_site = get_local_site()

    # Получаем данные для формы
    sites = Site.objects.all()
    items = Item.objects.all().order_by('name')

    # Остатки на главной больше не показываем (перенесено на отдельную страницу)

    # Обработка формы создания операции
    if request.method == 'POST':
        # Примитивное добавление ТМЦ прямо с главной (чтобы не тащить отдельный UI)
        if request.POST.get('form_type') == 'add_item':
            name = (request.POST.get('item_new_name') or '').strip()
            unit = (request.POST.get('item_new_unit') or 'шт').strip() or 'шт'
            if not name:
                messages.error(request, 'Введите наименование ТМЦ')
                return redirect('/')
            item, created = Item.objects.get_or_create(name=name, defaults={'default_unit': unit})
            if created:
                messages.success(request, f'ТМЦ "{item.name}" добавлено')
            else:
                messages.info(request, f'ТМЦ "{item.name}" уже существует')
            return redirect('/')

        try:
            if request.POST.get('form_type') != 'operation':
                raise ValueError('Неизвестная форма')

            op_type = request.POST['operation_type']

            item_id = request.POST.get('item_id')
            if not item_id:
                messages.error(request, 'Выберите ТМЦ')
                return redirect('/')
            item = Item.objects.get(id=item_id)

            operation = Operation(
                operation_type=op_type,
                created_by=request.user,
                item=item,
                item_name=item.name,  # legacy для отображения в старых местах
                serial=request.POST.get('serial', '') or None,
                quantity=float(request.POST['quantity']),
                unit=(item.default_unit or 'шт').strip(),
                receiver_name=(request.POST.get('receiver_name') or '').strip() or None,
                vehicle=(request.POST.get('vehicle') or '').strip() or None,
                comment=(request.POST.get('comment') or '').strip() or None,
            )

            if op_type == OperationType.MOVE:
                # Перемещение: оба склада обязательны
                operation.from_site_id = request.POST['from_site']
                operation.to_site_id = request.POST['to_site']
                if not operation.from_site_id or not operation.to_site_id:
                    messages.error(request, 'Для перемещения укажите "Откуда" и "Куда"')
                    return redirect('/')
                if operation.from_site_id == operation.to_site_id:
                    messages.error(request, 'Для перемещения склады "Откуда" и "Куда" должны быть разными')
                    return redirect('/')

                # ВАЖНО: перемещение не может быть между двумя «чужими» складами.
                if int(operation.from_site_id) != local_site.id and int(operation.to_site_id) != local_site.id:
                    messages.error(
                        request,
                        f'Перемещение должно затрагивать локальный склад "{local_site.name}".'
                    )
                    return redirect('/')

            elif op_type == OperationType.INCOMING:
                # Приход: только "Куда" обязательно
                # Локальная установка: приход всегда на локальный склад
                operation.to_site_id = local_site.id

            elif op_type == OperationType.WRITEOFF:
                # Списание: только "Откуда" обязательно
                # Локальная установка: списание всегда с локального склада
                operation.from_site_id = local_site.id

            elif op_type == OperationType.ISSUE:
                # Выдача: только "Откуда" обязательно
                # Локальная установка: выдача всегда с локального склада
                operation.from_site_id = local_site.id

            # Проверка на отрицательные остатки
            if op_type in (OperationType.MOVE, OperationType.WRITEOFF, OperationType.ISSUE):
                available = get_available_quantity(site_id=int(operation.from_site_id), item_id=item.id)
                if operation.quantity > available + 1e-9:
                    messages.error(
                        request,
                        f'Недостаточно остатка на складе. Доступно: {available:g} {operation.display_unit}, '
                        f'запрошено: {operation.quantity:g} {operation.display_unit}.'
                    )
                    return redirect('/')

            operation.save()

            # Генерим накладную и отправляем письмо (минимум: move + issue)
            if op_type in (OperationType.MOVE, OperationType.ISSUE):
                attach_invoice_to_operation(operation)
                send_invoice_email(operation)

            pdf_link = ''
            if operation.pdf_file:
                pdf_link = f" <a href='/operations/{operation.id}/pdf/' target='_blank'>Скачать накладную PDF</a>"

            messages.success(request, f'Операция "{operation.get_operation_type_display()}" создана!')
            if pdf_link:
                messages.success(request, mark_safe(pdf_link))
            return redirect('/')

        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
            return redirect('/')

    # Операции за сегодня
    today = timezone.now().date()
    local_filter = Q(from_site=local_site) | Q(to_site=local_site)
    today_operations = Operation.objects.filter(
        local_filter,
        created_at__date=today,
    ).select_related('from_site', 'to_site', 'created_by', 'item').order_by('-created_at')[:50]

    # Последние 10 операций
    last_operations = Operation.objects.filter(local_filter).select_related('from_site', 'to_site', 'created_by', 'item').order_by(
        '-created_at')[:10]

    context = {
        'sites': sites,  # Теперь переменная определена
        'items': items,
        'today_operations': today_operations,
        'last_operations': last_operations,
        'operation_types': OperationType.choices,
        'local_site': local_site,
    }

    return render(request, 'main/home.html', context)


@login_required(login_url='/login/')
def stocks(request):
    """Остатки (вынесены с главной на отдельную страницу)."""
    local_site = get_local_site()

    # На локальной установке логичнее показывать остатки только своего склада.
    stock_rows = get_stock_rows(site_id=local_site.id)

    # Базовый поиск и сортировка (без JS-магии, всё сервером).
    q = (request.GET.get('q') or '').strip()
    if q:
        q_l = q.lower()
        stock_rows = [r for r in stock_rows if q_l in (r.item.name or '').lower()]

    sort = (request.GET.get('sort') or 'item').strip().lower()
    direction = (request.GET.get('dir') or 'asc').strip().lower()
    reverse = direction == 'desc'

    if sort == 'qty':
        stock_rows.sort(key=lambda r: float(r.quantity), reverse=reverse)
    elif sort == 'unit':
        stock_rows.sort(key=lambda r: (r.unit or '').lower(), reverse=reverse)
    else:  # item
        stock_rows.sort(key=lambda r: (r.item.name or '').lower(), reverse=reverse)

    return render(
        request,
        'main/stocks.html',
        {
            'local_site': local_site,
            'stock_rows': stock_rows,
            'q': q,
            'sort': sort,
            'dir': direction,
        }
    )


@login_required(login_url='/login/')
def operation_pdf(request, pk: int):
    op = get_object_or_404(Operation, pk=pk)
    if not op.pdf_file:
        raise Http404('PDF не найден')

    filename = (op.pdf_file.name or '').rsplit('/', 1)[-1] or f'invoice_{op.id}.pdf'
    download = (request.GET.get('download') or '').strip() in ('1', 'true', 'yes')

    resp = FileResponse(op.pdf_file.open('rb'), content_type='application/pdf')
    # Делаем поведение явным: либо открыть в браузере, либо скачать.
    disp_type = 'attachment' if download else 'inline'
    resp['Content-Disposition'] = f'{disp_type}; filename="{filename}"'
    return resp


@login_required(login_url='/login/')
def operation_invoice_generate(request, pk: int):
    """Явная генерация накладной по кнопке из списка операций."""
    if request.method != 'POST':
        # Не даём генерить по GET, чтобы не было случайных кликов/ботов.
        return redirect('/')

    op = get_object_or_404(Operation, pk=pk)

    # Накладная нужна только там, где есть смысл (минимум: перемещение и выдача).
    if op.operation_type not in (OperationType.MOVE, OperationType.ISSUE):
        messages.info(request, 'Для этой операции накладная не предусмотрена.')
        return redirect('/')

    if not op.pdf_file:
        attach_invoice_to_operation(op)

    if op.pdf_file:
        messages.success(request, mark_safe(
            f"Накладная сформирована: <a href='/operations/{op.id}/pdf/' target='_blank'>Открыть</a> | "
            f"<a href='/operations/{op.id}/pdf/?download=1'>Скачать</a>"
        ))
    else:
        messages.error(request, 'Не удалось сформировать накладную (PDF не создан).')

    # Возвращаем пользователя туда, где он был (главная), без усложнений.
    return redirect('/')