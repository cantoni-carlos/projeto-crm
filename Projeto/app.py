from flask import Flask, session, request, redirect, render_template
import sqlite3

app = Flask(__name__)
app.secret_key = 'segredo123'


# ======================
# CRIAR BANCO
# ======================
def criar_banco():
    conn = sqlite3.connect('clientes.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            email TEXT,
            senha TEXT,
            tipo TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            telefone TEXT,
            interesse TEXT,
            status TEXT,
            usuario_id INTEGER
        )
    ''')

    conn.commit()
    conn.close()

criar_banco()


# ======================
# HOME
# ======================
@app.route('/')
def home():
    if 'usuario_id' not in session:
        return redirect('/login')
    return redirect('/clientes')


# ======================
# REGISTRO
# ======================
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        tipo = 'Admin'

        conn = sqlite3.connect('clientes.db')
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO usuarios (nome, email, senha, tipo)
            VALUES (?, ?, ?, ?)
        ''', (nome, email, senha, tipo))

        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template('registro.html')


# ======================
# LOGIN
# ======================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        conn = sqlite3.connect('clientes.db')
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, nome, tipo FROM usuarios
            WHERE email = ? AND senha = ?
        ''', (email, senha))

        usuario = cursor.fetchone()
        conn.close()

        if usuario:
            session['usuario_id'] = usuario[0]
            session['usuario_nome'] = usuario[1]
            session['usuario_tipo'] = usuario[2]
            return redirect('/clientes')
        else:
            return "Login inválido"

    return render_template('login.html')


# ======================
# LOGOUT
# ======================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ======================
# CLIENTES (LISTAR + CADASTRAR)
# ======================
@app.route('/clientes', methods=['GET', 'POST'])
def listar_clientes():
    if 'usuario_id' not in session:
        return redirect('/login')

    usuario_id = session['usuario_id']

    conn = sqlite3.connect('clientes.db')
    cursor = conn.cursor()

    # 👉 CADASTRAR CLIENTE
    if request.method == 'POST':
        nome = request.form['nome']
        telefone = request.form['telefone']
        interesse = request.form['interesse']
        status = request.form['status']

        cursor.execute('''
            INSERT INTO clientes (nome, telefone, interesse, status, usuario_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (nome, telefone, interesse, status, usuario_id))

        conn.commit()
        conn.close()
        return redirect('/clientes')

    # 👉 FILTRO
    status = request.args.get('status')

    if status:
        cursor.execute('''
            SELECT id, nome, telefone, interesse, status
            FROM clientes
            WHERE status = ? AND usuario_id = ?
        ''', (status, usuario_id))
    else:
        cursor.execute('''
            SELECT id, nome, telefone, interesse, status
            FROM clientes
            WHERE usuario_id = ?
        ''', (usuario_id,))

    dados = cursor.fetchall()

    # 👉 DASHBOARD
    def contar(tipo):
        cursor.execute('''
            SELECT COUNT(*) FROM clientes
            WHERE status = ? AND usuario_id = ?
        ''', (tipo, usuario_id))
        return cursor.fetchone()[0]

    leads = contar('Lead')
    negociacao = contar('Negociação')
    fechados = contar('Fechado')
    perdidos = contar('Perdido')

    conn.close()

    return render_template(
        'clientes.html',
        clientes=dados,
        leads=leads,
        negociacao=negociacao,
        fechados=fechados,
        perdidos=perdidos
    )


# ======================
# EXCLUIR
# ======================
@app.route('/excluir/<int:id>')
def excluir(id):
    if 'usuario_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('clientes.db')
    cursor = conn.cursor()

    cursor.execute('DELETE FROM clientes WHERE id = ?', (id,))

    conn.commit()
    conn.close()

    return redirect('/clientes')


# ======================
# EDITAR
# ======================
@app.route('/editar/<int:id>')
def editar(id):
    if 'usuario_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('clientes.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM clientes WHERE id = ?', (id,))
    cliente = cursor.fetchone()

    conn.close()

    return render_template('editar.html', cliente=cliente)


# ======================
# ATUALIZAR
# ======================
@app.route('/atualizar/<int:id>', methods=['POST'])
def atualizar(id):
    if 'usuario_id' not in session:
        return redirect('/login')

    nome = request.form['nome']
    telefone = request.form['telefone']
    interesse = request.form['interesse']
    status = request.form['status']

    conn = sqlite3.connect('clientes.db')
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE clientes
        SET nome = ?, telefone = ?, interesse = ?, status = ?
        WHERE id = ?
    ''', (nome, telefone, interesse, status, id))

    conn.commit()
    conn.close()

    return redirect('/clientes')


# ======================
# RUN
# ======================
if __name__ == '__main__':
    app.run(debug=True)