#para pdf
#path_wkhtmltopdf = 'venv\\include\\wkhtmltopdf\\bin\\wkhtmltopdf.exe'
#config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
resultado = {}
import functools
import datetime

from werkzeug.security import generate_password_hash, check_password_hash

from flask import Flask, render_template, flash, request, redirect, url_for, jsonify, session, send_file, current_app, g, make_response
import utils
from db import get_db, close_db
import os
import secrets
import string
from sqlite3 import Error
import yagmail as yagmail
import boto3


app = Flask(__name__)
s3 = boto3.client('s3',
                    aws_access_key_id='AKIAX2G5FWLKECAQ3DOT',
                    aws_secret_access_key= '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',
                    )
app.secret_key = os.urandom(24)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=('POST','GET'))
def login():
    return render_template('login.html')

@app.route('/validacion', methods=('GET', 'POST'))
def validacion():
    try:
        if g.user:
            return redirect( url_for( 'dashboard' ) )
        if request.method == 'POST':
            db = get_db()
            error = None
            username = request.form['username']
            password = request.form['password']

            if not username:
                error = 'Debes ingresar el usuario'
                flash( error )
                return render_template( 'login.html' )

            if not password:
                error = 'Contraseña requerida'
                flash( error )
                return render_template( 'login.html' )

            user = db.execute('SELECT * FROM usuarios WHERE usuario = ?',(username,)).fetchone()

            if user is None:
                error = 'Usuario o contraseña inválidos'
            else:
                if check_password_hash(user[2],password):
                    session.clear()
                    session['usuario_ID'] = user[0]
                    session['username'] = user[1]
                    session['contraseña'] = user[2]
                    session['correo'] = user[3]
                    session['nombre'] = user[4]
                    session['apellido'] = user[5]
                    return redirect(url_for('dashboard'))
            error = 'Usuario o contraseña inválidos'
            flash( error )
            
        return render_template( 'login.html' )    
    except:
        return render_template( 'login.html' )  


def login_required(view):
    @functools.wraps( view )
    def wrapped_view():
        if g.user is None:
            return redirect( url_for( 'login' ) )
        return view( )
    return wrapped_view 
    
@app.route('/perfil')
@login_required
def userInf():
    return render_template('userInformation.html')


@app.route('/CrearCuenta' , methods=('GET', 'POST'))
def registro():
    try:
        if request.method == 'POST':
            name = request.form['name']
            lastname = request.form['lastname']
            username = request.form['user']
            password = request.form['password']
            confirmPass = request.form['confirmPass']
            email = request.form['email']
            active = True
            error = None
            db = get_db() #Conectarse a la base de datos

            if not utils.isUsernameValid( username ):
                error = "El usuario debe ser alfanumerico o incluir solo '.','_','-'"
                flash( error )
                return render_template( 'createUser.html' )

            if password != confirmPass:
                error = "Las contraseñas no coinciden, por favor verifiquelas"
                flash( error )
                return render_template( 'createUser.html' )    

            if not utils.isPasswordValid( password ):
                error = 'La contraseña debe contenir al menos una minúscula, una mayúscula, un número y 8 caracteres'
                flash( error )
                return render_template( 'createUser.html' )

            if not utils.isEmailValid( email ):
                error = 'Correo invalido'
                flash( error )
                return render_template( 'createUser.html' )

            #Preguntar si el correo no ha sido registrado anteriormente
            if db.execute( 'SELECT usuario_ID FROM usuarios WHERE correo = ?', (email,) ).fetchone() is not None:
                error = 'El correo ya existe'.format( email )
                flash( error )
                return render_template( 'createUser.html' )

            #Preguntar si el usuario existe
            if db.execute( 'SELECT usuario_ID FROM usuarios WHERE usuario = ?', (username,) ).fetchone() is not None:
                error = 'El usuario ya existe'.format( username )
                flash( error )
                return render_template( 'createUser.html' )    

            hashPassword = generate_password_hash(password)
            db.execute(
                'INSERT INTO usuarios (usuario, contraseña, correo, nombre, apellido, activo) VALUES (?,?,?,?,?,?)',
                (username, hashPassword, email, name, lastname, active)
            )
            db.commit()
            close_db()
            # yag = yagmail.SMTP('micuenta@gmail.com', 'clave') #modificar con tu informacion personal
            # yag.send(to=email, subject='Activa tu cuenta',
            #        contents='Bienvenido, usa este link para activar tu cuenta ')
            flash( 'El usuario ha sido creado con exito' )
            return render_template( 'login.html', user_created="El usuario ha sido creado con exito" )
        return render_template( 'createUser.html' )
    except:
        return render_template( 'createUser.html' )


