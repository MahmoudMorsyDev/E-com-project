import dotenv
from flask import Flask,jsonify, render_template,redirect, url_for, request, flash, abort
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, IntegerField
from wtforms.validators import DataRequired
from flask_sqlalchemy import SQLAlchemy
import werkzeug.security
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_gravatar import Gravatar
from functools import wraps
import stripe
import os

dotenv.load_dotenv()
app = Flask(__name__)



app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
Bootstrap(app)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK-MODIFICATIONS'] = False
db= SQLAlchemy(app)
gravatar = Gravatar( app,\
                     size=100,
                     rating='g',
                     default ='retro',
                     force_default=False,
                     force_lower=False,
                     use_ssl =False,
                     base_url=None
                     )

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return Data.query.get(int(user_id))


class Data(UserMixin, db.Model):
    __tablename__ = 'users-data'
    id = db.Column(db.Integer, primary_key=True)
    name= db.Column(db.String(200), nullable=False)
    email=db.Column(db.String(200), nullable=False)
    password=db.Column(db.String(200), nullable=False)
    products = relationship('UserCart', back_populates = 'user')

class UserCart(db.Model):
    __tablename__= 'user-cart'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users-data.id'))
    user = relationship('Data', back_populates='products')
    product_name = db.Column(db.String(250), nullable=False)
    product_description =db.Column(db.Text, nullable= False)
    product_price = db.Column(db.Integer, nullable=False)
    product_img = db.Column(db. String(250), nullable=False)




class Produts(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(250), nullable = False)
    product_description = db.Column(db.Text, nullable=False)
    product_price = db.Column(db.Integer, nullable=False)
    product_category = db.Column(db.String(250), nullable = False)
    product_img = db.Column(db.String(250), nullable=False)
#db.create_all()
#Produts.__table__.drop(db.engine)
admin = Data.query.filter_by(id=1).first()
def admin_only(f):
    @wraps(f)
    def decorated_functions(*args, **kwargs):
        if current_user.is_authenticated and current_user.id == 1:
            return f(*args, **kwargs)
        else:
            return abort(403)
    return decorated_functions
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')
class RegisterForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Your password', validators=[DataRequired()])
    re_password = PasswordField('Re-enter your password', validators=[DataRequired()])
    submit = SubmitField('Complete Registration')
class AddItem(FlaskForm):
    name = StringField('Item Name', validators=[DataRequired()])
    description = StringField('Description', validators=[DataRequired()])
    price = IntegerField('Price', validators=[DataRequired()])
    product_image = StringField('Image', validators=[DataRequired()])
    category = StringField('Category', validators=[DataRequired()])
    submit = SubmitField('Add Item')
#db.create_all()
@app.route('/', methods=['GET', 'POST'])
def home():
    products = Produts.query.all()
    return render_template('index.html',logged_in=current_user.is_authenticated, admin= admin, products= products)





