import pytest
import pytest_asyncio

from server import create_app


@pytest_asyncio.fixture
async def client(aiohttp_client):
    app = create_app()
    return await aiohttp_client(app)


@pytest.mark.asyncio
async def test_index_page(client):
    response = await client.get('/')
    assert response.status == 200
    text = await response.text()
    assert 'Объявления' in text
    assert 'doCreate' in text
    assert 'doGet' in text
    assert 'doDelete' in text


@pytest.mark.asyncio
async def test_create_and_list_ads(client):
    response = await client.post('/ads', json={'title': 'Квартира', 'owner': 'Иван'})
    assert response.status == 201
    data = await response.json()
    assert data['title'] == 'Квартира'
    assert data['owner'] == 'Иван'
    assert data['description'] == ''
    assert 'id' in data

    list_response = await client.get('/ads')
    assert list_response.status == 200
    all_ads = await list_response.json()
    assert isinstance(all_ads, list)
    assert any(item['title'] == 'Квартира' for item in all_ads)


@pytest.mark.asyncio
async def test_delete_ad(client):
    create_response = await client.post('/ads', json={'title': 'Удалить', 'owner': 'Анна'})
    created = await create_response.json()

    delete_response = await client.delete(f"/ads/{created['id']}")
    assert delete_response.status == 200
    assert await delete_response.json() == {'message': 'deleted'}
