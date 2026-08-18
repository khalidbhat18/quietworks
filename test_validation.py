import requests, json

base = 'http://127.0.0.1:5000'

# health
r = requests.get(f'{base}/api/health')
print('HEALTH', r.status_code, r.json())

# admin login
s = requests.Session()
admin = s.post(f'{base}/api/auth/login', json={
    'email': 'admin@localshop.test',
    'password': 'admin123'
})
print('ADMIN_LOGIN', admin.status_code, admin.json())
assert admin.status_code == 200 and admin.json()['success']

admin_stats = s.get(f'{base}/api/admin/stats')
print('ADMIN_STATS', admin_stats.status_code, admin_stats.json()['stats'])
assert admin_stats.status_code == 200 and admin_stats.json()['stats']['total_shops'] >= 1

# shopkeeper login
s2 = requests.Session()
shopkeeper = s2.post(f'{base}/api/auth/login', json={
    'email': 'shopkeeper@localshop.test',
    'password': 'shop123'
})
print('SHOPKEEPER_LOGIN', shopkeeper.status_code, shopkeeper.json())
assert shopkeeper.status_code == 200 and shopkeeper.json()['success']

shop = s2.get(f'{base}/api/shopkeeper/shop')
print('SHOPKEEPER_SHOP', shop.status_code, shop.json())
assert shop.status_code == 200

shop_products = s2.get(f'{base}/api/shopkeeper/products')
print('SHOPKEEPER_PRODUCTS', shop_products.status_code, len(shop_products.json()['products']))
assert shop_products.status_code == 200 and len(shop_products.json()['products']) >= 10

# public shop and product filtering
pub = requests.get(f'{base}/api/shops/DEMO001/products')
print('PUBLIC_PRODUCTS', pub.status_code, len(pub.json()['products']))
assert pub.status_code == 200 and len(pub.json()['products']) >= 10
assert any(p['is_available'] is False for p in pub.json()['products'])

# unauthorized order with unavailable product
product_id = next(p['id'] for p in pub.json()['products'] if not p['is_available'])
order_bad = requests.post(f'{base}/api/orders', json={
    'shop_code': 'DEMO001',
    'customer_name': 'Test Customer',
    'customer_phone': '9999988888',
    'delivery_address': '123 Test Street',
    'items': [{'product_id': product_id, 'quantity': 1}],
})
print('UNAVAILABLE_ORDER', order_bad.status_code, order_bad.json())
assert order_bad.status_code == 400

# order with available product
product_id2 = next(p['id'] for p in pub.json()['products'] if p['is_available'])
order_ok = requests.post(f'{base}/api/orders', json={
    'shop_code': 'DEMO001',
    'customer_name': 'Test Customer',
    'customer_phone': '9999988888',
    'delivery_address': '123 Test Street',
    'items': [{'product_id': product_id2, 'quantity': 2}],
})
print('ORDER_OK', order_ok.status_code, order_ok.json())
assert order_ok.status_code == 200 and order_ok.json()['success']
order_id = order_ok.json()['order']['id']

# shopkeeper sees order and updates status
orders = s2.get(f'{base}/api/shopkeeper/orders')
print('SHOPKEEPER_ORDERS', orders.status_code, len(orders.json()['orders']))
assert orders.status_code == 200 and any(o['id'] == order_id for o in orders.json()['orders'])
status_update = s2.patch(f'{base}/api/shopkeeper/orders/{order_id}/status', json={'status': 'Accepted'})
print('STATUS_UPDATE', status_update.status_code, status_update.json())
assert status_update.status_code == 200

# admin can see order
admin_orders = s.get(f'{base}/api/admin/orders')
print('ADMIN_ORDERS', admin_orders.status_code, len(admin_orders.json()['orders']))
assert admin_orders.status_code == 200 and any(o['id'] == order_id for o in admin_orders.json()['orders'])

# unauthorized public access to private page
no_auth = requests.get(f'{base}/shopkeeper/dashboard', allow_redirects=False)
print('PRIVATE_REDIRECT', no_auth.status_code, no_auth.headers.get('Location'))
assert no_auth.status_code in (302, 401)

print('ALL_CHECKS_PASSED')
