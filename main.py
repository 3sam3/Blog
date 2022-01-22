from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length
from flask_sqlalchemy import SQLAlchemy
from datetime import date
import functools
from flask_ckeditor import CKEditor, CKEditorField
import os
# need to add postgres support and secret all variables. Also add create delete paths.
# also need to add edit and delete paths to blog posts

app = Flask(__name__)
Bootstrap(app)
ckeditor = CKEditor(app)

app.secret_key = os.environ.get("SECRET_KEY")
app.config['ADMIN_PASSWORD'] = os.environ.get("ADMIN_PASSWORD")
app.config['SITE_WIDTH'] = 800

# Database -----------------------------------------------

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///blog.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(250), nullable=False)
    post_url = db.Column(db.String(250), nullable=False, unique=True)
    category = db.Column(db.Integer, db.ForeignKey('category.id'))


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), unique=True, nullable=False)
    posts = db.relationship('Post', lazy='subquery',
                            backref=db.backref('Category', lazy=True))


db.create_all()


# Forms --------------------------------------------------

class LoginForm(FlaskForm):
    # email = StringField(label='Email', validators=[DataRequired(), Email(message="please use a valid email address")])
    password = PasswordField(label='Password', validators=[DataRequired(), Length(min=8, max=30,
                                                                                  message="please use a password "
                                                                                          "between 8-30 characters")])
    submit = SubmitField(label='Log in')


class BlogSubmission(FlaskForm):
    title = StringField("Blog Post Title", validators=[DataRequired()])
    subtitle = StringField("Subtitle", validators=[DataRequired()])
    author = StringField("Your Name", validators=[DataRequired()])
    body = CKEditorField("Blog Content", validators=[DataRequired()])
    post_url = StringField("Post URL")
    category = StringField("Post Category")
    submit = SubmitField("Submit Post")


# routes -------------------------------------------------

def login_required(fn):
    @functools.wraps(fn)
    def inner(*args, **kwargs):
        if session.get('logged_in'):
            return fn(*args, **kwargs)
        return redirect(url_for('login', next=request.path))

    return inner


@app.route("/")
def hello():
    return render_template('index.html')


@app.route("/home")
def go_home():
    return render_template('home.html')


@app.route("/words")
def go_words():
    everything = Post.query.all()

    return render_template('words.html', all_posts=everything)


@app.route("/pictures")
def go_pictures():
    return render_template('pictures.html')

@app.route("/point_shoot")
def go_photo_dump():
    return render_template('point_shoot.html')


@app.route('/login/', methods=['GET', 'POST'])
def login():
    next_url = request.args.get('next') or request.form.get('next')
    if request.method == 'POST' and request.form.get('password'):
        password = request.form.get('password')
        if password == app.config['ADMIN_PASSWORD']:
            session['logged_in'] = True
            session.permanent = True  # Use cookie to store session.
            flash('You are now logged in.', 'success')
            return redirect(next_url or url_for('hello'))
        else:
            flash('Incorrect password.', 'danger')
    return render_template('login.html', next_url=next_url)


@app.route('/logout/', methods=['GET', 'POST'])
def logout():
    if request.method == 'POST':
        session.clear()
        return redirect(url_for('login'))
    return render_template('logout.html')


@app.route('/create/', methods=['GET', 'POST'])
@login_required
def create():
    blog_entry = BlogSubmission()
    if blog_entry.validate_on_submit() and request.method == "POST":
        if Category.query.filter_by(name=blog_entry.category.data).first() is None:
            new_category = Category(
                name=blog_entry.category.data
            )
            db.session.add(new_category)
        category = Category.query.filter_by(name=blog_entry.category.data).first()
        new_post = Post(
            title=blog_entry.title.data,
            subtitle=blog_entry.subtitle.data,
            body=blog_entry.body.data,
            author=blog_entry.author.data,
            date=date.today().strftime("%B %d, %Y"),
            post_url=blog_entry.post_url.data,
            category=category.id
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("go_words"))
    return render_template('create.html', form=blog_entry)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    post = Post.query.get(post_id)
    edit_form = BlogSubmission(
        title=post.title,
        subtitle=post.subtitle,
        author=post.author,
        body=post.body,
        post_url=post.post_url
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        post.post_url = edit_form.post_url.data
        db.session.commit()
        return redirect(url_for("go_words"))
    return render_template("create.html", form=edit_form, is_edit=True)


@app.route("/delete/<int:post_id>")
@login_required
def delete_post(post_id):
    post_to_delete = Post.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('go_words'))


@app.route("/post/<post_url>")
def show_post(post_url):
    requested_post = Post.query.filter_by(post_url=post_url).first()
    return render_template("post.html", post=requested_post)


if __name__ == "__main__":
    app.run(debug=True)
