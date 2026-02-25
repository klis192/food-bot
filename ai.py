import os
import anthropic


def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def suggest_dishes_from_available(products: list[str]) -> str:
    """Return 5 dishes that can be cooked with the given products."""
    product_list = ", ".join(products)
    prompt = f"""У меня есть следующие продукты: {product_list}

Предложи ровно 5 блюд, которые можно приготовить из этих продуктов (без необходимости докупать что-либо ещё).

Для каждого блюда укажи:
1. Название блюда
2. Какие из моих продуктов используются
3. Краткий рецепт (2-3 предложения)

Отвечай на русском языке."""

    client = get_client()
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def suggest_dishes_to_buy(products: list[str]) -> str:
    """Return 5 dishes that require buying 1-3 additional ingredients."""
    product_list = ", ".join(products)
    prompt = f"""У меня есть следующие продукты: {product_list}

Предложи ровно 5 блюд, для которых нужно докупить всего 1-3 ингредиента.

Для каждого блюда укажи:
1. Название блюда
2. Какие из моих продуктов используются
3. Что нужно докупить (1-3 ингредиента)
4. Краткий рецепт (2-3 предложения)

Отвечай на русском языке."""

    client = get_client()
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text
