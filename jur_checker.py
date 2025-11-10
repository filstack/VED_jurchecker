import pandas as pd
import ahocorasick
import json
import logging
import pickle
import hashlib
import re
import time
import os
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

# Third-party libraries for alias expansion
import pymorphy3
from petrovich.main import Petrovich
from transliterate import translit

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Common Russian words for false positive detection (Observability feature)
COMMON_RUSSIAN_WORDS = {
    # Top 50 (ultra-common, definite false positives)
    "и", "в", "не", "на", "с", "что", "а", "как", "по", "это",
    "он", "она", "они", "к", "но", "за", "у", "от", "о", "из",
    "для", "же", "до", "так", "мы", "вы", "я", "все", "был", "была",
    "было", "были", "быть", "если", "есть", "когда", "где", "кто", "или",
    "этот", "этого", "этой", "этих", "может", "можно", "нет", "да", "только",

    # Top 51-100 (common, likely false positives)
    "такой", "такая", "такое", "свой", "своя", "свое", "год", "день", "время",
    "два", "три", "раз", "один", "одна", "одно", "много", "мало", "более",
    "самый", "очень", "еще", "уже", "там", "здесь", "сейчас", "тогда", "потом",
    "тут", "вот", "после", "через", "без", "под", "над", "между", "при",
    "про", "нас", "вас", "них", "ним", "том", "тем", "которые", "который",
    "стать", "сказать", "говорить", "видеть", "знать", "сделать", "хотеть",

    # Abbreviations & prepositions causing false positives
    "со", "во", "ко", "об", "со", "то", "бы", "ли", "ни", "же",
    "ст", "ук", "рф", "км", "дон", "тр", "вс", "гг", "мид",

    # Common words from entity names
    "группа", "центр", "фонд", "союз", "комитет", "движение", "партия",
    "издание", "агентство", "первый", "второй", "развитие", "поддержка",
    "альянс", "команда", "проект", "отдел", "факт", "выбор", "инициатива",
    "весь", "вся", "все", "ноги", "вот", "максим", "сергей", "александр",
    "николай", "союзники", "исключение", "великобритания", "настоящее",
    "время", "мемориал", "сейчас", "объединение",

    # Common words causing false positives (from 500-text analysis)
    "россия", "россии", "россию", "россией", "вместе", "процесс", "другой", "наши", "друг", "собеседник",
    "голосов", "городской", "научный", "выборы", "акцент", "граждане",

    # Common first names (high false positive risk)
    "андрей", "михаил", "антон", "олег", "татьяна", "роман", "илья",
    "виктор", "александра", "роберт", "дарья", "анастасия", "евгений",
    "дмитрий", "алексей", "иван", "петр", "павел", "юрий", "владимир",
    "игорь", "сергей", "николай", "максим",

    # Common patronymics (from hard test)
    "петрович", "александрович", "иванович", "сергеевич", "владимирович",
    "николаевич", "михайлович", "алексеевич", "дмитриевич", "андреевич",
    "евгеньевич", "олегович", "павлович", "юрьевич", "борисович",
    "анатольевич", "валерьевич", "викторович", "геннадьевич", "григорьевич",
    "петровна", "александровна", "ивановна", "сергеевна", "владимировна",
    "николаевна", "михайловна", "алексеевна", "дмитриевна", "андреевна",

    # Common adjectives causing false positives (single word)
    "свободная", "свободный", "открытый", "открытая", "новый", "новая",
    "старый", "старая", "белый", "белая", "черный", "черная", "красный",
    "красная", "синий", "синяя", "зеленый", "зеленая",

    # Generic organizational terms (too broad)
    "некоммерческая организация", "общественное объединение",
    "межрегиональное общественное объединение", "автономная некоммерческая организация",
    "общественная организация", "религиозная организация",

    # Country/region abbreviations
    "ссср", "сша", "фрг", "кнр", "рсфср", "усср", "бсср",

    # Three-letter words that are too generic
    "аль", "дон", "бен", "эль", "дер", "ван", "фон"
}

def is_dangerous_alias(alias: str) -> bool:
    """
    Проверяет, является ли алиас опасным (высокий риск ложных срабатываний).

    Опасные алиасы:
    - Очень короткие (< 3 символов)
    - Частые русские слова (предлоги, союзы, местоимения)
    - Однобуквенные аббревиатуры
    - Отчества (заканчиваются на -ович/-евич/-ич/-овна/-евна/-ична)
    - Слишком общие термины (> 2 слов)

    Args:
        alias: Нормализованный алиас для проверки

    Returns:
        True если алиас опасен, False если безопасен
    """
    alias_lower = alias.lower().strip()

    # Критерий 1: Слишком короткие (< 3 символов)
    if len(alias_lower) < 3:
        return True

    # Критерий 2: В списке частых слов
    if alias_lower in COMMON_RUSSIAN_WORDS:
        return True

    # Критерий 3: Только цифры или только точки
    if alias_lower.replace('.', '').replace(' ', '').isdigit():
        return True

    # Критерий 4: Отчества (паттерн)
    # Если однословный и заканчивается на типичное отчество
    if ' ' not in alias_lower:
        patronymic_endings = ('ович', 'евич', 'ич', 'овна', 'евна', 'ична', 'инична')
        if any(alias_lower.endswith(ending) for ending in patronymic_endings):
            # Но разрешаем фамилии типа "Рабинович", "Абрамович" (если они больше 8 символов)
            if len(alias_lower) <= 10:
                return True

    # Критерий 5: Очень длинные фразы (> 30 символов, вероятно слишком общие)
    if len(alias_lower) > 35:
        return True

    return False


