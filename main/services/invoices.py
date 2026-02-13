from __future__ import annotations

import io
from datetime import datetime

from django.conf import settings
from django.core.files.base import ContentFile

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet


_FONTS_REGISTERED = False


def _register_fonts_once() -> None:
    """Регистрируем кириллический шрифт для reportlab.

    Пытаемся использовать DejaVuSans (обычно есть в Linux). Если его нет, упадём на стандартные шрифты
    (тогда кириллица может выглядеть грустно).
    """
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return

    try:
        pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
        pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
        _FONTS_REGISTERED = True
    except Exception:
        # Ничего страшного. Просто не будет кириллического шрифта.
        _FONTS_REGISTERED = True


def build_invoice_pdf_bytes(operation) -> bytes:
    """Генерирует PDF накладной и возвращает байты."""
    _register_fonts_once()

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title='Накладная',
    )

    styles = getSampleStyleSheet()
    normal = styles['Normal']
    title_style = styles['Title']

    # Если шрифты зарегистрированы, подцепим их в стили
    try:
        pdfmetrics.getFont('DejaVuSans')
        normal.fontName = 'DejaVuSans'
        try:
            pdfmetrics.getFont('DejaVuSans-Bold')
            title_style.fontName = 'DejaVuSans-Bold'
        except Exception:
            title_style.fontName = 'DejaVuSans'
    except Exception:
        pass

    op_dt: datetime = operation.created_at
    number = operation.id
    date_str = op_dt.strftime('%d.%m.%Y')

    shipper = getattr(settings, 'INVOICE_SHIPPER', 'Грузоотправитель: (не задано в настройках)')
    consignee = getattr(settings, 'INVOICE_CONSIGNEE', 'ООО АС «Горизонт»')
    permit_by = getattr(settings, 'INVOICE_PERMIT_BY', 'Отпуск разрешил: __________________')

    basis = _build_basis_text(operation)
    storekeeper_name = _display_user_name(operation.created_by)

    story = []
    story.append(Paragraph(f"Накладная №{number} от {date_str}", title_style))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(f"{shipper}", normal))
    story.append(Paragraph(f"Грузополучатель: {consignee}", normal))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(f"Основание для отпуска: {basis}", normal))
    story.append(Spacer(1, 6 * mm))

    data = [
        ['№', 'Наименование ТМЦ', 'Ед. изм', 'Кол-во'],
        ['1', operation.display_item_name, operation.display_unit, f"{operation.quantity:g}"],
    ]
    table = Table(data, colWidths=[12 * mm, 110 * mm, 25 * mm, 25 * mm])
    table.setStyle(
        TableStyle(
            [
                ('FONTNAME', (0, 0), (-1, -1), normal.fontName),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (-1, 1), (-1, -1), 'RIGHT'),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 12 * mm))

    story.append(Paragraph(permit_by, normal))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(f"Отпустил: {storekeeper_name}", normal))

    doc.build(story)

    return buffer.getvalue()


def attach_invoice_to_operation(operation) -> None:
    """Генерирует PDF и сохраняет в Operation.pdf_file (если ещё нет)."""
    if operation.pdf_file:
        return

    pdf_bytes = build_invoice_pdf_bytes(operation)
    filename = f"invoice_{operation.id}.pdf"
    operation.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)


def _build_basis_text(operation) -> str:
    t = operation.operation_type
    if t == 'move':
        return f"Перемещение: {operation.from_site} → {operation.to_site}"
    if t == 'issue':
        who = operation.receiver_name or 'получатель не указан'
        veh = f", транспорт: {operation.vehicle}" if operation.vehicle else ''
        return f"Выдача: {who}{veh}"
    if t == 'incoming':
        return f"Приход на склад: {operation.to_site}"
    if t == 'writeoff':
        return f"Списание со склада: {operation.from_site}"
    return operation.get_operation_type_display()


def _display_user_name(user) -> str:
    if hasattr(user, 'profile') and getattr(user.profile, 'full_name', ''):
        return user.profile.full_name
    if user.first_name or user.last_name:
        return f"{user.first_name or ''} {user.last_name or ''}".strip()
    return user.username