@app.route('/register-user',  methods=['GET', 'POST'])
def register_user():
    register_form = RegisterForm()
    if register_form.validate_on_submit():
        if register_form.password.data == register_form.re_password.data:
            hashed_pass = werkzeug.security.generate_password_hash(
                password= register_form.password.data,
                method= 'pbkdf2:sha256',
                salt_length=8
            )
            new_user = Data(
                name = register_form.name.data,
                password = hashed_pass,
                email= register_form.email.data
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return render_template('index.html', logged_in=current_user.is_authenticated, admin= admin)
    return render_template('register-user.html', form = register_form)


@app.route('/log-in',methods=['GET', 'POST'])
def log_in():
    login_form = LoginForm()
    if login_form.validate_on_submit():
        email = login_form.email.data
        password = login_form.password.data
        user = Data.query.filter_by(email=email).first()
        if not user:
            flash('You have entered a wrong email')
            return render_template('log-in.html', form=login_form)
        elif not check_password_hash(user.password, password):
            flash('invalid password')
            return render_template('log-in.html', form=login_form)
        else:
            login_user(user)
            return render_template('index.html', logged_in =current_user.is_authenticated, current_user=current_user, admin=admin)
    return render_template('log-in.html', form=login_form)




@app.route('/add-item', methods =['GET', 'POST'])
@admin_only
@login_required
def add_item():
    add_item_form = AddItem()
    if add_item_form.validate_on_submit():
        new_item = Produts(
            product_name = add_item_form.name.data,
            product_description=add_item_form.description.data,
            product_price=add_item_form.price.data,
            product_category = add_item_form.category.data,
            product_img = f'https://drive.google.com/uc?export=view&id={add_item_form.product_image.data}'
        )
        db.session.add(new_item)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('add-item.html',logged_in = current_user.is_authenticated, current_user=current_user, admin=admin, form= add_item_form)


@app.route('/<choice>/clothing',methods=['GET', 'POST'])
def category(choice):
    cat = choice
    products = Produts.query.filter_by(product_category=choice)

    return render_template('category-clothing.html',logged_in=current_user.is_authenticated, admin= admin, current_user=current_user, choice=cat, products =products)


@app.route('/<int:id>/add-to-cart', methods =['GET', 'POST'])
@login_required
def add_to_cart(id):
    product = Produts.query.get(id)
    new_product = UserCart(
        user=current_user,
        product_name = product.product_name,
        product_description = product.product_description,
        product_price = product.product_price,
        product_img = product.product_img
    )
    db.session.add(new_product)
    db.session.commit()
    return redirect(request.referrer)

@app.route('/<int:id>/user-cart')
@login_required
def user_cart(id):
    chosen_items = UserCart.query.filter_by(user_id = id)
    total_price = sum(item.product_price for item in chosen_items)


    return render_template('user-cart.html', logged_in= current_user.is_authenticated, current_user= current_user, items= chosen_items, price=total_price)

@app.route("/<int:id>/delete-cart-item")
@login_required
def delete_cart_item(id):
    item_to_delete = UserCart.query.get(id)
    db.session.delete(item_to_delete)
    db.session.commit()
    return redirect(request.referrer)

@app.route("/<int:id>/delete-product")
@admin_only
@login_required
def delete_product(id):
    product_to_delete = Produts.query.get(id)
    db.session.delete(product_to_delete)
    db.session.commit()
    return redirect(request.referrer)

@app.route("/<int:id>/edit-product", methods = ["GET", 'POST'])
@admin_only
@login_required
def edit_product(id):
    product_to_edit = Produts.query.get(id)
    edit_form = AddItem(
        name=product_to_edit.product_name,
        description=product_to_edit.product_description,
        price=product_to_edit.product_price,
        category=product_to_edit.product_category,
        product_image = product_to_edit.product_img
    )
    if edit_form.validate_on_submit():
        product_to_edit.product_name= edit_form.name.data
        product_to_edit.product_description= edit_form.description.data
        product_to_edit.product_price = edit_form.price.data
        product_to_edit.product_category = edit_form.category.data
        product_to_edit.product_img= edit_form.product_image.data
        db.session.commit()
        return render_template('index.html', logged_in=current_user.is_authenticated, admin=admin)
    return render_template('edit-product.html', form=edit_form, current_user=current_user, admin=admin,
                           logged_in=current_user.is_authenticated)


#stripe.api_key = "pk_test_51KkD32Ctiqjw9Jj3LO3h5oY53qTTNm3veldk2SnCH1h3Dm2LOGBcITvQv22SOCbjIJVTqOVvUeRlDpcJAQNoiXPA00xTgDzr03"
stripe.api_key= "sk_test_51KkD32Ctiqjw9Jj3sB2F6UuYMGCjcVQjrs3tEkh74qiqH6VqTOkm6wxmelmeNWStL2fOSfOrW23OEWSXLZuuQr9r003VdISh00"


check_out_site = "https://api.sandbox.checkout.com/"



@app.route('/search-results', methods = ["GET","POST"])
def search_results():
    if request.method == "POST":
        item_name = request.form['search']
        products = Produts.query.filter(Produts.product_name.contains(item_name))
        return render_template("search-results.html", products=products, logged_in=current_user.is_authenticated, admin=admin, current_user=current_user)
    return redirect(url_for('user_cart', id = current_user.id, logged_in=current_user.is_authenticated))


@app.route('/create-check-out-session', methods=["GET",'POST'])
@login_required
def check_out():
    cart_items= []
    chosen_items = UserCart.query.filter_by(user_id = current_user.id)
    for item in chosen_items:
        cart_items.append(item.product_name)
    total_price = sum(item.product_price for item in chosen_items)
    session = stripe.checkout.Session.create(
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': (items for items in cart_items),
                },
                'unit_amount': total_price * 100,
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url='https://example.com/success',
        cancel_url='https://example.com/cancel',
    )

    return redirect(session.url, code=303)



#return render_template('check-out.html', logged_in= current_user.is_authenticated, current_user= current_user )

@app.route('/logout')
def log_out():
    logout_user()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
