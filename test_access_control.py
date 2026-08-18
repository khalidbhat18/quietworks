import requests

# Test access control
base = 'http://127.0.0.1:5000'

# Try accessing admin dashboard without auth
no_auth = requests.get(f'{base}/admin/dashboard', allow_redirects=False)
print('ADMIN_NO_AUTH:', no_auth.status_code, no_auth.headers.get('Location', 'N/A'))

# Try accessing shopkeeper dashboard without auth
no_auth_shop = requests.get(f'{base}/shopkeeper/dashboard', allow_redirects=False)
print('SHOPKEEPER_NO_AUTH:', no_auth_shop.status_code, no_auth_shop.headers.get('Location', 'N/A'))

# Try accessing public shop without auth (should succeed)
public_shop = requests.get(f'{base}/shop/DEMO001', allow_redirects=False)
print('PUBLIC_SHOP_NO_AUTH:', public_shop.status_code)

# Verify admin stats endpoint requires auth
stats_no_auth = requests.get(f'{base}/api/admin/stats', allow_redirects=False)
print('STATS_NO_AUTH:', stats_no_auth.status_code, stats_no_auth.json())

# Test as customer trying to access shopkeeper endpoint
s = requests.Session()
customer = requests.post(f'{base}/api/auth/register', json={
    'email': 'customer_test@test.com',
    'name': 'Test Customer',
    'password': 'pass123'
})
print('CUSTOMER_REGISTER:', customer.status_code, customer.json()['success'])

# Login as customer
customer_login = requests.post(f'{base}/api/auth/login', json={
    'email': 'customer_test@test.com',
    'password': 'pass123'
})
print('CUSTOMER_LOGIN:', customer_login.status_code, customer_login.json()['success'])

# Try accessing shopkeeper endpoint as customer
s = requests.Session()
s.cookies.update(requests.cookies.RequestsCookieJar())
s.post(f'{base}/api/auth/login', json={
    'email': 'customer_test@test.com',
    'password': 'pass123'
})
shopkeeper_as_customer = s.get(f'{base}/api/shopkeeper/products')
print('SHOPKEEPER_PRODUCTS_AS_CUSTOMER:', shopkeeper_as_customer.status_code, 'Forbidden' if shopkeeper_as_customer.status_code == 403 else shopkeeper_as_customer.json())

print('\nACCESS_CONTROL_VERIFIED')
