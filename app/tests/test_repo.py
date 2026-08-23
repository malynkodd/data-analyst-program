"""Дерево строится из blueprint, а не из своего списка.

Порядок прохождения и названия модулей приложение берёт из
`design/blueprint.md` — часть 6.2 («Этапы и недели») и часть 6.1 («Часы по
модулям»). Свой список в коде разошёлся бы с проектом молча: blueprint
правится решениями, а копия — нет. Тест сторожит именно эту связь: если
таблицу переименуют или переформатируют, дерево обязано сломаться здесь,
а не в браузере.
"""

from __future__ import annotations

import repo


def test_every_module_folder_has_a_human_name() -> None:
    """У каждой папки `program/` есть имя — иначе в дереве останется код."""
    catalog = repo.catalog()
    for module in repo.modules():
        assert module in catalog, f"{module} не назван ни в 6.1, ни в декларации проекта"
        assert catalog[module]["name"], f"{module}: пустое имя"
        assert catalog[module]["hours"], f"{module}: пустые часы"


def test_names_come_from_blueprint_verbatim() -> None:
    catalog = repo.catalog()
    assert catalog["M3"]["name"] == "SQL"
    assert catalog["M4"] == {"name": "Power BI", "hours": "26–35"}
    assert catalog["M5"]["hours"] == "43–56"  # вилка решения 31, не 80–120
    assert catalog["P1"]["name"] == "Какая точка худшая"
    assert catalog[repo.CAREER]["hours"] == "8–11"  # вилка решения 37


def test_six_stages_in_blueprint_order() -> None:
    stages = repo.stages()
    assert [s["number"] for s in stages] == [1, 2, 3, 4, 5, 6]
    assert [s["name"] for s in stages] == [
        "Основание", "Данные в руках", "Показать",
        "Автоматизировать", "Специализация", "Выход",
    ]
    assert stages[1]["codes"] == ["M2", "M3", "M10", "P1", "P2"]
    assert repo.CAREER in stages[5]["codes"], "блок «Выход» не привязан к этапу 6"


def test_stage_order_covers_every_module_exactly_once() -> None:
    order = repo.stage_order()
    assert len(order) == len(set(order)), "модуль попал в дерево дважды"
    assert set(order) == set(repo.modules()), "модуль потерялся между этапами и деревом"
    assert order[0] == "M0", "прохождение начинается не с M0"


def test_sections_keep_file_order_and_mark_the_two_that_matter() -> None:
    secs = repo.ordered_sections(repo.step_text("M4", 5))
    assert [s["num"] for s in secs] == ["1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7", "1.8"]
    assert [s["num"] for s in secs if s["key"]] == ["1.4", "1.5"]
    assert secs[4]["title"] == "Критерий готовности"
    assert all(s["hint"] for s in secs), "у раздела нет подписи для интерфейса"


def test_section_bodies_do_not_lose_text() -> None:
    """Тело раздела — то же, что отдаёт `sections()`, без заголовка."""
    text = repo.step_text("M4", 5)
    whole = repo.sections(text)["1.5"]
    body = next(s for s in repo.ordered_sections(text) if s["num"] == "1.5")["body"]
    assert body in whole
    assert len(body) > len(whole) - 60, "из раздела пропал текст, а не только заголовок"


def test_preamble_drops_header_fields_but_keeps_warnings() -> None:
    """Шапка `Умение:`/`Время:` показана чипами, повторять её в теле не нужно."""
    pre = repo.preamble(repo.step_text("M4", 0))
    assert "Умение:" not in pre and "Время:" not in pre
    assert "Не шаг для учащегося" in pre  # предупреждение декларации осталось
