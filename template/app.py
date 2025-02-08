from flask import Flask, render_template, request, redirect, url_for, send_file, send_from_directory, jsonify
import csv
import json
import os
import uuid
from datetime import datetime
from dateutil.relativedelta import relativedelta

app = Flask(__name__)

# Diretório de uploads (dentro de "static/uploads")
UPLOAD_FOLDER = os.path.join(os.getcwd(), "static/uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER



# Arquivo JSON para armazenar bens
BENS_FILE = "bens.json"

# Remover caracteres não numérico
def tratar_valor(valor):
    valor = valor.replace('R$', '').replace('.', '').replace(',', '.')
    return float(valor)

# Função para limpar e formatar valores
def limpar_valor(valor_str):
    if not valor_str:
        return 0
    valor_str = valor_str.replace("R$", "").strip()  # Remove o "R$" e espaços
    valor_str = valor_str.replace(".", "")  # Remove os pontos (separadores de milhar)
    valor_str = valor_str.replace(",", ".")  # Substitui a vírgula por ponto (separador decimal)
    
    try:
        return float(valor_str)  # Converte para float
    except ValueError:
        return 0  # Retorna 0 caso não consiga converter



# Função para carregar bens do JSON com tratamento de erro
def carregar_bens():
    if os.path.exists(BENS_FILE):
        try:
            with open(BENS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            # Retorna lista vazia se o JSON estiver corrompido
            return []
    return []

# Função para salvar bens no JSON
def salvar_bens(bens):
    with open(BENS_FILE, "w", encoding="utf-8") as f:
        json.dump(bens, f, ensure_ascii=False, indent=4)

# Carrega os bens ao iniciar a aplicação
bens = carregar_bens()

def limpar_valor(valor_str):
    if not valor_str:
        return 0
    valor_str = valor_str.replace("R$", "").strip()
    valor_str = valor_str.replace(".", "").replace(",", ".")
    try:
        return float(valor_str)
    except ValueError:
        return 0

    # Remove "R$", espaços e converte separador de milhares e decimal
    valor_str = valor_str.replace("R$", "").strip()
    valor_str = valor_str.replace(".", "").replace(",", ".")
    try:
        return float(valor_str)
    except ValueError:
        return 0

# --- Funções de Cálculo ---
def calcular_depreciacao_acumulada(valor_compra, vida_util, meses_passados):
    vida_util_meses = vida_util * 12
    if vida_util_meses > 0:
        meses_validos = min(meses_passados, vida_util_meses)
        depreciacao_mensal = valor_compra / vida_util_meses
        return depreciacao_mensal * meses_validos
    return 0

def calcular_valor_uso_mensal(custo_total, meses_passados):
    if meses_passados > 0:
        return custo_total / meses_passados
    return 0

def calcular_vida_util_restante(data_compra, vida_util):
    if not data_compra:
        return 0
    vida_util_meses = vida_util * 12
    hoje = datetime.today().date()
    meses_passados = (hoje.year - data_compra.year) * 12 + (hoje.month - data_compra.month)
    return max(vida_util_meses - meses_passados, 0)

def calcular_tempo_vida_total(data_compra):
    if not data_compra:
        return 0
    hoje = datetime.today().date()
    return (hoje.year - data_compra.year) * 12 + (hoje.month - data_compra.month)

def calcular_garantia_restante_por_meses(garantia_meses, data_compra):
    if garantia_meses <= 0:
        return "N/A"
    tempo = calcular_tempo_vida_total(data_compra)
    restante = garantia_meses - tempo
    return restante if restante > 0 else 0

# --- Rotas da Aplicação ---

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome = request.form["nome_bem"]
        data_compra = datetime.strptime(request.form["data_compra"], "%Y-%m-%d").date()
        valor_compra = limpar_valor(request.form["valor_compra"])
        vida_util = int(request.form["vida_util"])
        categoria = request.form["categoria"]
        status = request.form["status"]
        garantia_meses = int(request.form["garantia"]) if request.form.get("garantia") else 0
        garantia_data = (data_compra + relativedelta(months=garantia_meses)).strftime("%Y-%m-%d") if garantia_meses > 0 else "N/A"
        
        # Custo de manutenção (se informado)
        custo_manutencao = limpar_valor(request.form.get("custo_manutencao", "0"))
        # Custo total: soma do valor de compra e do custo de manutenção
        custo_total = valor_compra + (custo_manutencao if custo_manutencao > 0 else 0)

        # Processa o upload da foto com nome único para evitar sobreposição
        foto = request.files.get("foto")
        caminho_foto = None
        if foto and foto.filename:
            extensao = os.path.splitext(foto.filename)[1]
            nome_unico = f"{uuid.uuid4().hex}{extensao}"
            caminho_foto = os.path.join(app.config["UPLOAD_FOLDER"], nome_unico)
            foto.save(caminho_foto)
            caminho_foto = nome_unico

        bem = {
            "id": len(bens) + 1,
            "nome": nome,
            "data_compra": data_compra.strftime("%Y-%m-%d"),
            "valor_compra": valor_compra,
            "vida_util": vida_util,  # em anos
            "categoria": categoria,
            "status": status,
            "foto": caminho_foto,
            "garantia_data": garantia_data,
            "garantia_meses": garantia_meses,
            "custo_manutencao": custo_manutencao,
            "custo_total": custo_total
        }
        bens.append(bem)
        salvar_bens(bens)
        return redirect(url_for("listar_bens"))
    
    return render_template("cadastro.html")


@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    bem = next((b for b in bens if b["id"] == id), None)
    if not bem:
        return "Bem não encontrado", 404

    if request.method == "POST":
        bem["nome"] = request.form["nome_bem"]
        data_compra = datetime.strptime(request.form["data_compra"], "%Y-%m-%d").date()
        bem["data_compra"] = data_compra.strftime("%Y-%m-%d")
        bem["valor_compra"] = limpar_valor(request.form["valor_compra"])
        bem["vida_util"] = int(request.form["vida_util"])
        bem["categoria"] = request.form["categoria"]
        bem["status"] = request.form["status"]
        garantia_meses = int(request.form["garantia"]) if request.form.get("garantia") else 0
        bem["garantia_meses"] = garantia_meses
        bem["garantia_data"] = (data_compra + relativedelta(months=garantia_meses)).strftime("%Y-%m-%d") if garantia_meses > 0 else "N/A"
        custo_manutencao = limpar_valor(request.form.get("custo_manutencao", "0"))
        bem["custo_manutencao"] = custo_manutencao
        # Recalcula o custo total
        bem["custo_total"] = bem["valor_compra"] + custo_manutencao

        # Atualiza a foto, se um novo arquivo for enviado
        foto = request.files.get("foto")
        if foto and foto.filename:
            extensao = os.path.splitext(foto.filename)[1]
            nome_unico = f"{uuid.uuid4().hex}{extensao}"
            caminho_foto = os.path.join(app.config["UPLOAD_FOLDER"], nome_unico)
            foto.save(caminho_foto)
            bem["foto"] = nome_unico

        salvar_bens(bens)
        return redirect(url_for("listar_bens"))
    
    return render_template("editar.html", bem=bem)

@app.route("/exportar/<formato>")
def exportar(formato):
    if formato == "csv":
        filename = os.path.join("static/uploads", "bens.csv")
        with open(filename, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                "ID", "Nome", "Data da Compra", "Valor da Compra", "Custo Total da Propriedade", "Categoria",
                "Foto", "Status", "Vida Útil Restante", "Depreciação", "Valor de Uso Mensal", "Valor Residual",
                "Tempo de Vida Total", "Manutenção Total", "Garantia Restante"
            ])
            for bem in bens:
                data_compra = datetime.strptime(bem["data_compra"], "%Y-%m-%d").date()
                meses_passados = calcular_tempo_vida_total(data_compra)
                meses_restantes = calcular_vida_util_restante(data_compra, bem["vida_util"])
                dep_acumulada = calcular_depreciacao_acumulada(bem["valor_compra"], bem["vida_util"], meses_passados)
                valor_residual = max(bem["valor_compra"] - dep_acumulada, 0)
                valor_uso_mensal = calcular_valor_uso_mensal(bem.get("custo_total", 0), meses_passados)
                garantia_restante = calcular_garantia_restante_por_meses(bem.get("garantia_meses", 0), data_compra)
                manutencao_total = bem.get("custo_manutencao", 0)
                
                custo_total = bem["custo_total"] if "custo_total" in bem else 0

                writer.writerow([
                    bem["id"],
                    bem["nome"],
                    bem["data_compra"],
                    f"R$ {bem['valor_compra']:,.2f}",
                    f"R$ {custo_total:,.2f}",
                    bem["categoria"],
                    bem["foto"],
                    bem["status"],
                    f"{meses_restantes} meses",
                    f"R$ {dep_acumulada:,.2f}",
                    f"R$ {valor_uso_mensal:,.2f}",
                    f"R$ {valor_residual:,.2f}",
                    f"{meses_passados} meses",
                    f"R$ {manutencao_total:,.2f}",
                    garantia_restante if isinstance(garantia_restante, str) else f"{garantia_restante} meses"
                ])
        return send_file(filename, as_attachment=True, mimetype="text/csv")
    else:
        return "Formato não suportado", 400

@app.route("/listar")
def listar_bens():
    bens_processados = []
    for bem in bens:
        bem_processado = bem.copy()
        data_compra = datetime.strptime(bem["data_compra"], "%Y-%m-%d").date()
        meses_passados = calcular_tempo_vida_total(data_compra)
        meses_restantes = calcular_vida_util_restante(data_compra, bem["vida_util"])
        dep_acumulada = calcular_depreciacao_acumulada(bem["valor_compra"], bem["vida_util"], meses_passados)
        valor_residual = max(bem["valor_compra"] - dep_acumulada, 0)
        valor_uso_mensal = calcular_valor_uso_mensal(bem.get("custo_total", 0), meses_passados)
        garantia_restante = calcular_garantia_restante_por_meses(bem.get("garantia_meses", 0), data_compra)
        
        bem_processado["vida_util_restante"] = meses_restantes
        bem_processado["tempo_vida_total"] = meses_passados
        bem_processado["depreciacao"] = dep_acumulada
        bem_processado["valor_residual"] = valor_residual
        bem_processado["valor_uso_mensal"] = valor_uso_mensal
        bem_processado["garantia_restante"] = garantia_restante
        
        # Formatar valores monetários
        bem_processado["valor_compra_fmt"] = "R$ {:,.2f}".format(bem["valor_compra"]).replace(",", "X").replace(".", ",").replace("X", ".")
        bem_processado["custo_total_fmt"] = "R$ {:,.2f}".format(bem.get("custo_total", 0)).replace(",", "X").replace(".", ",").replace("X", ".")
        bem_processado["depreciacao_fmt"] = "R$ {:,.2f}".format(dep_acumulada).replace(",", "X").replace(".", ",").replace("X", ".")
        bem_processado["valor_uso_mensal_fmt"] = "R$ {:,.2f}".format(valor_uso_mensal).replace(",", "X").replace(".", ",").replace("X", ".")
        bem_processado["valor_residual_fmt"] = "R$ {:,.2f}".format(valor_residual).replace(",", "X").replace(".", ",").replace("X", ".")
        bem_processado["custo_manutencao_fmt"] = "R$ {:,.2f}".format(bem.get("custo_manutencao", 0)).replace(",", "X").replace(".", ",").replace("X", ".")
        
        bens_processados.append(bem_processado)
    return render_template("listar.html", bens=bens_processados)

def format_currency(value):
    if value is None:
        value = 0.0
    return "R$ {:,.2f}".format(value).replace(",", "X").replace(".", ",").replace("X", ".")

app.jinja_env.filters['currency'] = format_currency
# Registrar o filtro no Jinja2 (duplicado para garantir registro)
app.jinja_env.filters['currency'] = format_currency

@app.route("/excluir/<int:id>", methods=["POST"])
def excluir(id):
    global bens
    bens = [bem for bem in bens if bem["id"] != id]
    salvar_bens(bens)
    return redirect(url_for("listar_bens"))

if __name__ == "__main__":
    app.run(debug=True)