@app.route('/recuperarCuenta')
def forgetPassword():
    return render_template('forgetPassword.html')



@app.route('/sendEmail', methods=('GET', 'POST'))
def sendEmail():
    try:
        if request.method == 'POST':
            username = request.form['user']
            email = request.form['email']
            db = get_db() #Conectarse a la base de datos
            alphabet = string.ascii_letters + string.digits
            password = ''.join(secrets.choice(alphabet) for i in range(8))
            #Preguntar si el correo no ha sido registrado anteriormente
            if db.execute( 'SELECT usuario_ID FROM usuarios WHERE usuario = ? AND correo = ?',(username, email)).fetchone() is not None:
                yag = yagmail.SMTP('misiontic2020@gmail.com', 'Uninorte2020!') #modificar con tu informacion personal
                yag.send(to=email, subject='Recupera tu cuenta',
                contents='¡Hola!, usa esta clave temporal para entrar a tu cuenta. \n\nClave temporal: '+password+'\n\nGracias por utilizar nuestros servicios!\nAtentamente,\nEquipo Grupo A Blogs')
                hashPassword = generate_password_hash(password)
                db.execute('UPDATE usuarios SET contraseña = ? WHERE correo = ?' ,(hashPassword, email))
                db.commit()
            close_db()
            return render_template('login.html')
    except:
        flash( 'Se ha producido un error, intente de nuevo en unos minutos' )
        return render_template( 'forgetPassword.html' )

@app.route('/cambiarClave')
@login_required
def cambiarClave():
    return render_template('changePassword.html')

@app.route('/newPassword', methods=('GET', 'POST') )
@login_required
def newPassword():
    try:
        if request.method == 'POST':
            oldPass = request.form['oldPass']
            newPass = request.form['newPass']
            confirmPass = request.form['confirmPass']
            db = get_db()
            if check_password_hash(session['contraseña'],oldPass) :
                if newPass == confirmPass:
                    if not utils.isPasswordValid( newPass ):
                        error = 'La contraseña debe contener al menos una minúscula, una mayúscula, un número y 8 caracteres'
                        flash( error )
                        return render_template( 'cambiarClave.html' )
                    hashPassword = generate_password_hash(confirmPass)
                    db.execute( 'UPDATE usuarios SET contraseña = ? WHERE correo = ?',(hashPassword, session['correo']))
                    db.commit()
                    flash("Contraseña cambiada con exito")
                    #session.clear()
                    #return redirect('login.html')
                else:
                    flash('Las contraseñas no concuerdan')
                    return render_template('changePassword.html')
            else:
                flash('Las contraseña actual no concuerdan')
                return render_template('changePassword.html')
            close_db()
            return render_template( 'changePassword.html' )
    except:
        #flash( 'Se ha producido un error, intente de nuevo en unos minutos' )
        return render_template( 'changePassword.html' )

@app.route('/dashboard')
@login_required
def dashboard():
        db = get_db()
        blogs_re = db.execute('SELECT * FROM blogs WHERE privado= 0').fetchall()
        blogs = db.execute('SELECT * FROM blogs WHERE privado= 0').fetchall()
        comments = db.execute('SELECT b.blog_ID FROM comentarios c, blogs b WHERE  b.blog_ID = c.blog_ID').fetchall()
        close_db()
        diccionario_comentarios = dict()
        for comentario in comments:
            for i in range(len(comments)):
                if comentario == i:
                    if diccionario_comentarios[comentario] in diccionario_comentarios:
                        diccionario_comentarios[comentario] += 1
                    else: 
                        diccionario_comentarios[comentario] = 1
        
        return render_template('dashboard.html', blog = blogs,blog_re = blogs_re, comentarios = diccionario_comentarios)

@app.route('/myBlogs')
@login_required
def myBlogs():
        db = get_db()
        blogs = db.execute('SELECT * FROM blogs WHERE usuario_ID= ?',(session["usuario_ID"],)).fetchall()
        return render_template('myBlogs.html', blog = blogs)

