# LocalShop MVP

LocalShop is a local retail ordering platform for multiple shops, customers, shopkeepers, and admins.

## Features

- Multi-shop public storefronts
- QR-based store access via /shop/{shop_code}
- Customer cart and COD checkout
- Shopkeeper dashboard with products and orders
- Admin dashboard for shops, users, products, and statistics
- SQLite database with persistent data
- Role-based authentication and authorization

## Local setup on Windows

1. Install Python 3.11+ and ensure it is available in PATH.
2. Open a terminal in the project root.
3. Create a virtual environment:
   py -m venv .venv
   .venv\Scripts\activate
4. Install dependencies:
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
5. Copy .env.example to .env and update values if needed.
6. Initialize the database by running the app once:
   python run_backend.py
7. The app will create the SQLite database and seed demo data automatically.
8. Open the browser to: http://127.0.0.1:5000/

## Demo login credentials

- Admin: admin@localshop.test / admin123
- Shopkeeper: shopkeeper@localshop.test / shop123

## Demo shop

- Shop name: Demo Local Store
- Shop code: DEMO001
- Public URL: http://127.0.0.1:5000/shop/DEMO001
- QR URL: http://127.0.0.1:5000/qr/DEMO001

## Project structure

- backend/ - Flask backend and API
- frontend/ - HTML, CSS, JS frontend templates and static assets
- database/ - SQLite database files
- static/ - QR images and generated assets
- uploads/ - product and shop images
- tests/ - automated tests

## Git commands

```bash
git init
git add .
git commit -m "Initial LocalShop MVP"
git branch
git remote add origin <your-repo-url>
git push -u origin main
```

## Future-ready architecture

The project is structured so it can later support delivery partners, payments, notifications, analytics, and broader e-commerce features.
