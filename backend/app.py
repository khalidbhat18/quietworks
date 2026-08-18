import os
import uuid
from datetime import datetime
from pathlib import Path

import qrcode
from dotenv import load_dotenv
from flask import Flask, Response, abort, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

load_dotenv(Path(__file__).resolve().parent.parent / '.env')

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_FOLDER = BASE_DIR / 'uploads'
QR_FOLDER = BASE_DIR / 'static' / 'qr'

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
QR_FOLDER.mkdir(parents=True, exist_ok=True)

DB_PATH = BASE_DIR / 'database' / 'localshop.db'
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(32), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(32), nullable=False, default='CUSTOMER')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    shops = db.relationship('ShopkeeperShop', back_populates='user', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Shop(db.Model):
    __tablename__ = 'shops'

    id = db.Column(db.Integer, primary_key=True)
    shop_code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    logo = db.Column(db.String(255), default='')
    description = db.Column(db.Text, default='')
    address = db.Column(db.String(255), default='')
    phone = db.Column(db.String(32), default='')
    opening_hours = db.Column(db.String(255), default='')
    status = db.Column(db.String(32), default='Open')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    products = db.relationship('Product', back_populates='shop', cascade='all, delete-orphan')
    shopkeepers = db.relationship('ShopkeeperShop', back_populates='shop', cascade='all, delete-orphan')
    orders = db.relationship('Order', back_populates='shop', cascade='all, delete-orphan')


class ShopkeeperShop(db.Model):
    __tablename__ = 'shopkeeper_shops'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shops.id'), primary_key=True)

    user = db.relationship('User', back_populates='shops')
    shop = db.relationship('Shop', back_populates='shopkeepers')


class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shops.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    category = db.Column(db.String(100), default='General')
    price = db.Column(db.Float, nullable=False, default=0.0)
    image = db.Column(db.String(255), default='')
    is_available = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    shop = db.relationship('Shop', back_populates='products')


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shops.id'), nullable=False)
    customer_name = db.Column(db.String(120), nullable=False)
    customer_phone = db.Column(db.String(32), nullable=False)
    delivery_address = db.Column(db.String(255), nullable=False)
    delivery_instructions = db.Column(db.Text, default='')
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    payment_method = db.Column(db.String(50), default='Cash on Delivery')
    status = db.Column(db.String(50), default='Pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    shop = db.relationship('Shop', back_populates='orders')
    items = db.relationship('OrderItem', back_populates='order', cascade='all, delete-orphan')


class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    product_name_snapshot = db.Column(db.String(200), nullable=False)
    price_snapshot = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)

    order = db.relationship('Order', back_populates='items')


def save_uploaded_file(file_storage):
    if not file_storage or file_storage.filename == '':
        return ''
    ext = os.path.splitext(file_storage.filename)[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    path = UPLOAD_FOLDER / unique_name
    file_storage.save(path)
    return f"/uploads/{unique_name}"


def generate_qr_image(shop_code):
    qr_dir = QR_FOLDER / f'{shop_code.upper()}.png'
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(f'/shop/{shop_code.upper()}')
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    img.save(qr_dir)
    return f'/static/qr/{shop_code.upper()}.png'


def serialize_shop(shop):
    return {
        'id': shop.id,
        'shop_code': shop.shop_code,
        'name': shop.name,
        'logo': shop.logo,
        'description': shop.description,
        'address': shop.address,
        'phone': shop.phone,
        'opening_hours': shop.opening_hours,
        'status': shop.status,
        'qr_code_url': f'/qr/{shop.shop_code}',
        'created_at': shop.created_at.isoformat() if shop.created_at else None,
    }


def serialize_product(product):
    return {
        'id': product.id,
        'shop_id': product.shop_id,
        'name': product.name,
        'description': product.description,
        'category': product.category,
        'price': float(product.price),
        'image': product.image,
        'is_available': bool(product.is_available),
        'created_at': product.created_at.isoformat() if product.created_at else None,
        'updated_at': product.updated_at.isoformat() if product.updated_at else None,
    }


def serialize_order(order):
    return {
        'id': order.id,
        'shop_id': order.shop_id,
        'shop_name': order.shop.name if order.shop else '',
        'customer_name': order.customer_name,
        'customer_phone': order.customer_phone,
        'delivery_address': order.delivery_address,
        'delivery_instructions': order.delivery_instructions,
        'total_amount': float(order.total_amount),
        'payment_method': order.payment_method,
        'status': order.status,
        'created_at': order.created_at.isoformat() if order.created_at else None,
        'items': [
            {
                'id': item.id,
                'product_id': item.product_id,
                'product_name_snapshot': item.product_name_snapshot,
                'price_snapshot': float(item.price_snapshot),
                'quantity': item.quantity,
                'subtotal': float(item.subtotal),
            }
            for item in order.items
        ],
    }


def create_app():
    app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'localshop-dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', f'sqlite:///{DB_PATH}')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    def seed_demo_data():
        if User.query.filter_by(email='admin@localshop.test').first():
            return
        admin = User(name='System Admin', email='admin@localshop.test', phone='9999999999', role='ADMIN')
        admin.set_password('admin123')
        db.session.add(admin)

        shopkeeper = User(name='Demo Shopkeeper', email='shopkeeper@localshop.test', phone='9876543210', role='SHOPKEEPER')
        shopkeeper.set_password('shop123')
        db.session.add(shopkeeper)
        db.session.flush()

        shop = Shop(
            shop_code='DEMO001',
            name='Demo Local Store',
            logo='/static/images/shop-logo.svg',
            description='Fresh groceries, essentials, and household items for local families.',
            address='Near Main Market, Sector 7, Delhi',
            phone='+91 98765 43210',
            opening_hours='8:00 AM - 9:00 PM',
            status='Open',
        )
        db.session.add(shop)
        db.session.flush()

        db.session.add(ShopkeeperShop(user_id=shopkeeper.id, shop_id=shop.id))

        product_data = [
            ('Milk 1L', 'Fresh dairy milk.', 'Dairy', 60.0, True),
            ('Bread', 'Whole wheat bread loaf.', 'Bakery', 45.0, True),
            ('Rice 5kg', 'Premium rice for daily meals.', 'Grains', 280.0, True),
            ('Wheat Flour 5kg', 'Stone-ground atta.', 'Grains', 230.0, True),
            ('Sugar 1kg', 'Refined sugar.', 'Groceries', 55.0, True),
            ('Tea', 'Aromatic black tea.', 'Beverages', 120.0, True),
            ('Biscuits', 'Crispy family biscuits.', 'Snacks', 40.0, False),
            ('Cooking Oil', 'High quality cooking oil.', 'Household', 180.0, True),
            ('Salt', 'Iodized salt.', 'Groceries', 20.0, True),
            ('Soap', 'Gentle bath soap.', 'Household', 35.0, False),
        ]
        for name, description, category, price, available in product_data:
            p = Product(
                shop_id=shop.id,
                name=name,
                description=description,
                category=category,
                price=price,
                image='/static/images/default-product.svg',
                is_available=available,
            )
            db.session.add(p)

        db.session.commit()
        generate_qr_image('DEMO001')

    with app.app_context():
        db.create_all()
        seed_demo_data()

    def get_current_user():
        user_id = session.get('user_id')
        if not user_id:
            return None
        return User.query.get(user_id)

    def get_current_shopkeeper_shop():
        user = get_current_user()
        if not user or user.role != 'SHOPKEEPER':
            return None
        mapping = ShopkeeperShop.query.filter_by(user_id=user.id).first()
        return mapping.shop if mapping else None

    def role_required(required_role):
        def decorator(func):
            def wrapped(*args, **kwargs):
                user = get_current_user()
                if not user:
                    if request.path.startswith('/api/'):
                        return jsonify({'success': False, 'message': 'Authentication required.'}), 401
                    return redirect('/login')
                if user.role != required_role:
                    if request.path.startswith('/api/'):
                        return jsonify({'success': False, 'message': 'Access denied.'}), 403
                    return redirect('/login')
                return func(*args, **kwargs)
            wrapped.__name__ = func.__name__
            return wrapped
        return decorator

    @app.context_processor
    def inject_user():
        user = get_current_user()
        return {'current_user': user}

    @app.route('/')
    def home():
        if session.get('user_id'):
            role = session.get('role')
            if role == 'ADMIN':
                return redirect('/admin/dashboard')
            if role == 'SHOPKEEPER':
                return redirect('/shopkeeper/dashboard')
        return render_template('index.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login_page():
        if request.method == 'POST':
            email = (request.form.get('email') or '').strip().lower()
            password = request.form.get('password') or ''
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                session['user_id'] = user.id
                session['role'] = user.role
                if user.role == 'ADMIN':
                    return redirect('/admin/dashboard')
                if user.role == 'SHOPKEEPER':
                    return redirect('/shopkeeper/dashboard')
                return redirect('/')
            return render_template('auth_login.html', error='Invalid email or password.')
        return render_template('auth_login.html')

    @app.route('/api/auth/login', methods=['POST'])
    def api_login():
        data = request.get_json(silent=True) or {}
        email = (data.get('email') or '').strip().lower()
        password = data.get('password') or ''
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            return jsonify({'success': False, 'message': 'Invalid email or password.'}), 401
        session['user_id'] = user.id
        session['role'] = user.role
        return jsonify({
            'success': True,
            'message': 'Login successful.',
            'role': user.role,
            'redirect': '/admin/dashboard' if user.role == 'ADMIN' else '/shopkeeper/dashboard' if user.role == 'SHOPKEEPER' else '/',
        })

    @app.route('/api/auth/register', methods=['POST'])
    def api_register():
        data = request.get_json(silent=True) or {}
        email = (data.get('email') or '').strip().lower()
        name = (data.get('name') or '').strip()
        password = data.get('password') or ''
        if not email or not name or not password:
            return jsonify({'success': False, 'message': 'Name, email and password are required.'}), 400
        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'message': 'Email already registered.'}), 409
        user = User(name=name, email=email, phone=data.get('phone', '0000000000'), role='CUSTOMER')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Customer registered successfully.'})

    @app.route('/api/auth/logout', methods=['POST'])
    def api_logout():
        session.clear()
        return jsonify({'success': True, 'message': 'Logged out.'})

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect('/login')

    @app.route('/admin/dashboard')
    @role_required('ADMIN')
    def admin_dashboard():
        return render_template('admin_dashboard.html')

    @app.route('/shopkeeper/dashboard')
    @role_required('SHOPKEEPER')
    def shopkeeper_dashboard():
        return render_template('shopkeeper_dashboard.html')

    @app.route('/checkout')
    def checkout_page():
        shop_code = (request.args.get('shop_code') or '').upper()
        shop = Shop.query.filter_by(shop_code=shop_code).first()
        if not shop:
            return render_template('shop_public.html', shop=None, error='This shop could not be found.'), 404
        return render_template('checkout.html', shop=shop)

    @app.route('/order-confirmation')
    def order_confirmation_page():
        order_id = request.args.get('id')
        order = Order.query.get(order_id)
        if not order:
            return render_template('order_confirmation.html', order=None)
        order_data = serialize_order(order)
        order_data['shop_code'] = order.shop.shop_code if order.shop else ''
        return render_template('order_confirmation.html', order=order_data)

    @app.route('/shop/<shop_code>')
    def public_shop(shop_code):
        shop = Shop.query.filter_by(shop_code=shop_code.upper()).first()
        if not shop:
            return render_template('shop_public.html', shop=None, error='This shop could not be found.'), 404
        return render_template('shop_public.html', shop=shop)

    @app.route('/qr/<shop_code>')
    def shop_qr(shop_code):
        code = shop_code.upper()
        shop = Shop.query.filter_by(shop_code=code).first()
        if not shop:
            abort(404)
        image_path = QR_FOLDER / f'{code}.png'
        if not image_path.exists():
            generate_qr_image(code)
        return send_file(image_path, mimetype='image/png')

    @app.route('/api/shops/<shop_code>', methods=['GET'])
    def get_shop_public(shop_code):
        shop = Shop.query.filter_by(shop_code=shop_code.upper()).first()
        if not shop:
            return jsonify({'success': False, 'message': 'Shop not found.'}), 404
        return jsonify({'success': True, 'shop': serialize_shop(shop)})

    @app.route('/api/shops/<shop_code>/products', methods=['GET'])
    def get_shop_products(shop_code):
        shop = Shop.query.filter_by(shop_code=shop_code.upper()).first()
        if not shop:
            return jsonify({'success': False, 'message': 'Shop not found.'}), 404
        products = Product.query.filter_by(shop_id=shop.id).order_by(Product.name.asc()).all()
        return jsonify({'success': True, 'products': [serialize_product(p) for p in products]})

    @app.route('/api/orders', methods=['POST'])
    def create_order():
        data = request.get_json(silent=True) or {}
        shop_code = (data.get('shop_code') or '').upper()
        items = data.get('items') or []
        customer_name = (data.get('customer_name') or '').strip()
        customer_phone = (data.get('customer_phone') or '').strip()
        delivery_address = (data.get('delivery_address') or '').strip()
        delivery_instructions = (data.get('delivery_instructions') or '').strip()

        if not shop_code or not customer_name or not customer_phone or not delivery_address or not items:
            return jsonify({'success': False, 'message': 'Please provide customer details and at least one item in the cart.'}), 400

        shop = Shop.query.filter_by(shop_code=shop_code).first()
        if not shop:
            return jsonify({'success': False, 'message': 'Shop not found.'}), 404

        total = 0.0
        validated_items = []
        for entry in items:
            product = Product.query.get(entry.get('product_id'))
            if not product or product.shop_id != shop.id:
                return jsonify({'success': False, 'message': f"Product {entry.get('product_id')} is not available in this shop."}), 400
            if not product.is_available:
                return jsonify({'success': False, 'message': f"{product.name} is currently unavailable."}), 400
            qty = int(entry.get('quantity') or 0)
            if qty <= 0:
                return jsonify({'success': False, 'message': f"Invalid quantity for {product.name}."}), 400
            subtotal = product.price * qty
            total += subtotal
            validated_items.append({
                'product': product,
                'quantity': qty,
                'subtotal': subtotal,
            })

        order = Order(
            shop_id=shop.id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            delivery_address=delivery_address,
            delivery_instructions=delivery_instructions,
            total_amount=total,
            payment_method='Cash on Delivery',
            status='Pending',
        )
        db.session.add(order)
        db.session.flush()

        for item in validated_items:
            product = item['product']
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name_snapshot=product.name,
                price_snapshot=float(product.price),
                quantity=item['quantity'],
                subtotal=float(item['subtotal']),
            )
            db.session.add(order_item)

        db.session.commit()
        return jsonify({'success': True, 'message': 'Order placed successfully.', 'order': serialize_order(order)})

    @app.route('/api/shopkeeper/shop', methods=['GET'])
    @role_required('SHOPKEEPER')
    def get_shopkeeper_shop():
        shop = get_current_shopkeeper_shop()
        if not shop:
            return jsonify({'success': False, 'message': 'No shop assigned to this shopkeeper.'}), 404
        return jsonify({'success': True, 'shop': serialize_shop(shop)})

    @app.route('/api/shopkeeper/shop', methods=['PUT'])
    @role_required('SHOPKEEPER')
    def update_shopkeeper_shop():
        shop = get_current_shopkeeper_shop()
        data = request.get_json(silent=True) or {}
        if not shop:
            return jsonify({'success': False, 'message': 'No shop assigned.'}), 404
        shop.name = data.get('name', shop.name)
        shop.description = data.get('description', shop.description)
        shop.address = data.get('address', shop.address)
        shop.phone = data.get('phone', shop.phone)
        shop.opening_hours = data.get('opening_hours', shop.opening_hours)
        shop.status = data.get('status', shop.status)
        if data.get('logo'):
            shop.logo = data['logo']
        db.session.commit()
        return jsonify({'success': True, 'shop': serialize_shop(shop)})

    @app.route('/api/shopkeeper/products', methods=['GET'])
    @role_required('SHOPKEEPER')
    def shopkeeper_products():
        shop = get_current_shopkeeper_shop()
        products = Product.query.filter_by(shop_id=shop.id).order_by(Product.name.asc()).all() if shop else []
        return jsonify({'success': True, 'products': [serialize_product(p) for p in products]})

    @app.route('/api/shopkeeper/products', methods=['POST'])
    @role_required('SHOPKEEPER')
    def create_shopkeeper_product():
        shop = get_current_shopkeeper_shop()
        if not shop:
            return jsonify({'success': False, 'message': 'No assigned shop.'}), 404
        data = request.form.to_dict() if request.form else (request.get_json(silent=True) or {})
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'success': False, 'message': 'Product name is required.'}), 400
        image_value = ''
        if 'image' in request.files and request.files['image'].filename:
            image_value = save_uploaded_file(request.files['image'])
        elif data.get('image'):
            image_value = data.get('image')
        product = Product(
            shop_id=shop.id,
            name=name,
            description=data.get('description', ''),
            category=data.get('category', 'General'),
            price=float(data.get('price', 0) or 0),
            image=image_value,
            is_available=data.get('is_available', 'true').lower() in ('true', '1', 'yes'),
        )
        db.session.add(product)
        db.session.commit()
        return jsonify({'success': True, 'product': serialize_product(product)})

    @app.route('/api/shopkeeper/products/<int:product_id>', methods=['PUT'])
    @role_required('SHOPKEEPER')
    def update_shopkeeper_product(product_id):
        shop = get_current_shopkeeper_shop()
        product = Product.query.filter_by(id=product_id, shop_id=shop.id).first() if shop else None
        if not product:
            return jsonify({'success': False, 'message': 'Product not found or access denied.'}), 404
        data = request.form.to_dict() if request.form else (request.get_json(silent=True) or {})
        if 'name' in data and (data.get('name') or '').strip():
            product.name = (data.get('name') or '').strip()
        if 'description' in data:
            product.description = data.get('description', '')
        if 'category' in data:
            product.category = data.get('category', product.category)
        if 'price' in data:
            product.price = float(data.get('price') or 0)
        if 'is_available' in data:
            product.is_available = str(data.get('is_available')).lower() in ('true', '1', 'yes')
        if 'image' in request.files and request.files['image'].filename:
            product.image = save_uploaded_file(request.files['image'])
        elif 'image' in data and data.get('image'):
            product.image = data.get('image')
        db.session.commit()
        return jsonify({'success': True, 'product': serialize_product(product)})

    @app.route('/api/shopkeeper/products/<int:product_id>', methods=['DELETE'])
    @role_required('SHOPKEEPER')
    def delete_shopkeeper_product(product_id):
        shop = get_current_shopkeeper_shop()
        product = Product.query.filter_by(id=product_id, shop_id=shop.id).first() if shop else None
        if not product:
            return jsonify({'success': False, 'message': 'Product not found or access denied.'}), 404
        db.session.delete(product)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Product deleted.'})

    @app.route('/api/shopkeeper/products/<int:product_id>/availability', methods=['PATCH'])
    @role_required('SHOPKEEPER')
    def toggle_product_availability(product_id):
        shop = get_current_shopkeeper_shop()
        product = Product.query.filter_by(id=product_id, shop_id=shop.id).first() if shop else None
        if not product:
            return jsonify({'success': False, 'message': 'Product not found or access denied.'}), 404
        data = request.get_json(silent=True) or {}
        product.is_available = bool(data.get('is_available', product.is_available))
        db.session.commit()
        return jsonify({'success': True, 'product': serialize_product(product)})

    @app.route('/api/shopkeeper/orders', methods=['GET'])
    @role_required('SHOPKEEPER')
    def shopkeeper_orders():
        shop = get_current_shopkeeper_shop()
        if not shop:
            return jsonify({'success': False, 'message': 'No assigned shop.'}), 404
        orders = Order.query.filter_by(shop_id=shop.id).order_by(Order.created_at.desc()).all()
        return jsonify({'success': True, 'orders': [serialize_order(order) for order in orders]})

    @app.route('/api/shopkeeper/orders/<int:order_id>/status', methods=['PATCH'])
    @role_required('SHOPKEEPER')
    def update_order_status(order_id):
        shop = get_current_shopkeeper_shop()
        order = Order.query.filter_by(id=order_id, shop_id=shop.id).first() if shop else None
        if not order:
            return jsonify({'success': False, 'message': 'Order not found or access denied.'}), 404
        data = request.get_json(silent=True) or {}
        status = (data.get('status') or '').strip()
        if not status:
            return jsonify({'success': False, 'message': 'Status is required.'}), 400
        valid_status = ['Pending', 'Accepted', 'Preparing', 'Out for Delivery', 'Delivered', 'Rejected']
        if status not in valid_status:
            return jsonify({'success': False, 'message': 'Invalid status.'}), 400
        order.status = status
        order.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True, 'order': serialize_order(order)})

    @app.route('/api/admin/shops', methods=['GET'])
    @role_required('ADMIN')
    def admin_shops():
        shops = Shop.query.order_by(Shop.created_at.desc()).all()
        return jsonify({'success': True, 'shops': [serialize_shop(shop) for shop in shops]})

    @app.route('/api/admin/shops', methods=['POST'])
    @role_required('ADMIN')
    def create_shop():
        data = request.get_json(silent=True) or {}
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'success': False, 'message': 'Shop name is required.'}), 400
        code = (data.get('shop_code') or '').upper().strip()
        if not code:
            code = generate_shop_code()
        if Shop.query.filter_by(shop_code=code).first():
            return jsonify({'success': False, 'message': 'Shop code must be unique.'}), 409
        shop = Shop(
            shop_code=code,
            name=name,
            description=data.get('description', ''),
            address=data.get('address', ''),
            phone=data.get('phone', ''),
            opening_hours=data.get('opening_hours', '9:00 AM - 9:00 PM'),
            status=data.get('status', 'Open'),
            logo=data.get('logo', ''),
        )
        db.session.add(shop)
        db.session.commit()
        generate_qr_image(shop.shop_code)
        return jsonify({'success': True, 'shop': serialize_shop(shop)})

    @app.route('/api/admin/shops/<int:shop_id>', methods=['PUT'])
    @role_required('ADMIN')
    def update_shop(shop_id):
        shop = Shop.query.get_or_404(shop_id)
        data = request.get_json(silent=True) or {}
        if 'name' in data:
            shop.name = data.get('name', shop.name)
        if 'description' in data:
            shop.description = data.get('description', shop.description)
        if 'status' in data:
            shop.status = data.get('status', shop.status)
        if 'address' in data:
            shop.address = data.get('address', shop.address)
        if 'phone' in data:
            shop.phone = data.get('phone', shop.phone)
        if 'opening_hours' in data:
            shop.opening_hours = data.get('opening_hours', shop.opening_hours)
        if 'logo' in data and data.get('logo'):
            shop.logo = data.get('logo')
        db.session.commit()
        return jsonify({'success': True, 'shop': serialize_shop(shop)})

    @app.route('/api/admin/shopkeepers', methods=['GET'])
    @role_required('ADMIN')
    def admin_shopkeepers():
        users = User.query.filter_by(role='SHOPKEEPER').all()
        result = []
        for user in users:
            shops = [shop.shop for shop in user.shops]
            result.append({
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'phone': user.phone,
                'role': user.role,
                'shop_ids': [s.id for s in shops],
                'shop_names': [s.name for s in shops],
                'created_at': user.created_at.isoformat() if user.created_at else None,
            })
        return jsonify({'success': True, 'shopkeepers': result})

    @app.route('/api/admin/shopkeepers', methods=['POST'])
    @role_required('ADMIN')
    def create_shopkeeper():
        data = request.get_json(silent=True) or {}
        email = (data.get('email') or '').strip().lower()
        name = (data.get('name') or '').strip()
        password = data.get('password') or ''
        shop_id = data.get('shop_id')
        if not email or not name or not password or not shop_id:
            return jsonify({'success': False, 'message': 'Name, email, password and shop are required.'}), 400
        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'message': 'Email already exists.'}), 409
        shop = Shop.query.get(shop_id)
        if not shop:
            return jsonify({'success': False, 'message': 'Shop not found.'}), 404
        user = User(name=name, email=email, phone=data.get('phone', '0000000000'), role='SHOPKEEPER')
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        db.session.add(ShopkeeperShop(user_id=user.id, shop_id=shop.id))
        db.session.commit()
        return jsonify({'success': True, 'shopkeeper': {'id': user.id, 'name': user.name, 'email': user.email, 'role': user.role}})

    @app.route('/api/admin/products', methods=['GET'])
    @role_required('ADMIN')
    def admin_products():
        products = Product.query.order_by(Product.created_at.desc()).all()
        return jsonify({'success': True, 'products': [serialize_product(p) for p in products]})

    @app.route('/api/admin/orders', methods=['GET'])
    @role_required('ADMIN')
    def admin_orders():
        orders = Order.query.order_by(Order.created_at.desc()).all()
        return jsonify({'success': True, 'orders': [serialize_order(order) for order in orders]})

    @app.route('/api/admin/stats', methods=['GET'])
    @role_required('ADMIN')
    def admin_stats():
        stats = {
            'total_shops': Shop.query.count(),
            'active_shops': Shop.query.filter_by(status='Open').count(),
            'total_products': Product.query.count(),
            'total_orders': Order.query.count(),
            'pending_orders': Order.query.filter_by(status='Pending').count(),
            'delivered_orders': Order.query.filter_by(status='Delivered').count(),
        }
        return jsonify({'success': True, 'stats': stats})

    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({'success': True, 'status': 'ok'})

    def generate_shop_code():
        prefix = 'SHOP'
        max_number = 999
        used = Shop.query.order_by(Shop.id.desc()).first()
        next_idx = 1
        if used:
            last = used.shop_code.replace('SHOP', '')
            try:
                next_idx = int(last) + 1
            except ValueError:
                next_idx = 1
        return f'{prefix}{str(next_idx).zfill(3)}'

    return app


app = create_app()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
