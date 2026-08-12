from flask import Flask, session, request, redirect, render_template
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'segredo123'


# ======================
# CONVERSÃO DE VALOR
# ======================
def converter_valor(valor):
    if not valor:
        return 0

    valor = valor.replace('.', '').replace(',', '.')

    try:
        return float(valor)
    except:
        return 0


# ======================
# BANCO DE DADOS
# ======================
def criar_banco():
    conn = sqlite3.connect('crm.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS empresas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            email TEXT,
            senha TEXT,
            tipo TEXT,
            empresa_id INTEGER
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            telefone TEXT,
            interesse TEXT,
            status TEXT,
            valor REAL DEFAULT 0,
            usuario_id INTEGER,
            empresa_id INTEGER,
            data_criacao TEXT,
            data_compra TEXT
        )
    ''')

    conn.commit()

    try:
        cursor.execute("ALTER TABLE clientes ADD COLUMN data_criacao TEXT")
    except:
        pass

    try:
        cursor.execute("ALTER TABLE clientes ADD COLUMN data_compra TEXT")
    except:
        pass

    try:
        cursor.execute("ALTER TABLE empresas ADD COLUMN meta REAL DEFAULT 0")
    except:
        pass

    conn.close()

criar_banco()


# ======================
# HOME
# ======================
@app.route('/')
def home():
    if 'usuario_id' not in session:
        return redirect('/login')
    return redirect('/clientes?aba=dashboard')


# ======================
# LOGIN
# ======================
@app.route('/login', methods=['GET', 'POST'])
def login():
    erro = None

    if request.method == 'POST':
        tipo_login = request.form.get('tipo_login')

        conn = sqlite3.connect('crm.db')
        cursor = conn.cursor()

        if tipo_login == 'admin':
            email = request.form.get('email')
            senha = request.form.get('senha')

            cursor.execute('SELECT id, nome, senha, tipo, empresa_id FROM usuarios WHERE email = ?', (email,))
            usuario = cursor.fetchone()

            if usuario and check_password_hash(usuario[2], senha):
                session['usuario_id'] = usuario[0]
                session['usuario_nome'] = usuario[1]
                session['usuario_tipo'] = usuario[3]
                session['empresa_id'] = usuario[4]
                return redirect('/clientes?aba=dashboard')
            else:
                erro = "Email ou senha inválidos"

        elif tipo_login == 'funcionario':
            nome = request.form.get('nome')
            senha = request.form.get('senha')

            cursor.execute('SELECT id, nome, senha, empresa_id FROM usuarios WHERE nome = ? AND tipo = "Funcionario"', (nome,))
            usuario = cursor.fetchone()

            if usuario and check_password_hash(usuario[2], senha):
                session['usuario_id'] = usuario[0]
                session['usuario_nome'] = usuario[1]
                session['usuario_tipo'] = 'Funcionario'
                session['empresa_id'] = usuario[3]
                return redirect('/clientes?aba=dashboard')
            else:
                erro = "Nome ou senha inválidos"

        conn.close()

    return render_template('login.html', erro=erro)

# ======================
# REGISTRO DE EMPRESA
# ======================
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    erro = None

    if request.method == 'POST':
        empresa = request.form.get('empresa', '').strip()
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')

        # ======================
        # VALIDAÇÕES
        # ======================

        if not empresa or not nome or not email or not senha:
            erro = "Preencha todos os campos."

        elif len(senha) < 6:
            erro = "A senha deve ter no mínimo 6 caracteres."

        elif not any(c.isupper() for c in senha):
            erro = "A senha deve conter pelo menos uma letra maiúscula."

        elif not any(c.islower() for c in senha):
            erro = "A senha deve conter pelo menos uma letra minúscula."

        elif not any(c.isdigit() for c in senha):
            erro = "A senha deve conter pelo menos um número."

        elif not any(not c.isalnum() for c in senha):
            erro = "A senha deve conter pelo menos um caractere especial."

        if erro:
            return render_template('registro.html', erro=erro)

        conn = sqlite3.connect('crm.db')
        cursor = conn.cursor()

        try:
            # ======================
            # VERIFICAR EMAIL
            # ======================
            cursor.execute(
                'SELECT id FROM usuarios WHERE email=?',
                (email,)
            )

            usuario_existente = cursor.fetchone()

            if usuario_existente:
                erro = "Este email já está cadastrado."
                conn.close()
                return render_template('registro.html', erro=erro)

            # ======================
            # CRIAR EMPRESA
            # ======================
            cursor.execute(
                'INSERT INTO empresas (nome) VALUES (?)',
                (empresa,)
            )

            empresa_id = cursor.lastrowid

            # ======================
            # CRIAR ADMIN
            # ======================
            senha_hash = generate_password_hash(senha)

            cursor.execute('''
                INSERT INTO usuarios
                (nome, email, senha, tipo, empresa_id)
                VALUES (?, ?, ?, "Admin", ?)
            ''', (
                nome,
                email,
                senha_hash,
                empresa_id
            ))

            conn.commit()
            conn.close()

            return redirect('/login')

        except Exception as e:
            conn.rollback()
            conn.close()

            print("ERRO NO REGISTRO:", e)

            erro = "Não foi possível criar a conta."

    return render_template('registro.html', erro=erro)


# ======================
# LOGOUT
# ======================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ======================
# CLIENTES + DASHBOARD + FUNCIONÁRIOS
# ======================
@app.route('/clientes', methods=['GET', 'POST'])
def clientes():
    if 'usuario_id' not in session:
        return redirect('/login')

    empresa_id = session.get('empresa_id')
    usuario_id = session.get('usuario_id')
    usuario_tipo = session.get('usuario_tipo')
    aba = request.args.get('aba', 'dashboard')
    vendedor_filtro = request.args.get('vendedor_id')
    busca = request.args.get('busca', '')
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')

    conn = sqlite3.connect('crm.db')
    cursor = conn.cursor()

    # ======================
    # SALVAR META
    # ======================
    if request.method == 'POST' and request.form.get('form_tipo') == 'salvar_meta':

       if usuario_tipo == 'Admin':

          meta = converter_valor(request.form.get('meta'))

          cursor.execute('''
              UPDATE empresas
              SET meta=?
              WHERE id=?
          ''', (meta, empresa_id))

          conn.commit()

       return redirect('/clientes?aba=dashboard')

    # ======================
    # CRIAR CLIENTE
    # ======================
    if request.method == 'POST' and request.form.get('form_tipo') == 'cliente':
        status = request.form.get('status')

        if status == 'Fechado':

            data_informada = request.form.get('data_compra')

            if data_informada:
                data_compra = data_informada
            else:
                data_compra = datetime.now().strftime('%Y-%m-%d')

        else:
            data_compra = None

        cursor.execute('''
            INSERT INTO clientes (
                nome, telefone, interesse, status, valor,
                usuario_id, empresa_id, data_criacao, data_compra
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            request.form.get('nome_cliente'),
            request.form.get('telefone'),
            request.form.get('interesse'),
            request.form.get('status'),
            converter_valor(request.form.get('valor')),
            usuario_id,
            empresa_id,
            datetime.now().strftime('%Y-%m-%d'),
            data_compra
        ))

        conn.commit()
        return redirect('/clientes?aba=clientes')

    # ======================
    # EDITAR CLIENTE
    # ======================
    if request.method == 'POST' and request.form.get('form_tipo') == 'editar_cliente':

        status = request.form.get('status')

        cursor.execute(
            'SELECT data_compra FROM clientes WHERE id=? AND empresa_id=?',
            (request.form.get('id_cliente'), empresa_id)
        )
        registro = cursor.fetchone()
        data_compra_atual = registro[0] if registro else None

        if status == 'Fechado':

            data_informada = request.form.get('data_compra')

            if data_informada:
                data_compra = data_informada
            else:
                data_compra = data_compra_atual or datetime.now().strftime('%Y-%m-%d')

        else:
            data_compra = None

        if usuario_tipo == 'Admin':
            cursor.execute('''
                UPDATE clientes SET
                    nome=?,
                    telefone=?,
                    interesse=?,
                    status=?,
                    valor=?,
                    data_compra=?
                WHERE id=? AND empresa_id=?
            ''', (
                request.form.get('nome'),
                request.form.get('telefone'),
                request.form.get('interesse'),
                request.form.get('status'),
                converter_valor(request.form.get('valor')),
                data_compra,
                request.form.get('id_cliente'),
                empresa_id
            ))
        else:
            cursor.execute('''
                UPDATE clientes SET
                    nome=?,
                    telefone=?,
                    interesse=?,
                    status=?,
                    valor=?,
                    data_compra=?
                WHERE id=? AND empresa_id=? AND usuario_id=?
            ''', (
                request.form.get('nome'),
                request.form.get('telefone'),
                request.form.get('interesse'),
                request.form.get('status'),
                converter_valor(request.form.get('valor')),
                data_compra,
                request.form.get('id_cliente'),
                empresa_id,
                usuario_id
            ))

        conn.commit()
        return redirect('/clientes?aba=clientes')

    # ======================
    # TRANSFERIR CLIENTE (NOVO)
    # ======================
    if request.method == 'POST' and request.form.get('form_tipo') == 'transferir_cliente':
        if usuario_tipo == 'Admin':
            cursor.execute('''
                UPDATE clientes
                SET usuario_id=?
                WHERE id=? AND empresa_id=?
            ''', (
                request.form.get('novo_vendedor_id'),
                request.form.get('id_cliente'),
                empresa_id
            ))

            conn.commit()

        return redirect('/clientes?aba=clientes')

    # ======================
    # CRIAR FUNCIONÁRIO
    # ======================
    if request.method == 'POST' and request.form.get('form_tipo') == 'funcionario':
        nome = request.form.get('nome_funcionario')
        senha = generate_password_hash(request.form.get('senha_funcionario'))

        cursor.execute('''
            INSERT INTO usuarios (nome, senha, tipo, empresa_id)
            VALUES (?, ?, "Funcionario", ?)
        ''', (nome, senha, empresa_id))

        conn.commit()
        return redirect('/clientes?aba=funcionarios')

    # ======================
    # EDITAR FUNCIONÁRIO
    # ======================
    if request.method == 'POST' and request.form.get('form_tipo') == 'editar_funcionario':
        nome = request.form.get('nome_funcionario')
        nova_senha = request.form.get('senha_funcionario')
        id_funcionario = request.form.get('id_funcionario')

        if nova_senha:
            senha_hash = generate_password_hash(nova_senha)
            cursor.execute('''
                UPDATE usuarios
                SET nome=?, senha=?
                WHERE id=? AND empresa_id=? AND tipo="Funcionario"
            ''', (nome, senha_hash, id_funcionario, empresa_id))
        else:
            cursor.execute('''
                UPDATE usuarios
                SET nome=?
                WHERE id=? AND empresa_id=? AND tipo="Funcionario"
            ''', (nome, id_funcionario, empresa_id))

        conn.commit()
        return redirect('/clientes?aba=funcionarios')

    # ======================
    # LISTAR VENDEDORES (NOVO)
    # ======================
    cursor.execute('''
        SELECT id, nome
        FROM usuarios
        WHERE empresa_id=? AND tipo="Funcionario"
    ''', (empresa_id,))
    vendedores = cursor.fetchall()

    # ======================
    # LISTAR CLIENTES (COM FILTROS)
    # ======================
    sql = '''
        SELECT id, nome, telefone, interesse, status,
               valor, usuario_id, data_compra
        FROM clientes
        WHERE empresa_id=?
    '''

    params = [empresa_id]

    # Funcionário vê apenas seus clientes
    if usuario_tipo != 'Admin':
        sql += ' AND usuario_id=?'
        params.append(usuario_id)

    # Filtro por vendedor
    elif vendedor_filtro:
        sql += ' AND usuario_id=?'
        params.append(vendedor_filtro)

    # Pesquisa por nome
    if busca:
        sql += ' AND nome LIKE ?'
        params.append(f'%{busca}%')

    # Filtro por data de venda
    if data_inicio:
        sql += ' AND data_compra >= ?'
        params.append(data_inicio)

    if data_fim:
        sql += ' AND data_compra <= ?'
        params.append(data_fim)

    sql += ' ORDER BY id DESC'

    cursor.execute(sql, params)
    clientes = cursor.fetchall()

    # ======================
    # META
    # ======================
    cursor.execute('''
        SELECT meta
        FROM empresas
        WHERE id=?
    ''', (empresa_id,))

    resultado_meta = cursor.fetchone()

    meta = resultado_meta[0] if resultado_meta and resultado_meta[0] else 0
    
    # ======================
    # FATURAMENTO
    # ======================
    cursor.execute('SELECT SUM(valor) FROM clientes WHERE status="Fechado" AND empresa_id=?', (empresa_id,))
    faturamento = cursor.fetchone()[0] or 0

    # ======================
    # DASHBOARD
    # ======================
    cursor.execute('''
        SELECT 
            strftime('%m', data_criacao),
            status,
            COUNT(*),
            COALESCE(SUM(valor),0)
        FROM clientes
        WHERE empresa_id=? AND data_criacao IS NOT NULL
        GROUP BY strftime('%m', data_criacao), status
    ''', (empresa_id,))

    dados = cursor.fetchall()

    meses = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']

    leads_m = [0]*12
    neg_m = [0]*12
    fech_m = [0]*12
    perd_m = [0]*12
    faturamento_m = [0] * 12
    vendas_m = [0] * 12

    for mes, status, total, valor_total in dados:
        if not mes:
            continue

        i = int(mes) - 1

        if status == 'Lead':
            leads_m[i] = total
        elif status == 'Negociação':
            neg_m[i] = total
        elif status == 'Fechado':
            fech_m[i] = total
            faturamento_m[i] = valor_total
            vendas_m[i] = total
        elif status == 'Perdido':
            perd_m[i] = total

    # ======================
    # FATURAMENTO MENSAL
    # ======================
    cursor.execute('''
        SELECT
            strftime('%m', data_compra) as mes,
            COUNT(*) as vendas,
            COALESCE(SUM(valor), 0) as faturado
        FROM clientes
        WHERE status="Fechado"
          AND empresa_id=?
          AND data_compra IS NOT NULL
        GROUP BY mes
    ''', (empresa_id,))

    dados_faturamento = cursor.fetchall()

    fat_mensal = [0] * 12
    vendas_mensal = [0] * 12
    carros_mensal = [0] * 12

    for mes, vendas, faturado in dados_faturamento:

        if not mes:
            continue

        i = int(mes) - 1

        fat_mensal[i] = faturado
        vendas_mensal[i] = vendas
        carros_mensal[i] = vendas

    # ======================
    # MODELOS MAIS VENDIDOS
    # ======================
    cursor.execute('''
        SELECT interesse, COUNT(*)
        FROM clientes
        WHERE status="Fechado"
          AND empresa_id=?
          AND interesse IS NOT NULL
          AND interesse != ''
        GROUP BY interesse
        ORDER BY COUNT(*) DESC
    ''', (empresa_id,))

    dados_modelos = cursor.fetchall()

    modelos_labels = []
    modelos_qtd = []

    for modelo, qtd in dados_modelos:
        modelos_labels.append(modelo)
        modelos_qtd.append(qtd)

    # ======================
    # RANKING
    # ======================
    cursor.execute('''
        SELECT u.nome,
               COUNT(c.id),
               COALESCE(SUM(c.valor), 0)
        FROM clientes c
        JOIN usuarios u ON u.id = c.usuario_id
        WHERE c.status="Fechado" AND c.empresa_id=?
        GROUP BY u.nome
        ORDER BY 3 DESC
    ''', (empresa_id,))

    ranking = cursor.fetchall()

    # ======================
    # DESEMPENHO POR VENDEDOR
    # ======================
    cursor.execute('''
        SELECT
            u.nome,

            COUNT(CASE WHEN c.status="Fechado" THEN 1 END),

            COALESCE(SUM(
                CASE
                    WHEN c.status="Fechado"
                    THEN c.valor
                    ELSE 0
                END
            ),0),

            COUNT(CASE WHEN c.status="Lead" THEN 1 END),
            COUNT(CASE WHEN c.status="Negociação" THEN 1 END),
            COUNT(CASE WHEN c.status="Perdido" THEN 1 END)

        FROM usuarios u

        LEFT JOIN clientes c
            ON c.usuario_id = u.id

        WHERE u.empresa_id=?

        GROUP BY u.nome
    ''', (empresa_id,))

    dados_vendedores = cursor.fetchall()

    dados_grafico_vendedores = {}

    for row in dados_vendedores:
        nome = row[0]

        dados_grafico_vendedores[nome] = {
            'fechado': row[1],
            'faturamento': row[2],
            'lead': row[3],
            'negociacao': row[4],
            'perdido': row[5]
        }

    # ======================
    # FUNCIONÁRIOS
    # ======================
    cursor.execute('''
        SELECT id, nome
        FROM usuarios
        WHERE tipo="Funcionario" AND empresa_id=?
    ''', (empresa_id,))

    funcionarios = cursor.fetchall()

    conn.close()

    nomes_vendedores = []
    faturamento_vendedor = []
    vendas_vendedor = []
    lead_vendedor = []
    neg_vendedor = []
    perd_vendedor = []
    fechado_vendedor = []

    for r in ranking:
        nomes_vendedores.append(r[0])

        vendas_vendedor.append(r[1])

        faturamento_vendedor.append(float(r[2] or 0))

        # BUSCAR DADOS INDIVIDUAIS
        dados = dados_grafico_vendedores.get(r[0], {})

        lead_vendedor.append(dados.get('lead', 0))

        neg_vendedor.append(dados.get('negociacao', 0))

        perd_vendedor.append(dados.get('perdido', 0))

        fechado_vendedor.append(dados.get('fechado', 0))

    return render_template(
        'clientes.html',
        clientes=clientes,
        aba=aba,
        faturamento=faturamento,
        meta=meta,

        meses=meses,
        leads_m=leads_m,
        neg_m=neg_m,
        fech_m=fech_m,
        perd_m=perd_m,

        modelos_labels=modelos_labels,
        modelos_qtd=modelos_qtd,

        ranking=ranking,
        funcionarios=funcionarios,
        vendedores=vendedores,
        vendedor_filtro=vendedor_filtro,
        busca=busca,
        data_inicio=data_inicio,
        data_fim=data_fim,
        
        fat_mensal=fat_mensal,
        vendas_mensal=vendas_mensal,
        carros_mensal=carros_mensal,
        nomes_vendedores=nomes_vendedores,
        vendas_vendedor=vendas_vendedor,
        faturamento_vendedor=faturamento_vendedor,
        lead_vendedor=lead_vendedor,
        neg_vendedor=neg_vendedor,
        perd_vendedor=perd_vendedor,
        fechado_vendedor=fechado_vendedor,
        dados_grafico_vendedores=dados_grafico_vendedores,
    )

# ======================
# EXCLUIR FUNCIONÁRIO
# ======================
@app.route('/excluir_funcionario/<int:id>')
def excluir_funcionario(id):
    if 'usuario_id' not in session:
        return redirect('/login')

    empresa_id = session.get('empresa_id')

    conn = sqlite3.connect('crm.db')
    cursor = conn.cursor()

    cursor.execute('''
        DELETE FROM usuarios
        WHERE id=? AND empresa_id=? AND tipo="Funcionario"
    ''', (id, empresa_id))

    conn.commit()
    conn.close()

    return redirect('/clientes?aba=funcionarios')


# ======================
# RUN
# ======================
if __name__ == '__main__':
    app.run(debug=True)
