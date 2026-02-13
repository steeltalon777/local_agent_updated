from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Optional

from django.db.models import Sum

from main.models import Item, Operation, OperationType, Site


@dataclass(frozen=True)
class StockRow:
    site: Site
    item: Item
    quantity: float

    @property
    def unit(self) -> str:
        return self.item.default_unit


def get_stock_rows(site_id: Optional[int] = None) -> list[StockRow]:
    """Считает остатки как ledger-агрегацию движений.

    Правило:
      - incoming: + на to_site
      - move:     - на from_site, + на to_site
      - writeoff: - на from_site
      - issue:    - на from_site

    Возвращает список строк для UI.
    """

    # + на to_site
    plus_qs = Operation.objects.filter(
        item__isnull=False,
        to_site__isnull=False,
        operation_type__in=[OperationType.INCOMING, OperationType.MOVE],
    )
    if site_id:
        plus_qs = plus_qs.filter(to_site_id=site_id)
    plus = (
        plus_qs.values('to_site_id', 'item_id')
        .annotate(q=Sum('quantity'))
    )

    # - на from_site
    minus_qs = Operation.objects.filter(
        item__isnull=False,
        from_site__isnull=False,
        operation_type__in=[OperationType.MOVE, OperationType.WRITEOFF, OperationType.ISSUE],
    )
    if site_id:
        minus_qs = minus_qs.filter(from_site_id=site_id)
    minus = (
        minus_qs.values('from_site_id', 'item_id')
        .annotate(q=Sum('quantity'))
    )

    acc: dict[tuple[int, int], float] = defaultdict(float)
    site_ids: set[int] = set()
    item_ids: set[int] = set()

    for r in plus:
        key = (r['to_site_id'], r['item_id'])
        acc[key] += float(r['q'] or 0)
        site_ids.add(r['to_site_id'])
        item_ids.add(r['item_id'])

    for r in minus:
        key = (r['from_site_id'], r['item_id'])
        acc[key] -= float(r['q'] or 0)
        site_ids.add(r['from_site_id'])
        item_ids.add(r['item_id'])

    sites = {s.id: s for s in Site.objects.filter(id__in=site_ids)}
    items = {i.id: i for i in Item.objects.filter(id__in=item_ids)}

    rows: list[StockRow] = []
    for (s_id, i_id), qty in acc.items():
        # не показываем пустые позиции
        if abs(qty) < 1e-9:
            continue
        s = sites.get(s_id)
        it = items.get(i_id)
        if not s or not it:
            continue
        rows.append(StockRow(site=s, item=it, quantity=qty))

    rows.sort(key=lambda r: (r.site.name.lower(), r.item.name.lower()))
    return rows


def get_available_quantity(site_id: int, item_id: int) -> float:
    """Текущий остаток по (склад, ТМЦ)."""
    rows = get_stock_rows(site_id=site_id)
    for r in rows:
        if r.item.id == item_id:
            return float(r.quantity)
    return 0.0
