"""
Тесты для проекта food-bot (klis192/food-bot).
Покрывают: storage.py, ai.py, окружение.
"""

import os
import sys
import sqlite3
import tempfile
import pytest

# Добавляем корень проекта в путь импорта
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# ---------------------------------------------------------------------------
# storage.py — работа с SQLite базой данных
# ---------------------------------------------------------------------------

import storage


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Каждый тест получает чистую временную БД."""
    db_file = str(tmp_path / "test_food_bot.db")
    monkeypatch.setattr(storage, "DB_PATH", db_file)
    storage.init_db()
    yield
    # Файл удаляется автоматически вместе с tmp_path


class TestInitDb:
    def test_creates_products_table(self):
        """init_db() создаёт таблицу products."""
        conn = storage.get_connection()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='products'"
        ).fetchall()
        conn.close()
        assert len(tables) == 1

    def test_idempotent(self):
        """Повторный вызов init_db() не вызывает ошибок."""
        storage.init_db()  # второй вызов
        storage.init_db()  # третий вызов


class TestAddProducts:
    def test_add_single_product(self):
        storage.add_products(user_id=1, products=["яблоко"])
        assert storage.get_products(1) == ["яблоко"]

    def test_add_multiple_products(self):
        storage.add_products(user_id=1, products=["молоко", "яйца", "мука"])
        result = storage.get_products(1)
        assert set(result) == {"молоко", "яйца", "мука"}

    def test_strips_whitespace(self):
        """Пробелы вокруг названий продуктов должны обрезаться."""
        storage.add_products(user_id=1, products=["  картофель  ", " лук"])
        result = storage.get_products(1)
        assert "картофель" in result
        assert "лук" in result

    def test_ignores_empty_strings(self):
        """Пустые строки не сохраняются."""
        storage.add_products(user_id=1, products=["", "   ", "томат"])
        result = storage.get_products(1)
        assert result == ["томат"]

    def test_users_are_isolated(self):
        """Продукты разных пользователей не смешиваются."""
        storage.add_products(user_id=1, products=["хлеб"])
        storage.add_products(user_id=2, products=["масло"])
        assert storage.get_products(1) == ["хлеб"]
        assert storage.get_products(2) == ["масло"]


class TestGetProducts:
    def test_returns_empty_list_for_new_user(self):
        assert storage.get_products(999) == []

    def test_returns_list_type(self):
        storage.add_products(user_id=1, products=["сыр"])
        result = storage.get_products(1)
        assert isinstance(result, list)

    def test_preserves_order(self):
        """Продукты возвращаются в порядке добавления."""
        products = ["молоко", "яйца", "масло"]
        storage.add_products(user_id=1, products=products)
        result = storage.get_products(1)
        assert result == products


class TestClearProducts:
    def test_clears_user_products(self):
        storage.add_products(user_id=1, products=["хлеб", "молоко"])
        storage.clear_products(user_id=1)
        assert storage.get_products(1) == []

    def test_clear_only_affects_target_user(self):
        """clear_products удаляет только продукты нужного пользователя."""
        storage.add_products(user_id=1, products=["хлеб"])
        storage.add_products(user_id=2, products=["молоко"])
        storage.clear_products(user_id=1)
        assert storage.get_products(1) == []
        assert storage.get_products(2) == ["молоко"]

    def test_clear_empty_is_safe(self):
        """Очистка пустого списка не вызывает ошибок."""
        storage.clear_products(user_id=999)


# ---------------------------------------------------------------------------
# ai.py — функции генерации блюд (мокируем Anthropic API)
# ---------------------------------------------------------------------------

import ai
from unittest.mock import patch, MagicMock


def make_mock_response(text: str):
    """Создаёт имитацию ответа Anthropic API."""
    mock_content = MagicMock()
    mock_content.text = text
    mock_response = MagicMock()
    mock_response.content = [mock_content]
    return mock_response


class TestSuggestDishesFromAvailable:
    def test_returns_string(self):
        with patch.object(ai, "get_client") as mock_client:
            mock_client.return_value.messages.create.return_value = make_mock_response(
                "1. Яичница\n2. Омлет\n3. Глазунья\n4. Болтунья\n5. Яйца пашот"
            )
            result = ai.suggest_dishes_from_available(["яйца", "масло"])
        assert isinstance(result, str)
        assert len(result) > 0

    def test_products_passed_to_prompt(self):
        """Список продуктов должен попасть в запрос к API."""
        products = ["курица", "рис", "лук"]
        captured_prompt = {}

        def fake_create(**kwargs):
            captured_prompt["messages"] = kwargs.get("messages", [])
            return make_mock_response("блюда...")

        with patch.object(ai, "get_client") as mock_client:
            mock_client.return_value.messages.create.side_effect = fake_create
            ai.suggest_dishes_from_available(products)

        prompt_text = captured_prompt["messages"][0]["content"]
        for product in products:
            assert product in prompt_text

    def test_empty_product_list(self):
        """Функция не падает при пустом списке продуктов."""
        with patch.object(ai, "get_client") as mock_client:
            mock_client.return_value.messages.create.return_value = make_mock_response(
                "Нет продуктов"
            )
            result = ai.suggest_dishes_from_available([])
        assert isinstance(result, str)


class TestSuggestDishesToBuy:
    def test_returns_string(self):
        with patch.object(ai, "get_client") as mock_client:
            mock_client.return_value.messages.create.return_value = make_mock_response(
                "1. Борщ — докупить: свёкла"
            )
            result = ai.suggest_dishes_to_buy(["картофель", "капуста"])
        assert isinstance(result, str)
        assert len(result) > 0

    def test_products_passed_to_prompt(self):
        products = ["макароны", "томат"]
        captured_prompt = {}

        def fake_create(**kwargs):
            captured_prompt["messages"] = kwargs.get("messages", [])
            return make_mock_response("блюда...")

        with patch.object(ai, "get_client") as mock_client:
            mock_client.return_value.messages.create.side_effect = fake_create
            ai.suggest_dishes_to_buy(products)

        prompt_text = captured_prompt["messages"][0]["content"]
        for product in products:
            assert product in prompt_text


class TestGetClient:
    def test_requires_api_key(self):
        """get_client() бросает KeyError, если ANTHROPIC_API_KEY не задан."""
        env_without_key = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        with patch.dict(os.environ, env_without_key, clear=True):
            with pytest.raises((KeyError, Exception)):
                ai.get_client()


# ---------------------------------------------------------------------------
# Окружение и файлы проекта
# ---------------------------------------------------------------------------

class TestProjectFiles:
    def test_requirements_txt_exists(self):
        assert os.path.isfile("requirements.txt")

    def test_env_example_exists(self):
        """.env.example должен быть в репо."""
        assert os.path.isfile(".env.example")

    def test_gitignore_ignores_env(self):
        """.gitignore должен исключать .env с секретами."""
        with open(".gitignore") as f:
            content = f.read()
        assert ".env" in content

    def test_no_real_env_file_committed(self):
        """.env с реальными секретами не должен лежать в репо (только .env.example)."""
        # Наличие .env не обязательно означает утечку, но сигнализирует о риске
        # Проверяем, что если .env есть — он не содержит реального токена API
        if os.path.isfile(".env"):
            with open(".env") as f:
                content = f.read()
            # Реальные ключи Anthropic начинаются с sk-ant-
            assert "sk-ant-" not in content, ".env содержит реальный ANTHROPIC_API_KEY!"
