import pandas as pd
import ahocorasick
import json
import logging
import pickle
import hashlib
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

    def _load_and_prepare_data(self, csv_path: str) -> dict:
        """
        Загружает данные из CSV, парсит псевдонимы и наполняет
        автомат Ахо-Корасик для быстрого поиска. Каждое ключевое слово
        (имя или псевдоним) будет указывать на полную информацию о сущности.

        Args:
            csv_path (str): Путь к CSV-файлу.

        Returns:
            dict: Словарь для быстрого доступа к данным сущности по ключевому слову.
        """
        logger.info(f"Загрузка и обработка реестра из файла: {csv_path}...")
        entity_map = {}

        try:
            # Используем pandas для удобного и надежного чтения CSV
            df = pd.read_csv(csv_path)
        except FileNotFoundError:
            logger.error(f"Файл {csv_path} не найден.")
            return entity_map

        for index, row in df.iterrows():
            # Сохраняем полную информацию об объекте в виде словаря
            entity_data = row.to_dict()
            
            # 1. Добавляем основное имя
            main_name = str(entity_data.get('name', '')).strip().lower()
            # Добавляем все слова, даже короткие. Фильтрация будет на следующих этапах.
            if main_name:
                # Ключ автомата - само слово, значение - кортеж (ключ, значение)
                # Это немного избыточно, но полезно для отладки
                self.automaton.add_word(main_name, (main_name, entity_data))
                entity_map[main_name] = entity_data

            # 2. Добавляем псевдонимы (хранятся в JSON-формате)
            try:
                # Убедимся, что aliases - это строка, прежде чем парсить JSON
                aliases_str = entity_data.get('aliases')
                if aliases_str and isinstance(aliases_str, str):
                    aliases = json.loads(aliases_str)
                    for alias in aliases:
                        alias_clean = str(alias).strip().lower()
                        if alias_clean:
                            self.automaton.add_word(alias_clean, (alias_clean, entity_data))
                            entity_map[alias_clean] = entity_data
            except (json.JSONDecodeError, TypeError):
                # Пропускаем, если псевдонимы некорректны или отсутствуют
                continue
        
        logger.info(f"Реестр успешно загружен. {len(entity_map)} ключевых слов добавлено в поисковый движок.")
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
        Возвращает путь к файлу кэша на основе имени CSV файла.

        Returns:
            Path: Путь к файлу кэша.
        """
        csv_name = Path(self.csv_path).stem
        return self.cache_dir / f"{csv_name}_automaton.pkl"

    def _get_hash_path(self) -> Path:
        """
        Возвращает путь к файлу с хэшем CSV.

        Returns:
            Path: Путь к файлу с хэшем.
        """
        csv_name = Path(self.csv_path).stem
        return self.cache_dir / f"{csv_name}_hash.txt"

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
            entity_id = entity_data['id']
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
                "entity_id": entity_data['id'],
                "entity_name": entity_data['name'],
                "entity_type": entity_data['type'],
                "found_alias": found_keyword,
                "context": context_snippet
            }
            candidates.append(candidate_info)
            
        return candidates