from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.safestring import mark_safe

from main.auth_utils import can_manage_catalog, chief_required
from main.forms import CategoryForm, ItemForm, OperationFilterForm, OperationForm, SiteForm
from main.models import Category, Item, Operation, OperationType, Site
from main.services.emailing import send_invoice_email
from main.services.invoices import attach_invoice_to_operation
from main.services.local_site import get_local_site
from main.services.stocks import get_available_quantity, get_stock_rows


def _operation_queryset_for_local(local_site):
    local_filter = Q(from_site=local_site) | Q(to_site=local_site)
    return Operation.objects.filter(local_filter).select_related('from_site', 'to_site', 'created_by', 'item')


@login_required(login_url='/login/')
def home(request):
    local_site = get_local_site()
    sites = Site.objects.filter(is_active=True).order_by('name')

    form = OperationForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            op_type = form.cleaned_data['operation_type']
            item = form.cleaned_data['item_id']
            quantity = form.cleaned_data['quantity']
            from_site = form.cleaned_data['from_site']
            to_site = form.cleaned_data['to_site']

            if op_type == OperationType.MOVE:
                if not from_site or not to_site:
                    messages.error(request, 'Для перемещения укажите склады "Откуда" и "Куда".')
                    return redirect('home')
                if from_site == to_site:
                    messages.error(request, 'Для перемещения склады "Откуда" и "Куда" должны быть разными.')
                    return redirect('home')
                if from_site.id != local_site.id and to_site.id != local_site.id:
                    messages.error(request, f'Перемещение должно затрагивать локальный склад "{local_site.name}".')
                    return redirect('home')
            elif op_type == OperationType.INCOMING:
                from_site = None
                to_site = local_site
            elif op_type in (OperationType.WRITEOFF, OperationType.ISSUE):
                from_site = local_site
                to_site = None

            if op_type in (OperationType.MOVE, OperationType.WRITEOFF, OperationType.ISSUE):
                available = get_available_quantity(site_id=from_site.id, item_id=item.id)
                if quantity > available + 1e-9:
                    messages.error(
                        request,
                        f'Недостаточно остатка на складе. Доступно: {available:g} {item.default_unit}, '
                        f'запрошено: {quantity:g} {item.default_unit}.',
                    )
                    return redirect('home')

            operation = Operation.objects.create(
                operation_type=op_type,
                created_by=request.user,
                item=item,
                item_name=item.name,
                serial=form.cleaned_data['serial'] or None,
                quantity=quantity,
                unit=(item.default_unit or 'шт').strip(),
                receiver_name=form.cleaned_data['receiver_name'] or None,
                vehicle=form.cleaned_data['vehicle'] or None,
                comment=form.cleaned_data['comment'] or None,
                from_site=from_site,
                to_site=to_site,
            )

            if op_type in (OperationType.MOVE, OperationType.ISSUE):
                attach_invoice_to_operation(operation)
                send_invoice_email(operation)

            messages.success(request, f'Операция "{operation.get_operation_type_display()}" создана.')
            return redirect('home')

        messages.error(request, 'Проверьте корректность заполнения формы операции.')

    today = timezone.now().date()
    qs = _operation_queryset_for_local(local_site)
    context = {
        'form': form,
        'sites': sites,
        'today_operations': qs.filter(created_at__date=today)[:50],
        'last_operations': qs[:10],
        'local_site': local_site,
        'can_manage_catalog': can_manage_catalog(request.user),
    }
    return render(request, 'main/home.html', context)


@login_required(login_url='/login/')
def stocks(request):
    local_site = get_local_site()
    stock_rows = get_stock_rows(site_id=local_site.id)

    q = (request.GET.get('q') or '').strip()
    if q:
        q_l = q.lower()
        stock_rows = [r for r in stock_rows if q_l in (r.item.name or '').lower() or q_l in (r.item.sku or '').lower()]

    sort = (request.GET.get('sort') or 'item').strip().lower()
    direction = (request.GET.get('dir') or 'asc').strip().lower()
    reverse = direction == 'desc'

    if sort == 'qty':
        stock_rows.sort(key=lambda r: float(r.quantity), reverse=reverse)
    elif sort == 'unit':
        stock_rows.sort(key=lambda r: (r.unit or '').lower(), reverse=reverse)
    else:
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
            'can_manage_catalog': can_manage_catalog(request.user),
        },
    )


