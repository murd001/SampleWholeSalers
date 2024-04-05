import os
import re
from flask import Flask, render_template, request, redirect, url_for, flash, session, get_flashed_messages
from flask import jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import csv
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db' 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'  
app.config['UPLOAD_FOLDER'] = 'static/uploads'  # Folder for storing uploaded files
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}  # Allowed file extensions

db = SQLAlchemy(app)

# Define User model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    contact_person = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    carts = db.relationship('UserCart', backref='user', lazy=True)
    orders = db.relationship('UserOrder', backref='user', lazy=True)

# Define Product model
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)  # New field for quantity
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    images = db.Column(db.String(255))
    user_orders = db.relationship('UserOrder', backref='product', lazy=True)
    admin_orders = db.relationship('AdminOrder', backref='product', lazy=True)

# Define Category model
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

# Define UserCart model
class UserCart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    added_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    product = relationship('Product', backref='carts')

# Define UserOrder model
class UserOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    ordered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

# Define AdminOrder model
class AdminOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ordered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    delivered = db.Column(db.Boolean, nullable=False, default=False)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Define logout route
@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('home'))

# Route for registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        company_name = request.form['companyName']
        contact_person = request.form['contactPerson']
        email = request.form['email']
        phone = request.form['phone']
        address = request.form['address']
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            flash('Email already exists. Please choose a different one.')
            return redirect(url_for('register'))
        new_user = User(company_name=company_name, contact_person=contact_person, email=email, phone=phone, address=address)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful. Please login.')
        return redirect(url_for('login'))  
    return render_template('signup.html')

# Route for home page
@app.route('/')
def home():
    categories = Category.query.all()
    products = Product.query.all()
    if not products:  
        flash('No products available.')
    return render_template('home.html', categories=categories, products=products)

# Define login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful.')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password.')
    return render_template('login.html')


@app.route('/admin/add-product/blahxyz', methods=['GET', 'POST'])
def admin_add_product():
    if request.method == 'POST':
        uploaded_file_paths = []
        if 'images[]' in request.files:
            files = request.files.getlist('images[]')
            for file in files:
                if file.filename != '':
                    if allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        uploaded_file_paths.append(filename)
                    else:
                        flash('Invalid file extension')
        else:
            flash('No file part')
        category_id = request.form['category']
        name = request.form['name']
        quantity = int(request.form['quantity'])
        description = request.form['description']
        price = request.form['unit_price']
        new_product = Product(name=name, category_id=category_id, quantity=quantity, description=description, price=price)
        new_product.images = ','.join(uploaded_file_paths) 
        db.session.add(new_product)
        db.session.commit()
        flash('Product added successfully.')
        return redirect(url_for('admin_add_product'))    
    categories = Category.query.all()
    return render_template('admin.html', categories=categories)

@app.route('/product/<int:product_id>')
def product_details(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product_details.html', product=product)

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    quantity = int(request.form['quantity'])
    product = Product.query.get(product_id)
    if product:
        cart_item = UserCart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
        if cart_item:
            cart_item.quantity += quantity
        else:
            new_cart_item = UserCart(user_id=current_user.id, product_id=product_id, quantity=quantity)
            db.session.add(new_cart_item)
        db.session.commit()
        flash('Product added to cart.')
    else:
        flash('Product not found.')
    return redirect(url_for('cart'))

@app.route('/cart')
@login_required
def cart():
    cart_items = UserCart.query.filter_by(user_id=current_user.id).all()
    total_amount = 0
    cart_products = []
    for cart_item in cart_items:
        product = Product.query.get(cart_item.product_id)
        if product:
            item_total = product.price * cart_item.quantity
            total_amount += item_total
            cart_products.append((product.name, product.description, product.price, cart_item.quantity, item_total))
    return render_template('cart.html', cart_products=cart_products, total_amount=total_amount, cart_items=cart_items)

@app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
@login_required
def remove_from_cart(product_id):
    cart_item = UserCart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()
        flash('Product removed from cart.')
    else:
        flash('Product not found in cart.')
    return redirect(url_for('cart'))
    
@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    if query:
        products = Product.query.filter(Product.name.ilike(f"%{query}%")).all()
        return render_template('home.html', categories=Category.query.all(), products=products)
    else:
        flash('Please enter a search query.')
        return redirect(url_for('home'))

# Define route for checkout page
@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if request.method == 'POST':
        transaction_code = request.form['transaction-code']
        # Check if the transaction code matches the required pattern
        if re.match(r'^[Ss]\w{9}$', transaction_code):
            cart_items = UserCart.query.filter_by(user_id=current_user.id).all()
            for cart_item in cart_items:
                product = Product.query.get(cart_item.product_id)
                if product:
                    if cart_item.quantity <= product.quantity:
                        # Update inventory
                        product.quantity -= cart_item.quantity
                        # Mark item as sold
                        new_order = UserOrder(user_id=current_user.id, product_id=product.id, quantity=cart_item.quantity, total_price=cart_item.quantity * product.price)
                        db.session.add(new_order)
                        # Add the order to the all orders table
                        all_order = AdminOrder(user_id=current_user.id, product_id=product.id, quantity=cart_item.quantity, total_price=cart_item.quantity * product.price)
                        db.session.add(all_order)
                        db.session.delete(cart_item)
                    else:
                        flash(f"Not enough quantity available for {product.name}.")
                        return redirect(url_for('checkout'))
            db.session.commit()
            flash(' ', 'success') 
            return redirect(url_for('orders')) 
        else:
            flash('Invalid transaction code. ', 'error') 
            return redirect(url_for('checkout'))

    cart_items = UserCart.query.filter_by(user_id=current_user.id).all()
    total_amount = 0
    cart_products = []
    for cart_item in cart_items:
        product = Product.query.get(cart_item.product_id)
        if product:
            item_total = product.price * cart_item.quantity
            total_amount += item_total
            cart_products.append((product.name, product.description, product.price, cart_item.quantity, item_total))
    return render_template('checkout.html', cart_products=cart_products, total_amount=total_amount, cart_items=cart_items, messages=get_flashed_messages(with_categories=True))  

# Define a route to handle AJAX request for updating cart quantity
@app.route('/update_cart_quantity', methods=['POST'])
@login_required
def update_cart_quantity():
    data = request.get_json()
    product_id = data['product_id']
    new_quantity = data['new_quantity']
    cart_item = UserCart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if cart_item:
        cart_item.quantity = new_quantity
        db.session.commit()
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Cart item not found.'})    
    
@app.route('/orders')
@login_required
def orders():
    orders = UserOrder.query.filter_by(user_id=current_user.id).all()
    return render_template('orders.html', orders=orders)

@app.route('/admin/orders/blahxyz')
@login_required
def admin_orders():
    orders = AdminOrder.query.all()
    return render_template('admin_orders.html', orders=orders)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables
    app.run(debug=True)