class AliasExpander:
    """
    Generates searchable alias variants for entity names.

    Handles: name orders, initials, morphological forms, diminutives, transliterations.
    Implements: FR-001 through FR-021.

    Type-based strategies to reduce false positives:
    - террористы: exact match + abbreviations
    - экстремисты: full names + morphology
    - нежелательные: exact match (Cyrillic/Latin)
    - иноагенты: smart (person names get full expansion, organizations get strict)
    """

    def __init__(self, max_aliases: int = 100):
        """
        Initialize AliasExpander with morphological analyzer and name dictionaries.

        Args:
            max_aliases: Maximum aliases per entity (FR-013)
        """
        self.max_aliases = max_aliases
        self.logger = logging.getLogger(__name__)

        # Initialize pymorphy3 (heavy operation, do once)
        self.morph_analyzer = pymorphy3.MorphAnalyzer()

        # Build diminutive lookup from petrovich or hardcoded map
        self.diminutive_map = self._build_diminutive_map()

        self.logger.info(f"AliasExpander initialized with max_aliases={max_aliases}")

    def _build_diminutive_map(self) -> dict:
        """
        Build lookup table for first name → diminutives.

        Returns:
            Dictionary mapping formal names to diminutive lists
        """
        # Hardcoded common Russian diminutives (petrovich v2+ doesn't expose diminutives API easily)
        return {
            "александр": ["саша", "сашка", "шура", "саня"],
            "алексей": ["лёша", "леша", "алекс", "лёха", "алёша"],
            "владимир": ["вова", "вовка", "володя"],
            "дмитрий": ["дима", "митя", "димка"],
            "сергей": ["серёжа", "сережа", "серёга"],
            "андрей": ["андрюша", "дрюша"],
            "евгений": ["женя", "женька"],
            "михаил": ["миша", "мишка"],
            "николай": ["коля", "колька", "николаша"],
            "иван": ["ваня", "ванька", "ванечка"],
            "юрий": ["юра", "юрка"],
            "анна": ["аня", "анька", "нюра"],
            "мария": ["маша", "машка", "маруся"],
            "елена": ["лена", "ленка", "алёна"],
            "ольга": ["оля", "олька"],
            "татьяна": ["таня", "танька", "танюша"],
            "наталья": ["наташа", "наташка"],
            "ирина": ["ира", "ирка"],
            "екатерина": ["катя", "катюша", "катька"],
        }

    def is_person_name(self, name: str) -> bool:
        """
        Determine if entity name is a person (ФИО) or organization.

        Args:
            name: Entity name from CSV

        Returns:
            True if person name, False if organization
        """
        name_lower = name.lower()
        words = name.split()

        # 1. Organization keywords (clear indicators)
        ORG_KEYWORDS = {
            'фонд', 'организация', 'общество', 'проект', 'издание',
            'движение', 'союз', 'партнерство', 'центр', 'институт',
            'комитет', 'ано', 'оао', 'ооо', 'нко', 'автономная',
            'некоммерческая', 'благотворительный', 'региональн',
            'межрегиональн', 'общероссийск', 'объединение',
            'группа', 'компания', 'корпорация', 'ассоциация',
            'террористическ', 'экстремистск', 'сообщество'
        }

        if any(kw in name_lower for kw in ORG_KEYWORDS):
            return False  # Organization

        # 2. Person name indicators (patronymic endings)
        PATRONYMIC_ENDINGS = ('ович', 'евич', 'овна', 'евна', 'ичем', 'ична')

        for word in words:
            word_lower = word.lower()
            # Check patronymic (must be longer than 5 chars to avoid false matches)
            if len(word) > 5 and any(word_lower.endswith(end) for end in PATRONYMIC_ENDINGS):
                return True  # Person with patronymic

        # 3. Heuristics by word count
        if len(words) == 2:
            # "Захаров Андрей" or "Кедр.медиа" or "Исламское государство"?
            # Check if both words look like typical Russian surnames/names (capitalized, Cyrillic)
            # Exclude common organization patterns like "Исламское государство"
            common_org_words = {'государство', 'движение', 'сообщество', 'коммунистическ'}
            if any(org_word in name_lower for org_word in common_org_words):
                return False  # Organization pattern

            # If no dots/digits → likely person name
            if '.' not in name and not any(char.isdigit() for char in name):
                return True

        if len(words) == 3:
            # "Захаров Андрей Вячеславович" or "Михнов-Вайтенко Григорий Александрович"
            # Check for hyphenated surnames (common in person names)
            if any('-' in word for word in words[:2]):
                return True
            # Three words without org keywords → likely person
            return True

        # 4. Default: organization
        return False

    def parse_person_name(self, name: str) -> tuple:
        """
        Parse Russian full name into components.

        Args:
            name: Full name string

        Returns:
            (first_name, patronymic_or_none, last_name)
        """
        parts = name.strip().split()

        if len(parts) == 1:
            # Single word: treat as both first and last
            return (parts[0], None, parts[0])
        elif len(parts) == 2:
            # Two parts: first, last (no patronymic)
            return (parts[0], None, parts[1])
        elif len(parts) == 3:
            # Three parts: first, patronymic, last
            return (parts[0], parts[1], parts[2])
        else:
            # 4+ parts: join first parts, second-to-last as patronymic, last as surname
            return (" ".join(parts[:-2]), parts[-2], parts[-1])

    def expand_name_orders(
        self,
        first: str,
        patronymic: Optional[str],
        last: str
    ) -> list:
        """
        Generate name order variants.

        Args:
            first: First name
            patronymic: Patronymic (may be None)
            last: Last name

        Returns:
            List of name order variants (not normalized yet)
        """
        variants = []

        if patronymic:
            # Full name with patronymic (FR-004)
            variants.append(f"{first} {patronymic} {last}")
            # Without patronymic
            variants.append(f"{first} {last}")
            variants.append(f"{last} {first}")
        else:
            # Two-part name
            variants.append(f"{first} {last}")
            variants.append(f"{last} {first}")

        return variants

    def expand_initials(
        self,
        first: str,
        patronymic: Optional[str],
        last: str
    ) -> list:
        """
        Generate initial variants.

        Args:
            first: First name
            patronymic: Patronymic (may be None)
            last: Last name

        Returns:
            List of initial variants (not normalized yet)
        """
        variants = []

        # Extract first letter of first name (Unicode-safe)
        first_initial = first[0] if first else ""

        # Single initial variants (FR-002)
        variants.append(f"{first_initial}. {last}")
        variants.append(f"{last} {first_initial}.")

        # Double initial variants (FR-003, only if patronymic present)
        if patronymic:
            patronymic_initial = patronymic[0] if patronymic else ""
            variants.append(f"{first_initial}.{patronymic_initial}. {last}")
            variants.append(f"{last} {first_initial}.{patronymic_initial}.")

        return variants

    def expand_diminutives(self, first_name: str) -> list:
        """
        Get diminutive variants for a first name.

        Args:
            first_name: Russian first name

        Returns:
            List of diminutive forms (empty if none found)
        """
        normalized = first_name.lower()
        return self.diminutive_map.get(normalized, [])

    def expand_transliterations(self, variants: list) -> list:
        """
        Generate Latin transliterations for Cyrillic variants.

        Args:
            variants: List of Cyrillic name variants (already generated)

        Returns:
            List of transliterated (Latin) variants (lowercase)
        """
        transliterated = []

        for variant in variants:
            try:
                # Check if variant contains Cyrillic characters
                if not any('\u0400' <= c <= '\u04FF' for c in variant):
                    continue  # Skip non-Cyrillic text

                # Transliterate from Cyrillic to Latin (reversed=True)
                # Then manually simplify for phonetic friendliness
                transliterated_text = translit(variant, 'ru', reversed=True)

                # Apply phonetic simplifications (FR-007)
                # Remove apostrophes from transliteration
                transliterated_text = transliterated_text.replace("'", "")

                # Lowercase first for easier pattern matching
                transliterated_text = transliterated_text.lower()

                # Normalize common patterns to phonetic equivalents
                # j endings → y (Jurij → Yuriy, yj → y)
                transliterated_text = transliterated_text.replace("yj", "y")
                transliterated_text = transliterated_text.replace("ij", "iy")

                # е, ей → ey (Aleksej → Aleksey)
                transliterated_text = transliterated_text.replace("sej", "sey")

                # Ю → Yu not Ju (Jurij → Yuriy)
                transliterated_text = transliterated_text.replace("ju", "yu")

                transliterated.append(transliterated_text)
            except Exception:
                # Skip variants that fail transliteration (e.g., already Latin, mixed script)
                continue

        return transliterated

    def expand_morphological_forms(self, surname: str) -> list:
        """
        Generate all Russian case forms for a surname using pymorphy3.

        Args:
            surname: Last name to decline

        Returns:
            List of case forms (lowercase), or empty if parsing fails
        """
        parsed = self.morph_analyzer.parse(surname)

        if not parsed:
            return []

        # Get the first parse (most likely interpretation)
        word = parsed[0]

        # Check if this looks like a Russian surname (heuristic: check score/confidence)
        # If score is too low, it's likely a foreign name - return empty to trigger fallback
        if word.score < 0.1:
            return []

        # Check if result contains non-Cyrillic characters (foreign name)
        if not any('\u0400' <= c <= '\u04FF' for c in surname):
            return []

        # Generate all inflected forms (lexeme)
        forms = set()
        for form in word.lexeme:
            forms.add(form.word.lower())

        return list(forms)

    def apply_heuristic_fallback(self, full_name: str, morphology_results: list) -> list:
        """
        Apply manual suffix heuristics when morphological analysis fails.

        Args:
            full_name: Full name or surname that failed morphology
            morphology_results: Results from morphological analysis (empty if failed)

        Returns:
            List of morphology results if available, or heuristic forms if empty
        """
        # If morphology succeeded, return results unchanged
        if morphology_results:
            return morphology_results

        # Apply heuristic suffixes for foreign names
        surname = full_name.strip().lower()
        heuristic_forms = [
            surname,                # Base form
            surname + "ого",       # Genitive
            surname + "ому",       # Dative
            surname + "ым",        # Instrumental
            surname + "ом",        # Prepositional
        ]

        # Log warning (FR-018)
        self.logger.warning(f"Morphological fallback for surname='{full_name}'")

        return heuristic_forms

    def normalize_alias(self, alias: str) -> str:
        """
        Normalize alias for consistent automaton insertion.

        Args:
            alias: Raw alias variant

        Returns:
            Normalized alias (lowercase, ё→е, whitespace cleaned)
        """
        # Lowercase first (FR-017)
        normalized = alias.lower()

        # ё → е (FR-016)
        normalized = normalized.replace('ё', 'е')

        # Replace multiple whitespace with single space (FR-018)
        # Keep dots and dashes for initials like "а." and hyphenated names
        normalized = re.sub(r'\s+', ' ', normalized)

        # Trim leading/trailing whitespace
        normalized = normalized.strip()

        return normalized

    def prioritize_aliases(self, aliases: list) -> list:
        """
        Select top N aliases by priority when total exceeds max_aliases.

        Args:
            aliases: All generated aliases (may be >max_aliases)

        Returns:
            Top max_aliases by priority
        """
        # If under limit, return all
        if len(aliases) <= self.max_aliases:
            return aliases

        # Truncate to max (simple strategy: keep first N, which are already prioritized by generation order)
        return aliases[:self.max_aliases]

    def expand_all(self, entity_name: str, entity_type: str = "иноагенты") -> list:
        """
        Generate all alias variants for an entity using type-based strategies.

        Args:
            entity_name: Full entity name from CSV
            entity_type: Type of entity (террористы, экстремисты, нежелательные, иноагенты)

        Returns:
            List of normalized, deduplicated aliases (length ≤ max_aliases)
        """
        # ВАЖНО: Для ЛЮДЕЙ используем полную стратегию расширения имен, независимо от типа
        if self.is_person_name(entity_name):
            return self._expand_person_name(entity_name)

        # Type-based expansion strategies для организаций
        if "террорист" in entity_type.lower():
            return self._expand_terrorist(entity_name)
        elif "экстремист" in entity_type.lower():
            return self._expand_extremist(entity_name)
        elif "нежелательн" in entity_type.lower():
            return self._expand_undesirable(entity_name)
        else:  # иноагенты or default
            return self._expand_organization_name(entity_name)

    def expand_phrase_morphology(self, phrase: str, max_words: int = 3) -> list:
        """
        Склоняет словосочетание (прилагательное + существительное) с согласованием.

        Пример: "правый сектор" → ["правый сектор", "правого сектора", "правому сектору", ...]

        Args:
            phrase: Словосочетание для склонения (последние 1-3 слова)
            max_words: Максимум слов для склонения (по умолчанию 3)

        Returns:
            Список склоненных форм
        """
        words = phrase.split()
        if len(words) == 0:
            return []

        # Берем только последние max_words слов (чтобы не склонять длинные названия целиком)
        words = words[-max_words:]

        if len(words) == 1:
            # Одно слово — просто склоняем
            return self.expand_morphological_forms(words[0])

        # Несколько слов — склоняем с согласованием
        # Разбираем слова
        parsed_words = []
        for word in words:
            parsed = self.morph_analyzer.parse(word)
            if parsed:
                parsed_words.append(parsed[0])
            else:
                # Если слово не распознано, возвращаем пустой список
                return []

        if not parsed_words:
            return []

        # Определяем главное слово (обычно последнее — существительное)
        main_word = parsed_words[-1]

        # Генерируем формы
        variants = set()

        # Для каждого падежа главного слова
        for main_form in main_word.lexeme:
            # Согласуем остальные слова
            inflected_words = []

            # Согласуем зависимые слова (прилагательные)
            for i, parsed_word in enumerate(parsed_words[:-1]):
                # Пытаемся согласовать с главным словом
                # Берем род, число, падеж главного слова
                grammemes = {main_form.tag.case, main_form.tag.gender, main_form.tag.number}
                # Удаляем None
                grammemes = {g for g in grammemes if g}

                inflected = parsed_word.inflect(grammemes)
                if inflected:
                    inflected_words.append(inflected.word.lower())
                else:
                    # Если не удалось согласовать, берем исходное слово
                    inflected_words.append(words[i].lower())

            # Добавляем главное слово
            inflected_words.append(main_form.word.lower())

            # Собираем словосочетание
            variant = " ".join(inflected_words)
            variants.add(variant)

        return list(variants)

    def _expand_terrorist(self, entity_name: str) -> list:
        """
        Strategy for terrorists: exact match + known abbreviations + morphology for key terms.
        Добавлено склонение для последних 1-2 слов названия.
        """
        normalized = self.normalize_alias(entity_name)
        aliases = [normalized]

        # Add morphological forms for key phrase (last 1-2 words)
        words = entity_name.split()
        if len(words) >= 2:
            # Склоняем последние 2 слова (например, "Исламское государство")
            key_phrase = " ".join(words[-2:])
            morpho_forms = self.expand_phrase_morphology(key_phrase, max_words=2)

            # Добавляем полные и короткие формы
            prefix = " ".join(words[:-2]) if len(words) > 2 else ""
            for form in morpho_forms:
                if prefix:
                    aliases.append(self.normalize_alias(f"{prefix} {form}"))
                # Короткая форма (только ключевая фраза)
                aliases.append(self.normalize_alias(form))
        elif len(words) == 1:
            # Одно слово — склоняем (например, "Талибан")
            morpho_forms = self.expand_morphological_forms(words[0])
            aliases.extend([self.normalize_alias(f) for f in morpho_forms])

        # Add common terrorist abbreviations if present
        if "исламское государство" in normalized or "игил" in normalized:
            aliases.extend(["игил", "иг", "isis", "isil", "даиш"])
            # Склоняем аббревиатуры
            aliases.extend(["игила", "игилу", "игилом", "игиле"])
        if "аль-каида" in normalized or "аль каида" in normalized:
            aliases.extend(["аль-каида", "аль каида", "al-qaeda", "al qaeda"])
            # Склоняем
            aliases.extend(["аль-каиды", "аль-каиде", "аль-каидой", "аль-каиде"])
        if "талибан" in normalized:
            aliases.extend(["талибан", "taliban"])
            # Формы уже добавлены выше через морфологию

        return list(set(aliases))

    def _expand_extremist(self, entity_name: str) -> list:
        """
        Strategy for extremists: full name + key phrase morphology with adjective agreement.
        Example: "Украинская организация Правый сектор" →
                 [..., "украинская организация правого сектора", "правого сектора", ...]
        """
        normalized = self.normalize_alias(entity_name)
        aliases = [normalized]

        # Add morphological forms of the last 2-3 words (key phrase) with adjective agreement
        words = entity_name.split()
        if len(words) >= 2:
            # Склоняем последние 2-3 слова как словосочетание (с согласованием прилагательных)
            # Пример: "Правый сектор" → "правого сектора", "правому сектору"
            key_phrase = " ".join(words[-2:])  # Последние 2 слова
            morpho_forms = self.expand_phrase_morphology(key_phrase, max_words=2)

            # Добавляем ДВА набора форм:
            # 1. Полное название с вариантами склонения (с префиксом)
            # 2. Только ключевая фраза (БЕЗ префикса) — для поиска коротких упоминаний
            prefix = " ".join(words[:-2]) if len(words) > 2 else ""
            for form in morpho_forms:
                # Полная форма (если есть префикс)
                if prefix:
                    variant_full = f"{prefix} {form}"
                    aliases.append(self.normalize_alias(variant_full))

                # Короткая форма (только ключевая фраза) — ВСЕГДА добавляем
                aliases.append(self.normalize_alias(form))
        elif len(words) == 1:
            # Одно слово — просто склоняем
            morpho_forms = self.expand_morphological_forms(words[0])
            aliases.extend([self.normalize_alias(f) for f in morpho_forms])

        return list(set(aliases))

    def _expand_undesirable(self, entity_name: str) -> list:
        """
        Strategy for undesirable orgs: exact match only (Cyrillic + Latin variants).
        Many have Latin names, just normalize.
        """
        normalized = self.normalize_alias(entity_name)
        aliases = [normalized]

        # If contains parentheses with translation, extract both
        # Example: "Greenpeace International (Гринпис Интернешнл)"
        if '(' in entity_name and ')' in entity_name:
            # Extract text in parentheses
            import re
            match = re.search(r'\(([^)]+)\)', entity_name)
            if match:
                alternate = match.group(1)
                aliases.append(self.normalize_alias(alternate))

        return list(set(aliases))

    def _expand_foreign_agent(self, entity_name: str) -> list:
        """
        Strategy for foreign agents: smart detection (person vs organization).
        - Person names: full expansion (morphology, initials, diminutives, transliteration)
        - Organizations: strict (full name only, no single-word extraction)
        """
        if self.is_person_name(entity_name):
            # Full expansion for person names
            return self._expand_person_name(entity_name)
        else:
            # Strict expansion for organizations (just full name + morphology of full phrase)
            return self._expand_organization_name(entity_name)

    def _expand_person_name(self, entity_name: str) -> list:
        """
        Full alias expansion for person names (ФИО).

        CRITICAL FIX: НЕ генерируем склонения для отдельных частей имени.
        Генерируем только склонения ПОЛНЫХ имен (Имя Фамилия, Имя Отчество Фамилия).
        """
        all_variants = []

        # Parse name
        first, patronymic, last = self.parse_person_name(entity_name)

        # 1. Name orders (FR-001, FR-004)
        name_order_variants = self.expand_name_orders(first, patronymic, last)
        all_variants.extend(name_order_variants)

        # 2. Initials (FR-002, FR-003)
        all_variants.extend(self.expand_initials(first, patronymic, last))

        # 3. Morphological forms for FULL NAME ONLY (не для отдельных слов!)
        # Склоняем только полные варианты имен (2-3 слова), не фамилию/отчество отдельно
        for name_variant in name_order_variants:
            words = name_variant.split()
            if len(words) >= 2:
                # Склоняем словосочетание (Имя Фамилия или Имя Отчество Фамилия)
                morpho_forms = self.expand_phrase_morphology(name_variant, max_words=3)
                all_variants.extend(morpho_forms)

        # 4. Diminutives for first name (FR-005)
        # ТОЛЬКО в комбинации с фамилией, не отдельно
        diminutives = self.expand_diminutives(first)
        for dim in diminutives:
            if patronymic:
                all_variants.append(f"{dim} {patronymic} {last}")
            all_variants.append(f"{dim} {last}")

        # 5. Transliterations (FR-006, FR-007)
        # Транслитерируем только полные имена, не отдельные слова
        transliterations = self.expand_transliterations(all_variants)
        all_variants.extend(transliterations)

        # 6. Normalize all variants
        normalized_variants = [self.normalize_alias(v) for v in all_variants]

        # 7. Filter out single words (except initials with dots)
        # ЭТО КРИТИЧНО: убираем все однословные алиасы (николаевна, николаевну и т.д.)
        filtered_variants = []
        for v in normalized_variants:
            # Оставляем только:
            # - Инициалы с точками (а. навальный)
            # - Многословные имена (2+ слов)
            if '.' in v:
                filtered_variants.append(v)
            elif len(v.split()) >= 2:
                filtered_variants.append(v)
            # Однословные алиасы УДАЛЯЕМ полностью

        # 8. Deduplicate
        unique_variants = list(set(filtered_variants))

        # 9. Prioritize and truncate
        final_aliases = self.prioritize_aliases(unique_variants)

        return final_aliases

    def _expand_organization_name(self, entity_name: str) -> list:
        """
        Strict expansion for organizations: only full name (no single words).
        Reduces false positives on common words like "проект", "центр", etc.
        """
        normalized = self.normalize_alias(entity_name)
        return [normalized]