@login_required(login_url='/login/')
def operations_list(request):
    local_site = get_local_site()
    form = OperationFilterForm(request.GET or None)
    qs = _operation_queryset_for_local(local_site)

    if form.is_valid():
        q = form.cleaned_data['q']
        if q:
            qs = qs.filter(
                Q(item__name__icontains=q)
                | Q(item__sku__icontains=q)
                | Q(serial__icontains=q)
                | Q(comment__icontains=q)
            )
        if form.cleaned_data['operation_type']:
            qs = qs.filter(operation_type=form.cleaned_data['operation_type'])
        if form.cleaned_data['date_from']:
            qs = qs.filter(created_at__date__gte=form.cleaned_data['date_from'])
        if form.cleaned_data['date_to']:
            qs = qs.filter(created_at__date__lte=form.cleaned_data['date_to'])

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'main/operations_list.html',
        {'filter_form': form, 'page_obj': page_obj, 'can_manage_catalog': can_manage_catalog(request.user)},
    )


@login_required(login_url='/login/')
def operation_pdf(request, pk: int):
    op = get_object_or_404(Operation, pk=pk)
    if not op.pdf_file:
        raise Http404('PDF не найден')

    filename = (op.pdf_file.name or '').rsplit('/', 1)[-1] or f'invoice_{op.id}.pdf'
    download = (request.GET.get('download') or '').strip() in ('1', 'true', 'yes')

    resp = FileResponse(op.pdf_file.open('rb'), content_type='application/pdf')
    disp_type = 'attachment' if download else 'inline'
    resp['Content-Disposition'] = f'{disp_type}; filename="{filename}"'
    return resp


@login_required(login_url='/login/')
def operation_invoice_generate(request, pk: int):
    if request.method != 'POST':
        return redirect('operations_list')

    op = get_object_or_404(Operation, pk=pk)
    if op.operation_type not in (OperationType.MOVE, OperationType.ISSUE):
        messages.info(request, 'Для этой операции накладная не предусмотрена.')
        return redirect('operations_list')

    if not op.pdf_file:
        attach_invoice_to_operation(op)

    if op.pdf_file:
        messages.success(
            request,
            mark_safe(
                f"Накладная сформирована: <a href='/operations/{op.id}/pdf/' target='_blank'>Открыть</a> | "
                f"<a href='/operations/{op.id}/pdf/?download=1'>Скачать</a>"
            ),
        )
    else:
        messages.error(request, 'Не удалось сформировать накладную (PDF не создан).')
    return redirect(request.POST.get('next') or 'operations_list')


@chief_required
def items_list(request):
    qs = Item.objects.select_related('category').order_by('name')
    q = (request.GET.get('q') or '').strip()
    category_id = (request.GET.get('category') or '').strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q))
    if category_id:
        qs = qs.filter(category_id=category_id)
    return render(
        request,
        'main/items_list.html',
        {
            'items': qs,
            'q': q,
            'categories': Category.objects.order_by('name'),
            'category_id': category_id,
            'can_manage_catalog': can_manage_catalog(request.user),
        },
    )


@chief_required
def item_create(request):
    form = ItemForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'ТМЦ создано.')
        return redirect('items_list')
    return render(request, 'main/catalog_form.html', {'form': form, 'title': 'Создать ТМЦ', 'can_manage_catalog': True})


@chief_required
def item_edit(request, pk: int):
    obj = get_object_or_404(Item, pk=pk)
    form = ItemForm(request.POST or None, instance=obj)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'ТМЦ обновлено.')
        return redirect('items_list')
    return render(request, 'main/catalog_form.html', {'form': form, 'title': 'Редактировать ТМЦ', 'can_manage_catalog': True})


@chief_required
def categories_list(request):
    categories = Category.objects.select_related('parent').order_by('name')
    return render(request, 'main/categories_list.html', {'categories': categories, 'can_manage_catalog': True})


@chief_required
def category_create(request):
    form = CategoryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Категория создана.')
        return redirect('categories_list')
    return render(request, 'main/catalog_form.html', {'form': form, 'title': 'Создать категорию', 'can_manage_catalog': True})


@chief_required
def category_edit(request, pk: int):
    obj = get_object_or_404(Category, pk=pk)
    form = CategoryForm(request.POST or None, instance=obj)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Категория обновлена.')
        return redirect('categories_list')
    return render(request, 'main/catalog_form.html', {'form': form, 'title': 'Редактировать категорию', 'can_manage_catalog': True})


@chief_required
def sites_list(request):
    sites = Site.objects.order_by('name')
    return render(request, 'main/sites_list.html', {'sites': sites, 'can_manage_catalog': True})


@chief_required
def site_create(request):
    form = SiteForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Склад создан.')
        return redirect('sites_list')
    return render(request, 'main/catalog_form.html', {'form': form, 'title': 'Создать склад', 'can_manage_catalog': True})


@chief_required
def site_edit(request, pk: int):
    obj = get_object_or_404(Site, pk=pk)
    form = SiteForm(request.POST or None, instance=obj)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Склад обновлён.')
        return redirect('sites_list')
    return render(request, 'main/catalog_form.html', {'form': form, 'title': 'Редактировать склад', 'can_manage_catalog': True})
