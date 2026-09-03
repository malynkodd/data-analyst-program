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
    assert catalog["M4"] == {"name": "Power BI", "hours": "27–36"}
    assert catalog["M5"]["hours"] == "58–72"  # вилка решения 55, не 80–120
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


def test_header_fields_do_not_bleed_into_each_other() -> None:
    """Чужое поле — не перенос строки предыдущего.

    Шапка шага содержит не только четыре знакомых поля: `program/M4/step-05.md`
    объявляет ещё «Новые колонки к сквозной схеме модуля». Пока разбор знал
    только знакомые ключи, этот текст приклеивался к «Требуется до этого» —
    и подсказка о предусловии показывала абзац про схему датасета.
    """
    header = repo.step("M4", 5).header
    assert header["Требуется до этого"].endswith("сошлись с эталонами)")
    assert "Новые колонки" not in header["Требуется до этого"]
    assert header["Новые колонки к сквозной схеме модуля"].startswith("нет.")
    assert header["Время"] == "6–8 ч"


def test_repeated_field_is_kept_whole() -> None:
    """`program/M13/step-02.md` объявляет `Умение: J1` и `Умение: J2`.

    До решения 54 (2026-08-28) двумя строками объявлялся `M11/step-04.md`
    (G2 и G3); там они разделены, G3 уехал в `step-05.md`. Файл с двумя
    строками подряд в программе остался ровно один, и это он.
    """
    header = repo.step("M13", 2).header
    assert repo.step_skills(header) == ["J1", "J2"]


def test_every_one_of_46_skills_is_closed_by_a_step() -> None:
    """Та же связь, которую сторожит check_skill_ids() репозитория."""
    mapping = repo.skill_map()
    missing = [s["id"] for s in repo.skills() if s["id"] not in mapping]
    assert not missing, f"умения без единого шага: {missing}"
    assert len(repo.skills()) == 46  # 36 до решения 50, +10 новых умений


def test_skill_statement_comes_from_blueprint() -> None:
    c2 = next(s for s in repo.skills() if s["id"] == "C2")
    assert c2["group"] == "C"
    assert c2["statement"].startswith("Power Query")
    assert "Refresh" in c2["check"]


def test_skill_id_is_taken_from_the_head_of_the_field() -> None:
    """Пояснение шапки называет чужие ID — они не считаются умением шага."""
    header = repo.step("M3", 2).header
    assert "часть" in header["Умение"], "взят не тот шаг: пояснения в шапке нет"
    assert repo.step_skills(header) == ["A2"]


def test_prerequisites_are_parsed_in_all_five_shapes() -> None:
    def pre(module: str, number: int) -> dict:
        return repo.prerequisites(module, repo.step(module, number).header)

    assert pre("M4", 5)["steps"] == ["M4/step-04"]          # `step-04.md`
    assert "M0/step-03" in pre("M10", 1)["steps"] or pre("M10", 1)["modules"]
    assert "M5" in pre("M6", 1)["modules"]                   # «M5 целиком»
    career = pre("career", 1)
    assert career["modules"] == ["P1", "P2", "P3", "P4", "P5", "P6"], "диапазон P1–P6 не развёрнут"


def test_prerequisites_never_point_at_a_missing_file() -> None:
    for module in repo.modules():
        for st in repo.steps(module):
            for sid in repo.prerequisites(module, st.header)["steps"]:
                mod, _, name = sid.partition("/")
                assert (repo.PROGRAM / mod / f"{name}.md").is_file(), f"{st.step_id} → {sid}"


def test_review_block_is_read_from_blueprint_like_career() -> None:
    """Возвратный контроль — не модуль, но в дереве обязан быть (решение 49).

    Блок назван `review`, а не `M17`, по той же причине, что `career`:
    имя вида `M<номер>` включило бы его в проверки, написанные под модули.
    Цена этого отказа — что связь с blueprint держится текстом строки 6.1,
    а не кодом, и рвётся молча при переименовании. Тест сторожит связь.
    """
    catalog = repo.catalog()
    assert repo.REVIEW in catalog, "строка «Возвратный контроль» в 6.1 не найдена"
    assert catalog[repo.REVIEW]["hours"] == "29–35"  # вилка решения 54
    assert repo.REVIEW in repo.stage_order(), "блок не попал ни в один этап 6.2"

    numbers = [s.number for s in repo.steps(repo.REVIEW) if not s.is_declaration]
    assert numbers == [1, 2, 3, 4, 5], "пять точек R1–R5 не читаются как шаги"


def test_review_point_sections_are_parsed_without_step_numbering() -> None:
    """Разделы точки нумерованы одним числом, а не `1.1`…`1.8`."""
    text = repo.step(repo.REVIEW, 1).path.read_text(encoding="utf-8")
    parsed = repo.sections(text)
    assert parsed, "разделы возвратной точки не распарсились"
    assert any("Задания" in body.splitlines()[0] for body in parsed.values())