@app.route('/verblog', methods=['GET'])
@login_required
def verBlog():
    blog_ID = request.args.get('blog_ID')
    session["blog_ID"] = blog_ID
    db = get_db()
    blog = db.execute('SELECT * FROM blogs WHERE blog_ID=?',(blog_ID,)).fetchone()
    autores = db.execute('SELECT usuario FROM usuarios WHERE usuario_ID=?',(blog[6],)).fetchone()
    comments = db.execute('SELECT c.comentario, u.usuario, c.fechaComentario FROM comentarios c, blogs b, usuarios u WHERE  b.blog_ID = c.blog_ID AND c.usuario_ID = u.usuario_ID AND b.blog_ID = ?',(blog_ID)).fetchall()
    return render_template( 'VerBlog.html', blog = blog, autor = autores, comentarios = comments)

@app.route('/create')
@login_required
def create():
    return render_template( 'createBlog.html' )

@app.route('/edit')	
@login_required	
def editBlog():	
    blog_ID = request.args.get('blog_ID')
    session["blog_ID"] = blog_ID
    db = get_db()
    blog = db.execute('SELECT * FROM blogs b, etiquetas e WHERE blog_ID= ? AND e.etiqueta_ID = b.etiqueta_ID',(blog_ID,)).fetchone()
    return render_template('editBlog.html', blog = blog)

@app.route('/actionEdit', methods=('GET', 'POST'))	
@login_required	
def actionEdit():	
    if request.method == 'POST':
        blog_ID = session['blog_ID']
        titulo = request.form['titulo']
        #img = request.files['imagenes']
        cuerpo = request.form['cuerpo']
        etiqueta = request.form['etiqueta']
        etiqueta = str.lower(etiqueta)
        if request.form['privacidad'] == "privado":
            privado = True
        else:
            privado = False 
        
        db = get_db()

        if titulo is None:
                error = "debe ingresar el titulo del blog"
                flash( error )
                return render_template( 'create.html' )

        if cuerpo is None:
            error = "debe ingresar el cuerpo del blog"
            flash( error )
            return render_template( 'create.html' )

        if privado is None:
            error = "debe seleccionar la privacidad del blog"
            flash( error )
            return render_template( 'create.html' )
            
        tag = db.execute('SELECT etiqueta_ID FROM etiquetas WHERE nombre = ?',(etiqueta,)).fetchone()

        if tag is None:
            db.execute('INSERT INTO etiquetas (nombre) VALUES (?)',(etiqueta,))
            tag = db.execute('SELECT etiqueta_ID FROM etiquetas WHERE nombre = ?',(etiqueta,)).fetchone()
            etiqueta = tag[0]
        else:
            etiqueta = tag[0]
        """
        if img is not None:
            filename =  img.filename
            img.save(filename)
            response = s3.upload_file(
                Bucket = "blog-uninorte-2",
                Filename=filename,
                key = filename)
            blog = db.execute('UPDATE blogs SET titulo =?, imagen = ?, cuerpo = ?, privado = ? WHERE blog_ID=?',(titulo, filename, cuerpo, privado, etiqueta, blog_ID,))
        else:"""

        db.execute('UPDATE blogs SET titulo =?, cuerpo = ?, privado = ? WHERE blog_ID=?',(titulo, cuerpo, privado, blog_ID,))
        db.commit()
        close_db()
        return redirect( 'myBlogs')

    return render_template('editBlog.html') 

@app.route('/actionDelete', methods=('GET', 'POST'))	
@login_required	
def actionDelete():	
    if request.method == 'GET':
        blog_ID = request.args.get('blog_ID')
        db = get_db()
        blog = db.execute('DELETE FROM blogs WHERE blog_ID= ? ',(blog_ID, ))
        db.commit()
        close_db()
        return redirect( 'myBlogs')
        
    return render_template('myBlogs.html')
    

@app.route('/actionComment', methods=('GET', 'POST'))
@login_required
def actionComment():
    try:
        if request.method == 'POST':
            blog_ID = session["blog_ID"]
            usuario_ID = session['usuario_ID']
            comentario = request.form['comentariover']
            
            fechaComentario = datetime.date.today()
            db = get_db()
            db.execute('INSERT INTO comentarios (blog_ID, comentario, usuario_ID, fechaComentario) VALUES (?,?,?,?)',(blog_ID, comentario, usuario_ID, fechaComentario))
            blog = db.execute('SELECT * FROM blogs WHERE blog_ID=?',(blog_ID,)).fetchone()
            autores = db.execute('SELECT usuario FROM usuarios WHERE usuario_ID=?',(blog[6],)).fetchone()
            comments = db.execute('SELECT c.comentario, u.usuario, c.fechaComentario FROM comentarios c, blogs b, usuarios u WHERE  b.blog_ID = c.blog_ID AND c.usuario_ID = u.usuario_ID AND b.blog_ID = ?',(blog_ID)).fetchall()
            db.commit()
            close_db()
            #return redirect('dashboard')
            #return render_template( 'VerBlog')
            return render_template( 'VerBlog.html' ,blog = blog, autor = autores, comentario = comments)
        return render_template( 'VerBlog.html' )
    except:
        return render_template( 'VerBlog.html' )


