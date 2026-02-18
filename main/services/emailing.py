from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMessage

from main.models import AppSettings
from main.services.invoices import _display_user_name


def send_invoice_email(operation) -> None:
    """Отправляет накладную в бухгалтерию.

    Требует настройки SMTP в settings/env. Если ACCOUNTING_EMAIL не задан, молча ничего не делает.
    """

    # Приоритет: админка -> settings/env (OFFICE_EMAIL/ACCOUNTING_EMAIL)
    db_email = ''
    try:
        db_email = (AppSettings.get_solo().office_email or '').strip()
    except Exception:
        db_email = ''

    accounting_email = (
        db_email
        or getattr(settings, 'OFFICE_EMAIL', None)
        or getattr(settings, 'ACCOUNTING_EMAIL', None)
    )
    if not accounting_email:
        return
    if not operation.pdf_file:
        return

    op_dt = operation.created_at
    date_str = op_dt.strftime('%d.%m.%Y')
    subject = f"Накладная №{operation.id} от {date_str} ({operation.get_operation_type_display()})"

    created_by = _display_user_name(operation.created_by)
    from_site = operation.from_site.name if operation.from_site else ''
    to_site = operation.to_site.name if operation.to_site else ''

    lines = [
        f"Создал: {created_by}",
        f"Тип: {operation.get_operation_type_display()}",
        f"ТМЦ: {operation.display_item_name}",
        f"Кол-во: {operation.quantity:g} {operation.display_unit}",
    ]
    if from_site:
        lines.append(f"Откуда: {from_site}")
    if to_site:
        lines.append(f"Куда: {to_site}")
    if operation.receiver_name:
        lines.append(f"Получатель: {operation.receiver_name}")
    if operation.vehicle:
        lines.append(f"Транспорт: {operation.vehicle}")
    if operation.comment:
        lines.append(f"Комментарий: {operation.comment}")

    body = "\n".join(lines)

    msg = EmailMessage(
        subject=subject,
        body=body,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
        to=[accounting_email],
    )

    # attach() принимает bytes
    op_pdf = operation.pdf_file
    op_pdf.open('rb')
    try:
        msg.attach(op_pdf.name.rsplit('/', 1)[-1], op_pdf.read(), 'application/pdf')
    finally:
        op_pdf.close()

    msg.send(fail_silently=False)