class JurChecker:
    """
    Сервис для автоматической проверки текстов на упоминания лиц и организаций
    из реестров РФ. Эта версия выполняет быстрый первичный поиск всех
    потенциальных кандидатов для дальнейшей "умной" фильтрации.
    """

    def __init__(self, csv_path: str, cache_dir: str = ".cache"):
        """
        Инициализирует чекер, загружая и подготавливая данные из CSV.
        Создает и финализирует автомат Ахо-Корасик для поиска.
        Использует кэширование для ускорения повторных запусков.

        Args:
            csv_path (str): Путь к CSV-файлу с реестром.
            cache_dir (str): Директория для хранения кэша автомата.
        """
        self.csv_path = csv_path
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        # Попытка загрузить из кэша
        cache_loaded = self._load_from_cache()

        if not cache_loaded:
            # Если кэш не загружен, строим автомат с нуля
            self.automaton = ahocorasick.Automaton()
            self.entity_map = self._load_and_prepare_data(csv_path)
            # Финализируем автомат, чтобы он был готов к поиску
            self.automaton.make_automaton()
            # Сохраняем в кэш
            self._save_to_cache()
            logger.info("Сервис ЮРЧЕКЕР: поисковый движок построен с нуля и готов к работе.")
        else:
            logger.info("Сервис ЮРЧЕКЕР: поисковый движок загружен из кэша и готов к работе.")

        # T014: Cleanup old telemetry logs on startup
        self._cleanup_old_telemetry_logs()

    def _load_and_prepare_data(self, csv_path: str) -> dict:
        """
        Загружает данные из CSV, генерирует расширенные алиасы и наполняет
        автомат Ахо-Корасик для быстрого поиска. Каждое ключевое слово
        (имя или псевдоним) будет указывать на полную информацию о сущности.

        MODIFIED: Now generates expanded aliases using AliasExpander.

        Args:
            csv_path (str): Путь к CSV-файлу.

        Returns:
            dict: Словарь для быстрого доступа к данным сущности по ключевому слову.
        """
        logger.info(f"Загрузка и обработка реестра из файла: {csv_path}...")

        # Initialize AliasExpander once before loop (heavy operation)
        expander = AliasExpander(max_aliases=100)

        # Start build timer for performance tracking (FR-021)
        build_start_time = time.time()

        entity_map = {}

        try:
            # Используем pandas для удобного и надежного чтения CSV
            df = pd.read_csv(csv_path)
        except FileNotFoundError:
            logger.error(f"Файл {csv_path} не найден.")
            return entity_map

        total_aliases_count = 0
        alias_to_entities = {}  # Track collisions: alias -> set of entity_ids

        for index, row in df.iterrows():
            # Сохраняем полную информацию об объекте в виде словаря
            entity_data = row.to_dict()
            entity_id = entity_data.get('id', f'unknown_{index}')
            # Поддержка обоих форматов CSV: 'entity_name' или 'name'
            entity_name = str(entity_data.get('entity_name', entity_data.get('name', ''))).strip()
            entity_type = str(entity_data.get('type', 'иноагенты')).strip()

            if not entity_name:
                continue  # Skip empty names

            # Check if CSV has pre-generated aliases column
            if 'aliases' in entity_data and entity_data['aliases']:
                try:
                    # Use pre-generated aliases from CSV (JSON format)
                    aliases_raw = json.loads(entity_data['aliases'])
                    # Normalize and filter dangerous aliases
                    aliases_normalized = [expander.normalize_alias(a) for a in aliases_raw if a]
                    aliases_before = len(aliases_normalized)
                    aliases = [a for a in aliases_normalized if not is_dangerous_alias(a)]
                    filtered_count = aliases_before - len(aliases)

                    if filtered_count > 0:
                        logger.debug(f"Filtered {filtered_count} dangerous aliases for entity_id={entity_id}")

                    logger.debug(f"Using {len(aliases)} safe pre-generated aliases for entity_id={entity_id}")
                except (json.JSONDecodeError, TypeError, ValueError) as e:
                    # Fallback: generate aliases if JSON parsing fails
                    logger.warning(f"Failed to parse aliases for entity_id={entity_id}: {e}. Generating aliases.")
                    aliases = expander.expand_all(entity_name, entity_type)
            else:
                # Generate expanded aliases using AliasExpander with type-based strategy
                logger.debug(f"No pre-generated aliases found for entity_id={entity_id}. Generating aliases.")
                aliases = expander.expand_all(entity_name, entity_type)

            # T007: Calculate alias quality metrics
            single_word_aliases = [a for a in aliases if ' ' not in a and '.' not in a]
            single_word_count = len(single_word_aliases)
            is_person = expander.is_person_name(entity_name)

            # Track collisions (will be analyzed after loop)
            for alias in aliases:
                alias_to_entities.setdefault(alias, set()).add(entity_id)

            # Add all aliases to automaton
            for alias in aliases:
                self.automaton.add_word(alias, (alias, entity_data))
                entity_map[alias] = entity_data

            total_aliases_count += len(aliases)

            # T007: Log structured alias quality metrics (key=value format)
            logger.info(
                f"ALIAS_METRICS: entity_id={entity_id} entity_type={entity_type} "
                f"alias_count={len(aliases)} single_word_count={single_word_count} "
                f"is_person={is_person} collision_count=0"
            )

            # T008: Warn about single-word aliases from person names
            if is_person and single_word_count > 0:
                for alias in single_word_aliases:
                    logger.warning(
                        f"SINGLE_WORD_ALIAS: entity_id={entity_id} entity_name='{entity_name}' "
                        f"alias='{alias}' risk=high"
                    )

            # T009: Warn about aliases matching common Russian words
            for alias in aliases:
                if alias in COMMON_RUSSIAN_WORDS:
                    logger.warning(
                        f"COMMON_WORD_ALIAS: entity_id={entity_id} entity_name='{entity_name}' "
                        f"alias='{alias}' risk=very_high"
                    )

        # T010: Collision detection and warnings (after loop completes)
        for alias, entity_ids in alias_to_entities.items():
            if len(entity_ids) > 5:
                risk = "high" if len(entity_ids) > 10 else "medium"
                sample = list(entity_ids)[:10]
                logger.warning(
                    f"ALIAS_COLLISION: alias='{alias}' entity_count={len(entity_ids)} "
                    f"risk={risk} sample_ids={sample}"
                )

        # Calculate build time
        build_time = time.time() - build_start_time

        # Log total dictionary size and build time (FR-019)
        logger.info(
            f"Реестр успешно загружен. {total_aliases_count} ключевых слов добавлено в поисковый движок. "
            f"Build time: {build_time:.2f} seconds"
        )

        # Warn if approaching 2-minute limit (FR-021)
        if build_time > 90:
            logger.warning(
                f"Dictionary build time ({build_time:.2f}s) approaching 2-minute limit (120s)"
            )

        return entity_map

    def _get_csv_hash(self) -> str:
        """
        Вычисляет MD5 хэш CSV-файла для определения актуальности кэша.

        Returns:
            str: MD5 хэш содержимого файла.
        """
        hash_md5 = hashlib.md5()
        try:
            with open(self.csv_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except FileNotFoundError:
            logger.error(f"Не удалось вычислить хэш: файл {self.csv_path} не найден.")
            return ""

    def _get_cache_path(self) -> Path:
        """
        Возвращает путь к файлу кэша на основе имени CSV файла и режима строгости.

        Returns:
            Path: Путь к файлу кэша (mode-specific).
        """
        csv_name = Path(self.csv_path).stem
        mode = os.getenv("ALIAS_STRICTNESS", "strict")
        return self.cache_dir / f"{csv_name}_{mode}_automaton.pkl"

    def _get_hash_path(self) -> Path:
        """
        Возвращает путь к файлу с хэшем CSV (mode-specific).

        Returns:
            Path: Путь к файлу с хэшем.
        """
        csv_name = Path(self.csv_path).stem
        mode = os.getenv("ALIAS_STRICTNESS", "strict")
        return self.cache_dir / f"{csv_name}_{mode}_hash.txt"

    def _load_from_cache(self) -> bool:
        """
        Загружает автомат и entity_map из кэша, если кэш актуален.

        Returns:
            bool: True, если кэш успешно загружен; False в противном случае.
        """
        cache_path = self._get_cache_path()
        hash_path = self._get_hash_path()

        # Проверяем наличие файлов кэша
        if not cache_path.exists() or not hash_path.exists():
            logger.info("Кэш не найден, будет выполнена полная загрузка.")
            return False

        # Проверяем актуальность кэша по хэшу
        try:
            with open(hash_path, "r") as f:
                cached_hash = f.read().strip()

            current_hash = self._get_csv_hash()

            if cached_hash != current_hash:
                logger.info("Кэш устарел (CSV изменился), будет выполнена полная загрузка.")
                return False

            # Загружаем кэш
            with open(cache_path, "rb") as f:
                cache_data = pickle.load(f)
                self.automaton = cache_data["automaton"]
                self.entity_map = cache_data["entity_map"]

            logger.info(f"Кэш успешно загружен из {cache_path}")
            return True

        except Exception as e:
            logger.warning(f"Ошибка при загрузке кэша: {e}. Будет выполнена полная загрузка.")
            return False

    def _save_to_cache(self):
        """
        Сохраняет автомат и entity_map в кэш для ускорения последующих запусков.
        """
        cache_path = self._get_cache_path()
        hash_path = self._get_hash_path()

        try:
            # Сохраняем автомат и entity_map
            cache_data = {
                "automaton": self.automaton,
                "entity_map": self.entity_map
            }
            with open(cache_path, "wb") as f:
                pickle.dump(cache_data, f)

            # Сохраняем хэш CSV
            current_hash = self._get_csv_hash()
            with open(hash_path, "w") as f:
                f.write(current_hash)

            logger.info(f"Кэш успешно сохранён в {cache_path}")

        except Exception as e:
            logger.error(f"Не удалось сохранить кэш: {e}")

    def _get_telemetry_log_path(self) -> Path:
        """
        Returns path to today's telemetry log file.

        Returns:
            Path: Path to .logs/matches-{YYYY-MM-DD}.jsonl
        """
        logs_dir = Path(".logs")
        today = datetime.now().strftime("%Y-%m-%d")
        return logs_dir / f"matches-{today}.jsonl"

    def _cleanup_old_telemetry_logs(self):
        """
        Deletes telemetry log files older than LOG_RETENTION_DAYS.
        Runs once on startup to keep disk usage bounded.
        """
        logs_dir = Path(".logs")
        if not logs_dir.exists():
            return

        retention_days = int(os.getenv("LOG_RETENTION_DAYS", "30"))
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        deleted_count = 0
        for log_file in logs_dir.glob("matches-*.jsonl"):
            try:
                # Extract date from filename: matches-2025-01-15.jsonl
                date_str = log_file.stem.replace("matches-", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d")

                if file_date < cutoff_date:
                    log_file.unlink()
                    deleted_count += 1
            except (ValueError, OSError) as e:
                # Skip files that don't match expected format or can't be deleted
                logger.warning(f"Could not process telemetry log {log_file}: {e}")

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old telemetry log files (retention: {retention_days} days)")

    def _normalize_text(self, text: str) -> str:
        """
        Приводит текст к единому виду для корректного поиска:
        нижний регистр и замена 'ё' на 'е'.

        Args:
            text (str): Входной текст.

        Returns:
            str: Нормализованный текст.
        """
        return text.lower().replace('ё', 'е')

    def find_raw_candidates(self, text: str) -> list:
        """
        Находит "сырые" совпадения, проверяет границы слов и возвращает
        кандидатов с контекстом для дальнейшей верификации через ИИ.
        
        Args:
            text (str): Текст для проверки.

        Returns:
            list: Список словарей, где каждый словарь - это "кандидат" на упоминание.
        """
        normalized_text = self._normalize_text(text)
        
        # Находим все вхождения ключевых слов за один проход
        # item = (end_index, (keyword, entity_data))
        findings = list(self.automaton.iter(normalized_text))
        
        candidates = []
        processed_ids = set() # Чтобы не возвращать дубликаты одной и той же сущности

        for end_index, (found_keyword, entity_data) in findings:
            entity_id = entity_data.get('id', entity_data.get('entity_name', 'unknown'))
            if entity_id in processed_ids:
                continue

            # Проверка, что найденное слово является целым словом, а не частью другого
            start_index = end_index - len(found_keyword) + 1
            # Слева: либо начало строки, либо не буквенно-цифровой символ
            is_left_boundary = (start_index == 0) or (not normalized_text[start_index - 1].isalnum())
            # Справа: либо конец строки, либо не буквенно-цифровой символ
            is_right_boundary = (end_index + 1 == len(normalized_text)) or (not normalized_text[end_index + 1].isalnum())

            if not (is_left_boundary and is_right_boundary):
                continue # Пропускаем, если это часть другого слова (например, "мо" в "молоко")

            processed_ids.add(entity_id)

            # Вырезаем контекст из ОРИГИНАЛЬНОГО (не нормализованного) текста
            context_start = max(0, start_index - 150)
            context_end = min(len(text), end_index + 151)
            context_snippet = text[context_start:context_end]

            candidate_info = {
                "entity_id": entity_id,
                "entity_name": entity_data.get('entity_name', entity_data.get('name', 'unknown')),
                "entity_type": entity_data.get('entity_type', entity_data.get('type', 'unknown')),
                "found_alias": found_keyword,
                "context": context_snippet
            }
            candidates.append(candidate_info)

            # T013: Telemetry logging (if enabled)
            if os.getenv("ENABLE_MATCH_LOGGING", "false").lower() == "true":
                try:
                    log_path = self._get_telemetry_log_path()

                    # Truncate context to 300 chars for privacy
                    truncated_context = context_snippet[:300]

                    telemetry_entry = {
                        "timestamp": datetime.now().isoformat() + "Z",
                        "alias": found_keyword,
                        "entity_id": entity_id,
                        "entity_name": candidate_info["entity_name"],
                        "entity_type": candidate_info["entity_type"],
                        "context": truncated_context,
                        "request_id": None
                    }

                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(telemetry_entry, ensure_ascii=False) + "\n")
                except Exception as e:
                    # Never let telemetry errors break the main flow
                    logger.warning(f"Failed to write telemetry log: {e}")

        return candidates