@app.route('/createBlog', methods=('GET', 'POST'))
@login_required
def createBlog():
    try:
        if request.method == 'POST':
            titulo = request.form['titulo']
            img = request.files['imagenes']
            cuerpo = request.form['cuerpo']
            etiqueta = request.form['etiqueta']
            etiqueta = str.lower(etiqueta)
            usuarioCreador = session['usuario_ID']
            likes = 0
            fechaCreacion = datetime.date.today()
            error = None
            if img:
                filename =  img.filename
                img.save(filename)
                response = s3.upload_file(
                    Bucket = "blog-uninorte-2",
                    Filename=filename,
                    Key = filename
                )
            db = get_db() #Conectarse a la base de datos
            if request.form['privacidad'] == "privado":
                privado = True
            else:
                privado = False 
            
            if titulo is None:
                error = "debe ingresar el titulo del blog"
                flash( error )
                return render_template( 'create.html' )

            if cuerpo is None:
                error = "debe ingresar el cuerpo del blog"
                flash( error )
                return render_template( 'create.html' )

            if privado is None:
                error = "debe seleccionar la privacidad del blog"
                flash( error )
                return render_template( 'create.html' )
            
            tag = db.execute('SELECT etiqueta_ID FROM etiquetas WHERE nombre = ?',(etiqueta,)).fetchone()

            if tag is None:
                db.execute('INSERT INTO etiquetas (nombre) VALUES (?)',(etiqueta,))
                tag = db.execute('SELECT etiqueta_ID FROM etiquetas WHERE nombre = ?',(etiqueta,)).fetchone()
                etiqueta = tag[0]
            else:
                etiqueta = tag[0]
            
            db.execute(
                'INSERT INTO blogs (titulo, imagen, cuerpo, privado, etiqueta_ID, usuario_ID, likes, fecha) VALUES (?,?,?,?,?,?,?,?)',
                (titulo, filename, cuerpo, privado, etiqueta, usuarioCreador, likes, fechaCreacion)
            )
            db.commit()
            close_db()
            return render_template( 'dashboard.html', blog_created="El blog ha sido creado con exito" )
        return render_template( 'createBlog.html' )
    except:
        return render_template( 'createBlog.html' )   

@app.route('/search', methods=('GET','POST'))      
@login_required      
def search():
    if request.method == 'GET':
        db = get_db() #Conectarse a la base de datos
        blogs_re = db.execute('SELECT * FROM blogs WHERE privado= 0').fetchall()
        busqueda = request.args.get('buscar')  
        comments = db.execute('SELECT b.blog_ID FROM comentarios c, blogs b WHERE  b.blog_ID = c.blog_ID').fetchall()
        q = f"SELECT * FROM blogs b, etiquetas e WHERE (titulo LIKE '%{busqueda}%' OR cuerpo LIKE '%{busqueda}%' OR e.nombre LIKE '%{busqueda}%') AND (privado = 0) AND b.etiqueta_ID = e.etiqueta_ID"
        resultados = db.execute(q).fetchall()
        diccionario_comentarios = dict()
        for comentario in comments:
            for i in range(len(comments)):
                if comentario == i:
                    if diccionario_comentarios[comentario] in diccionario_comentarios:
                        diccionario_comentarios[comentario] += 1
                    else: 
                        diccionario_comentarios[comentario] = 1
        close_db()
        if resultados is None:
            resultados = ["No se encuentra algún resultado","No se encuentra algún resultado"]
        return render_template('dashboard.html', blog = resultados, blog_re = blogs_re, comentarios = diccionario_comentarios )

    return render_template('dashboard.html')

@app.before_request
def load_logged_in_user():
    user_id = session.get( 'usuario_ID' )
    if user_id is None:	
            g.user = None	
    else:	
        g.user = get_db().execute('SELECT * FROM usuarios WHERE usuario_ID = ?', (user_id,)).fetchone()	

@app.route( '/logout' )	
def logout():	
    session.clear()	
    return redirect( url_for( 'login' ) )	

if __name__ == '__main__':	
    app.run(debug=True,port=80)

