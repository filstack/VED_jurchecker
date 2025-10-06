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
    "стать", "сказать", "говорить", "видеть", "знать", "сделать", "хотеть"
}


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
        # Type-based expansion strategies
        if entity_type == "террористы":
            return self._expand_terrorist(entity_name)
        elif entity_type == "экстремисты":
            return self._expand_extremist(entity_name)
        elif entity_type == "нежелательные":
            return self._expand_undesirable(entity_name)
        else:  # иноагенты or default
            return self._expand_foreign_agent(entity_name)

    def _expand_terrorist(self, entity_name: str) -> list:
        """
        Strategy for terrorists: exact match + known abbreviations only.
        No morphology to avoid false positives.
        """
        normalized = self.normalize_alias(entity_name)
        aliases = [normalized]

        # Add common terrorist abbreviations if present
        if "исламское государство" in normalized or "игил" in normalized:
            aliases.extend(["игил", "иг", "isis", "isil", "даиш"])
        if "аль-каида" in normalized or "аль каида" in normalized:
            aliases.extend(["аль-каида", "аль каида", "al-qaeda", "al qaeda"])
        if "талибан" in normalized:
            aliases.extend(["талибан", "taliban"])

        return list(set(aliases))

    def _expand_extremist(self, entity_name: str) -> list:
        """
        Strategy for extremists: full name + morphology only.
        No single-word extraction to reduce false positives.
        """
        normalized = self.normalize_alias(entity_name)
        aliases = [normalized]

        # Add morphological forms of the full name (if Russian)
        words = entity_name.split()
        if len(words) > 0:
            # Get morphology for last significant word (usually the key term)
            last_word = words[-1]
            morpho_forms = self.expand_morphological_forms(last_word)

            # Reconstruct full phrases with morphological variants
            for form in morpho_forms:
                # Replace last word with morphological form
                variant_words = words[:-1] + [form]
                variant = " ".join(variant_words)
                aliases.append(self.normalize_alias(variant))

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
        """Full alias expansion for person names (original logic)."""
        all_variants = []

        # Parse name
        first, patronymic, last = self.parse_person_name(entity_name)

        # 1. Name orders (FR-001, FR-004)
        all_variants.extend(self.expand_name_orders(first, patronymic, last))

        # 2. Initials (FR-002, FR-003)
        all_variants.extend(self.expand_initials(first, patronymic, last))

        # 3. Morphological forms for surname (FR-011, FR-012)
        morphological_forms = self.expand_morphological_forms(last)

        # Apply heuristic fallback if morphology failed (FR-008, FR-009, FR-010)
        morphological_forms = self.apply_heuristic_fallback(last, morphological_forms)

        all_variants.extend(morphological_forms)

        # 4. Diminutives for first name (FR-005)
        diminutives = self.expand_diminutives(first)
        all_variants.extend(diminutives)

        # 5. Transliterations (FR-006, FR-007)
        transliterations = self.expand_transliterations(all_variants)
        all_variants.extend(transliterations)

        # 6. Normalize all variants
        normalized_variants = [self.normalize_alias(v) for v in all_variants]

        # 7. Filter out very short aliases (< 4 symbols) to reduce false positives
        # Exception: keep initials (contain dots)
        filtered_variants = [
            v for v in normalized_variants
            if len(v) >= 4 or '.' in v
        ]

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

            # Generate expanded aliases using AliasExpander with type-based strategy
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